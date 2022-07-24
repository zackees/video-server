"""
    Seeding a movie.
"""

import os
import subprocess
import threading
import time
from dataclasses import dataclass
from typing import Optional

DEFAULT_TRACKER_URL = "wss://webtorrent-tracker.onrender.com"
TRACKER_URL = os.environ.get("TRACKER_URL", DEFAULT_TRACKER_URL)
CLIENT_SEED_PORT = 80


@dataclass
class SeederProcess:  # pylint: disable=too-few-public-methods
    """Seeder process."""

    file_name: str
    magnet_uri: str
    process: subprocess.Popen
    thread_stdout_drain: threading.Thread

    def terminate(self) -> None:
        """Kill the seeder process."""
        self.process.kill()
        self.thread_stdout_drain.join()
        print(f"seeder killed for {self.file_name}.")


def seed_movie(file_path: str) -> Optional[SeederProcess]:
    """Callback for when a new movie is added."""

    print(f"Seeding new movie: {file_path}")
    cwd = os.path.dirname(file_path)
    file_name = os.path.basename(file_path)
    cmd = (
        f'webtorrent-hybrid seed --keep-seeding "{file_name}"'
        f" --announce {TRACKER_URL} --port {CLIENT_SEED_PORT}"
    )
    print(f"Running: {cmd}")
    process = subprocess.Popen(  # pylint: disable=consider-using-with
        cmd, shell=True, cwd=cwd, stdout=subprocess.PIPE, universal_newlines=True
    )
    magnet_uri: str
    for line in iter(process.stdout.readline, ""):  # type: ignore
        print(line, end="")
        if line.startswith("magnetURI: "):
            magnet_uri = line.split(" ")[1].strip()
            print("Found magnetURI!")
            break
    else:
        rtn_code = process.poll()
        if rtn_code is not None and rtn_code != 0:
            print(f"Process exited with non-zero exit code: {rtn_code}")
        else:
            print("Could not find magnetURI!")
            process.kill()
        return None

    # Make sure that the stdout buffer is drained, or else the process
    # may freeze.
    def drain_stdout(process: subprocess.Popen) -> None:
        for line in iter(process.stdout.readline, ""):  # type: ignore
            print(line, end="")

    thread_stdout_drain = threading.Thread(target=drain_stdout, args=(process,), daemon=True)
    thread_stdout_drain.start()
    # Generate a class to hold all the relevant information.
    seeder = SeederProcess(
        file_name=file_name,
        magnet_uri=magnet_uri,
        process=process,
        thread_stdout_drain=thread_stdout_drain,
    )
    return seeder
