from genericpath import isfile
import os
import sys
import unittest
from typing import List
import shutil

from video_server import generate_files
from video_server.settings import (
    DOMAIN_NAME,
    STUN_SERVERS,
    TRACKER_ANNOUNCE_LIST,
)

HERE = os.path.dirname(os.path.abspath(__file__))
TMP_DIR = os.path.join(HERE, "test_data", "tmp", "generate_files")
TEST_MP4 = os.path.join(HERE, "test_data", "test.mp4")
os.makedirs(TMP_DIR, exist_ok=True)


def fake_mktorrent(
    vidfile: str, torrent_path: str, tracker_announce_list: List[str], chunk_factor: int
) -> None:
    """
    Fake mktorrent function.
    """
    return "fake_mktorrent"


class GenerateFilesTester(unittest.TestCase):
    """Tester for the server."""

    def test_create_webtorrent_files(self) -> None:
        """Tests that the files can be created ok."""
        if sys.platform == "win32":
            generate_files.mktorrent = fake_mktorrent
        # Clear out TMP_DIR
        for f in os.listdir(TMP_DIR):
            full_path = os.path.join(TMP_DIR, f)
            if os.path.isfile(full_path):
                os.remove(full_path)
            else:
                shutil.rmtree(full_path, ignore_errors=True)
        assert os.path.exists(TEST_MP4)
        # Create a temporary folder.
        try:
            generate_files.create_webtorrent_files(
                vid_id=1,
                vid_name="test",
                vidfile=TEST_MP4,
                domain_name=DOMAIN_NAME,
                tracker_announce_list=TRACKER_ANNOUNCE_LIST,
                stun_servers=STUN_SERVERS,
                out_dir=TMP_DIR,
            )
            print("Finished")
        except Exception as e:
            self.fail(e)


if __name__ == "__main__":
    unittest.main()
