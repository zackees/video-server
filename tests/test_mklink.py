import os
import shutil
import unittest


from video_server.generate_files import mklink


HERE = os.path.dirname(os.path.abspath(__file__))
TMP_DIR = os.path.join(HERE, "tmp", "mklink")
TEST_MP4 = os.path.join(HERE, "tmp", "test.mp4")


class GenerateFilesTester(unittest.TestCase):
    """Tester for the server."""


    def test_create_webtorrent_files(self) -> None:
        src = TEST_MP4
        dst = os.path.join(TMP_DIR, "out_test.mp4")
        shutil.rmtree(TMP_DIR, ignore_errors=True)
        os.makedirs(TMP_DIR, exist_ok=True)
        mklink(src, dst)
        shutil.rmtree(TMP_DIR)



if __name__ == "__main__":
    unittest.main()
