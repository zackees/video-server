"""
Global settings for the webtorrent_movie_server. Could be migrated
to .env file in the future.
"""

import os

TRACKER_ANNOUNCE_LIST = [
    "wss://webtorrent-tracker.onrender.com",
    "wss://tracker.btorrent.xyz",
]
DOMAIN_NAME = os.environ.get("DOMAIN_NAME", "video-server.onrender.com")
STUN_SERVERS = os.environ.get(
    "STUN_SERVERS", '"stun:relay.socket.dev:443", "stun:global.stun.twilio.com:3478"'
)


HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
DATA_ROOT = os.environ.get("DATA_ROOT", os.path.join(PROJECT_ROOT, "var", "data"))
WWW_ROOT = os.path.join(DATA_ROOT, "www")
VIDEO_ROOT = os.path.join(WWW_ROOT, "v")
APP_DB = os.path.join(DATA_ROOT, "app.sqlite")
LOGFILE = os.path.join(DATA_ROOT, "log.txt")

for mydir in [DATA_ROOT, WWW_ROOT, VIDEO_ROOT]:
    os.makedirs(mydir, exist_ok=True)
