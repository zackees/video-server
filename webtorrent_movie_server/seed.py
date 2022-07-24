"""
    Seeding a movie.
"""

import os
import subprocess
import threading

DEFAULT_TRACKER_URL = "wss://webtorrent-tracker.onrender.com:80"
TRACKER_URL = os.environ.get("TRACKER_URL", DEFAULT_TRACKER_URL)
CLIENT_SEED_PORT = 80


class SeederProcess:  # pylint: disable=too-few-public-methods
    """Seeder process."""

    def __init__(
        self,
        file_name: str,
        magnet_uri: str,
        process: subprocess.Popen,
        stdout_thread: threading.Thread,
    ) -> None:
        self.file_name = file_name
        self.magnet_uri = magnet_uri
        self.process = process
        self.stdout_thread = stdout_thread

    def terminate(self) -> None:
        """Kill the seeder process."""
        self.process.kill()
        self.stdout_thread.join()
        print(f"seeder killed for {self.file_name}.")


def seed_movie(file_path: str) -> SeederProcess:
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
    magnet_uri = None
    for line in iter(process.stdout.readline, ""):  # type: ignore
        print(line, end="")
        if line.startswith("magnetURI: "):
            magnet_uri = line.split(" ")[1].strip()
            print(f"Found magnetURI: {magnet_uri}")
            break

    # Make sure that the stdout buffer is drained, or else the process
    # may freeze.
    def drain_stdout(process: subprocess.Popen) -> None:
        for line in iter(process.stdout.readline, ""):  # type: ignore
            print(line, end="")

    thread_stdout_drain = threading.Thread(target=drain_stdout, args=(process,), daemon=True)
    thread_stdout_drain.start()
    setattr(process, "magnet_uri", magnet_uri)
    assert magnet_uri is not None, "Could not find magnet URI"
    # Do something
    seeder = SeederProcess(file_name, magnet_uri, process, thread_stdout_drain)
    return seeder
