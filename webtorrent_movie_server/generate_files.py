"""
Generates webtorrent files.
"""

# pylint: disable=invalid-name
# pylint: disable=consider-using-with
# pylint: disable=too-many-arguments
# pylint: disable=too-many-locals
# pylint: disable=unnecessary-lambda
import sys
import hashlib
import os
import shutil
from typing import List, Tuple
import time
from webtorrent_movie_server.settings import (
    DOMAIN_NAME,
    STUN_SERVERS,
    TRACKER_ANNOUNCE_LIST,
)

# WORK IN PROGRESS
HERE = os.path.dirname(os.path.abspath(__file__))
PLAYER_DIR = os.path.join(HERE, "player")


def read_utf8(file: str) -> str:
    """Reads a file and returns its contents as a string."""
    with open(file, encoding="utf-8", mode="r") as f:
        return f.read()


def write_utf8(file: str, contents: str) -> None:
    """Writes a string to a file."""
    with open(file, encoding="utf-8", mode="w") as f:
        f.write(contents)


HTML_TEMPLATE = read_utf8(os.path.join(HERE, "template.html"))
WEBTORRENT_ZACH_MIN_JS = os.path.abspath(os.path.join(HERE, "webtorrent.zach.min.js"))
REDIRECT_HTML = os.path.join(HERE, "redirect.html")
assert os.path.exists(WEBTORRENT_ZACH_MIN_JS), f"Missing {WEBTORRENT_ZACH_MIN_JS}"


def filemd5(filename):
    """Gets the md5 of a file."""
    with open(filename, mode="rb") as filed:
        d = hashlib.md5()
        for buf in iter(lambda: filed.read(128 * d.block_size), b""):
            d.update(buf)
    return d.hexdigest()


def get_files(out_dir: str) -> Tuple[str, str, str]:  # pylint: disable=too-many-locals
    """Gets all the artificate names from the source file."""
    md5file = os.path.join(out_dir, "index.md5")
    torrent_path = os.path.join(out_dir, "index.torrent")
    html_path = os.path.join(out_dir, "index.html")
    return md5file, torrent_path, html_path


def create_webtorrent_files(
    file: str,
    domain_name: str,
    tracker_announce_list: List[str],
    stun_servers: str,
    out_dir: str,
    chunk_factor: int = 17,
) -> Tuple[str, str]:
    """Generates the webtorrent files for a given video file."""
    assert tracker_announce_list
    os.makedirs(out_dir, exist_ok=True)
    md5file, torrent_path, html_path = get_files(out_dir=out_dir)
    # Generate the md5 file
    md5 = filemd5(file)
    if not os.path.exists(md5file) or md5 != read_utf8(md5file):
        print(f"MD5 mismatch for {file}")
        for f in [md5file, torrent_path, html_path]:
            if os.path.exists(f):
                os.remove(f)
        write_utf8(md5file, contents=md5)
    if os.path.exists(torrent_path):
        os.remove(torrent_path)
    # Use which to detect whether the mktorrent binary is available.
    if not shutil.which("mktorrent"):
        raise OSError("mktorrent not found")
    tracker_announce = "-a " + " -a ".join(tracker_announce_list)
    # print(os.environ['path'])
    cmd = f'mktorrent "{file}" {tracker_announce} -l {chunk_factor} -o "{torrent_path}"'
    print(f"Running\n    {cmd}")
    # subprocess.check_output(cmd, shell=True)
    os.system(cmd)
    vid_name = os.path.basename(os.path.dirname(file))
    assert os.path.exists(torrent_path), f"Missing expected {torrent_path}"
    #http_type = "http" if "localhost" in domain_name else "https"
    #torrent_id = f"{http_type}://{domain_name}/v/{vid_name}/index.torrent"
    #webseed = f"{http_type}://{domain_name}/v/{vid_name}/vid.mp4"
    #html = HTML_TEMPLATE.replace("__TORRENT_URL__", torrent_id)
    #html = html.replace("__WEBSEED__", webseed)
    #html = html.replace("__STUN_SERVERS__", stun_servers)
    #write_utf8(html_path, contents=html)

    shutil.copytree(PLAYER_DIR, out_dir, dirs_exist_ok=True)
    # video_json_file = os.path.join(out_dir, "video.json")


    assert os.path.exists(html_path), f"Missing {html_path}"
    return (html_path, torrent_path)


