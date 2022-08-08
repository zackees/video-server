import os
import sys
import tempfile
import unittest

from webtorrent_movie_server.generate_files import create_webtorrent_files, get_files
from webtorrent_movie_server.settings import (
    DOMAIN_NAME,
    STUN_SERVERS,
    TRACKER_ANNOUNCE_LIST,
)


class GenerateFilesTester(unittest.TestCase):
    """Tester for the server."""

    def test_get_files(self) -> None:
        """Opens up the server and tests that the version returned is correct."""
        actual = get_files(out_dir="out")
        if sys.platform == "win32":
            expected = ('out\\index.md5', 'out\\index.torrent', 'out\\index.html')
        else:
            expected = ('out/index.md5', 'out/index.torrent', 'out/index.html')
        self.assertEqual(expected, actual)

    @unittest.skipIf(sys.platform == "win32", "Not supported on Windows")
    def test_create_webtorrent_files(self) -> None:
        """Tests that the files can be created ok."""
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
