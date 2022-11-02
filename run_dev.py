"""
Setup development environment
"""

import webbrowser
import os

os.environ.setdefault("DOMAIN_NAME", "localhost")
os.environ.setdefault("IS_TEST", "1")
os.environ.setdefault("DISABLE_AUTH", "1")

from video_server.app import main

if __name__ == "__main__":
    webbrowser.open("http://localhost:80")
    main()