def sync_source_file(file: str, out_file: str) -> bool:
    """Syncs the source file to the output file. The output file is only modified if different."""
    if not os.path.exists(out_file):
        shutil.copyfile(file, out_file)
        return True
    if filemd5(file) != filemd5(out_file):
        shutil.copyfile(file, out_file)
        return True
    return False


def init_static_files(out_dir: str) -> None:
    """Initializes the static files."""
    assert os.path.exists(out_dir)
    WEBTORRENT_ZACH_MIN_JS_OUT = os.path.join(out_dir, "webtorrent.zach.min.js")
    sync_source_file(WEBTORRENT_ZACH_MIN_JS, WEBTORRENT_ZACH_MIN_JS_OUT)
    sync_source_file(REDIRECT_HTML, os.path.join(out_dir, "index.html"))


def main() -> int:
    """Main entry point, deprecated and will be removed."""
    # Scan DATA_DIR for movie files
    # Directory structure is
    # $DATA_DIR/content - contains *.mp4 or *.webm files
    # $DATA_DIR - contains the generated files
    CHUNK_FACTOR = 17  # 128KB, or n^17
    OUT_DIR = os.environ.get("DATA_DIR", "/var/data")
    CONTENT_DIR = os.path.join(OUT_DIR, "content")
    os.makedirs(CONTENT_DIR, exist_ok=True)
    os.makedirs(OUT_DIR, exist_ok=True)
    init_static_files(OUT_DIR)
    prev_cwd = os.getcwd()
    os.chdir(CONTENT_DIR)
    while True:
        files = os.listdir()
        files = [
            f
            for f in files
            if f.lower().endswith(".mp4") or f.lower().endswith(".webm")
        ]
        if not files:
            return 0
        # Get the most recent time stamps
        newest_file = sorted(files, key=lambda f: os.path.getmtime(f))[0]
        # If newest_file is younger than 10 seconds, then wait then try again
        if os.path.getmtime(newest_file) > time.time() - 10:
            time.sleep(1)
            continue
        break
    html_str = "<html><body><ul>"
    for movie_file in files:
        try:
            iframe_src, torrent_path = create_webtorrent_files(
                movie_file,
                domain_name=DOMAIN_NAME,
                tracker_announce_list=TRACKER_ANNOUNCE_LIST,
                stun_servers=STUN_SERVERS,
                chunk_factor=CHUNK_FACTOR,
                out_dir=OUT_DIR,
            )
            assert os.path.exists(iframe_src), f"Missing {iframe_src}, skipping"
            html_str += f"""
                <li>
                <h3><a href="{os.path.basename(iframe_src)}">{os.path.basename(iframe_src)}</a></h3>
                <ul>
                    <li><a href="{f"content/{os.path.basename(movie_file)}"}">{f"content/{os.path.basename(movie_file)}"}</a></li>
                    <li><a href="{os.path.basename(torrent_path)}">{os.path.basename(torrent_path)}</a></li>
                </ul>
                </li>
            """
        except Exception as e:  # pylint: disable=broad-except
            print(f"Failed to create webtorrent files for {movie_file}: {e}")
            continue
    html_str += "</ul></body></html>"
    # Write the HTML file
    index_html = os.path.join(OUT_DIR, "index.html")
    print(f"Writing {index_html}")
    write_utf8(index_html, contents=html_str)
    os.chdir(prev_cwd)
    return 0


if __name__ == "__main__":
    sys.exit(main())
