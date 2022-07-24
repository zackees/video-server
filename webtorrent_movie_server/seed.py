"""
    Seeding a movie.
"""

import os
import subprocess
import threading

DEFAULT_TRACKER_URL = "wss://webtorrent-tracker.onrender.com"
TRACKER_URL = os.environ.get("TRACKER_URL", DEFAULT_TRACKER_URL)
CLIENT_SEED_PORT = 80


def seed_movie(file_path: str) -> str:
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

    threading.Thread(target=drain_stdout, args=(process,)).start()
    assert magnet_uri is not None, "Could not find magnet URI"
    # Do something
    return magnet_uri
