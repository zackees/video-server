import os

TRACKER_ANNOUNCE_LIST = [
    "wss://webtorrent-tracker.onrender.com",
    "wss://tracker.btorrent.xyz"
]
DOMAIN_NAME = os.environ.get("DOMAIN_NAME", "https://webtorrent-webseed.onrender.com")
STUN_SERVERS = os.environ.get("STUN_SERVERS", '"stun:relay.socket.dev:443", "stun:global.stun.twilio.com:3478"')
