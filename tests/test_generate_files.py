import os
import tempfile
import unittest

from webtorrent_movie_server.generate_files import create_webtorrent_files, get_files

STUN_SERVERS = '"stun:relay.socket.dev:443", "stun:global.stun.twilio.com:3478"'
TRACKER_ANNOUNCE_LIST = [
    "wss://webtorrent-tracker.onrender.com",
    "wss://tracker.btorrent.xyz"
]
DOMAIN_NAME = "https://webtorrent-webseed.onrender.com"

class GenerateFilesTester(unittest.TestCase):
    """Tester for the server."""

    def test_get_files(self) -> None:
        """Opens up the server and tests that the version returned is correct."""
        actual = get_files("blah.mp4", out_dir="out")
        if os.name == "nt":
            expected = ('out\\blah.mp4.md5', 'out\\blah.mp4.torrent', 'out\\blah.mp4.torrent.html')
        else:
            expected = ('out/blah.mp4.md5', 'out/blah.mp4.torrent', 'out/blah.mp4.torrent.html')
        self.assertEqual(expected, actual)

    def test_create_webtorrent_files(self) -> None:
        """Opens up the server and tests that the version returned is correct."""
        # Create a temporary folder.
        with tempfile.TemporaryDirectory() as tmpdirname:
            mp4 = os.path.join(tmpdirname, "test.mp4")
            with open(mp4, encoding="utf-8", mode="w") as f:
                f.write("")
            try:
                create_webtorrent_files(mp4,
                                        domain_name=DOMAIN_NAME,
                                        tracker_announce_list=TRACKER_ANNOUNCE_LIST,
                                        stun_servers=STUN_SERVERS,
                                        out_dir=tmpdirname)
            except Exception as e:
                self.fail(e)


if __name__ == "__main__":
    unittest.main()
