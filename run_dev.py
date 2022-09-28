"""
Setup development environment
"""

import webbrowser
import subprocess
import uvicorn  # type: ignore
import os

os.environ.setdefault("DOMAIN_NAME", "localhost")
os.environ.setdefault("IS_TEST", "1")
os.environ.setdefault("DISABLE_AUTH", "1")

from video_server.settings import DATA_ROOT
from video_server.app import app


def main() -> None:
    webbrowser.open("http://localhost:80")
    cmd = f"http-server {DATA_ROOT}/www -p 8000 --cors=* -c-1"
    print(f"Starting http-server: {cmd}")
    with subprocess.Popen(cmd, shell=True):
        # Run the server in debug mode.
        uvicorn.run(app, host="0.0.0.0", port=80)

if __name__ == "__main__":
    main()
