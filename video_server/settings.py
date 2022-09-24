"""
Global settings for the video_server. Could be migrated
to .env file in the future.
"""

import os

TRACKER_ANNOUNCE_LIST = [
    "wss://webtorrent-tracker.onrender.com",
    "wss://tracker.btorrent.xyz",
]
DEFAULT_DOMAIN = "video-server.onrender.com"
# if windows
if os.name == "nt":
    DEFAULT_DOMAIN = "localhost"  # we launched this from the app.
DOMAIN_NAME = os.environ.get("DOMAIN_NAME", DEFAULT_DOMAIN)
STUN_SERVERS = os.environ.get(
    "STUN_SERVERS", '"stun:relay.socket.dev:443", "stun:global.stun.twilio.com:3478"'
)


HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(HERE)
DATA_ROOT: str = os.environ.get("DATA_ROOT", os.path.join(HERE, "var", "data"))
WWW_ROOT = os.path.join(DATA_ROOT, "www")
VIDEO_ROOT = os.path.join(WWW_ROOT, "v")
APP_DB = os.path.join(DATA_ROOT, "app.sqlite")
LOGFILE = os.path.join(DATA_ROOT, "log.txt")

for mydir in [DATA_ROOT, WWW_ROOT, VIDEO_ROOT]:
    os.makedirs(mydir, exist_ok=True)

ENCODING_HEIGHTS = [
    int(v) for v in os.environ.get("ENCODING_HEIGHTS", "1080,720,480").split(",")
]
ENCODING_CRF = int(os.environ.get("ENCODING_CRF", 28))
NUMBER_OF_ENCODING_THREADS: int = int(os.environ.get("NUMBER_OF_THREADS", 4))
ENCODER_PRESET = os.environ.get("ENCODER_PRESET", "veryslow")
IS_TEST = os.environ.get("IS_TEST", "0") == "1"
STARTUP_LOCK = os.path.join(DATA_ROOT, "startup.lock")
LOGFILE = os.path.join(DATA_ROOT, "log.txt")
LOGFILELOCK = os.path.join(DATA_ROOT, "log.txt.lock")
MAX_BAD_LOGINS_RESET_TIME = 60 * 10  # 10 minutes
MAX_BAD_LOGINS = 10
PASSWORD = os.environ.get(
    "PASSWORD",
    "68fe2a982d12423ca59b699758684def",
)  # TODO: implement this  # pylint: disable=fixme
DISABLE_AUTH = os.environ.get("DISABLE_AUTH", "0") == "1"
WEBTORRENT_ENABLED = os.environ.get("WEBTORRENT_ENABLED", "1" if os.name != "nt" else "0") == "1"
