"""
Generates webtorrent files.
"""

# pylint: disable=invalid-name
# pylint: disable=consider-using-with
# pylint: disable=too-many-arguments
# pylint: disable=too-many-locals
# pylint: disable=unnecessary-lambda
# pylint: disable=fixme
# pylint: disable=too-many-return-statements
# pylint: disable=too-many-branches
# pylint: disable=too-many-statements

import sys
import hashlib
import os
import shutil
from pprint import pprint
from typing import List, Tuple, Optional
import subprocess
import time
import json
import warnings
from distutils.dir_util import copy_tree  # pylint: disable=deprecated-module
from webtorrent_movie_server.settings import (
    DOMAIN_NAME,
    STUN_SERVERS,
    TRACKER_ANNOUNCE_LIST,
)
from webtorrent_movie_server.generate_video_json import generate_video_json


# WORK IN PROGRESS
HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(HERE)
TESTS_DATA = os.path.join(PROJECT_ROOT, "tests", "test_data")
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
REDIRECT_HTML = os.path.join(HERE, "redirect.html")


def filemd5(filename):
    """Gets the md5 of a file."""
    with open(filename, mode="rb") as filed:
        d = hashlib.md5()
        for buf in iter(lambda: filed.read(128 * d.block_size), b""):
            d.update(buf)
    return d.hexdigest()


def get_files(out_dir: str) -> Tuple[str, str]:  # pylint: disable=too-many-locals
    """Gets all the artificate names from the source file."""
    torrent_path = os.path.join(out_dir, "index.torrent")
    html_path = os.path.join(out_dir, "index.html")
    return torrent_path, html_path


def mktorrent(
    vidfile: str, torrent_path: str, tracker_announce_list: List[str], chunk_factor: int
) -> None:
    """Creates a torrent file."""
    if os.path.exists(torrent_path):
        os.remove(torrent_path)
    # Use which to detect whether the mktorrent binary is available.
    if not shutil.which("mktorrent"):
        raise OSError("mktorrent not found")
    tracker_announce = "-a " + " -a ".join(tracker_announce_list)
    # print(os.environ['path'])
    cmd = f'mktorrent "{vidfile}" {tracker_announce} -l {chunk_factor} -o "{torrent_path}"'
    print(f"Running\n    {cmd}")
    # subprocess.check_output(cmd, shell=True)
    os.system(cmd)
    assert os.path.exists(torrent_path), f"Missing expected {torrent_path}"


def mklink(src: str, link_path: str) -> None:
    """Creates a symbolic link."""
    # If this fails here on win32 then turn on "developer mode".
    if os.path.exists(link_path):
        os.remove(link_path)
    os.symlink(src, link_path, target_is_directory=os.path.isdir(src))


def query_duration(vidfile: str) -> float:
    """Queries the duration of a video."""
    cmd = f'static_ffprobe "{vidfile}" -show_format 2>&1'
    stdout = subprocess.check_output(cmd, shell=True)
    lines = stdout.decode().splitlines()
    duration: Optional[float] = None
    for line in lines:
        if line.startswith("duration"):
            duration = float(line.split("=")[1])
            break
    assert duration is not None, f"Missing duration in {vidfile}"
    return duration


def create_webtorrent_files(
    vidfile: str,
    domain_name: str,
    tracker_announce_list: List[str],
    stun_servers: str,  # pylint: disable=unused-argument
    out_dir: str,
    chunk_factor: int = 17,
) -> Tuple[str, str]:
    """Generates the webtorrent files for a given video file."""
    assert tracker_announce_list
    os.makedirs(out_dir, exist_ok=True)
    torrent_path, html_path = get_files(out_dir=out_dir)
    mktorrent(
        vidfile=vidfile,
        torrent_path=torrent_path,
        tracker_announce_list=tracker_announce_list,
        chunk_factor=chunk_factor,
    )
    vidfolder = os.path.dirname(vidfile)
    subtitles_dir = os.path.join(vidfolder, "subtitles")
    print(f"Subtitles dir: {subtitles_dir}")
    size_mp4file = os.path.getsize(vidfile)
    duration: float = query_duration(vidfile)
    # Vidname is currently the parent directory, and this should be changed later.
    vid_name = os.path.basename(out_dir)
    http_type = "http" if "localhost" in domain_name else "https"
    torrent_url = f"{http_type}://{domain_name}/v/{vid_name}/index.torrent"
    webseed = f"{http_type}://{domain_name}/v/{vid_name}/vid.mp4"
    url_slug = f"/v/{vid_name}"

    def lang_label(langname: str) -> str:
        """Returns a label for a given name."""
        if langname.startswith("en"):
            return "English"
        if langname.startswith("es"):
            return "Spanish"
        if langname.startswith("fr"):
            return "French"
        if langname.startswith("pt"):
            return "Portuguese"
        if langname.startswith("it"):
            return "Italian"
        if langname.startswith("de"):
            return "German"
        if langname.startswith("ru"):
            return "Russian"
        if langname.startswith("ja"):
            return "Japanese"
        if langname.startswith("zh"):
            return "Chinese"
        if langname.startswith("ko"):
            return "Korean"
        if langname.startswith("ar"):
            return "Arabic"
        if langname.startswith("tr"):
            return "Turkish"
        if langname.startswith("pl"):
            return "Polish"
        if langname.startswith("nl"):
            return "Dutch"
        if langname.startswith("el"):
            return "Greek"
        if langname.startswith("hi"):
            return "Hindi"
        if langname.startswith("th"):
            return "Thai"
        if langname.startswith("vi"):
            return "Vietnamese"
        if langname.startswith("id"):
            return "Indonesian"
        if langname.startswith("fa"):
            return "Persian"
        if langname.startswith("he"):
            return "Hebrew"
        if langname.startswith("sq"):
            return "Albanian"
        if langname.startswith("ro"):
            return "Romanian"
        if langname.startswith("sr"):
            return "Serbian"
        if langname.startswith("uk"):
            return "Ukrainian"
        if langname.startswith("hr"):
            return "Croatian"
        if langname.startswith("cs"):
            return "Czech"
        if langname.startswith("sk"):
            return "Slovak"
        if langname.startswith("sl"):
            return "Slovenian"
        if langname.startswith("bg"):
            return "Bulgarian"
        if langname.startswith("hu"):
            return "Hungarian"
        if langname.startswith("lt"):
            return "Lithuanian"
        if langname.startswith("lv"):
            return "Latvian"
        if langname.startswith("mk"):
            return "Macedonian"
        if langname.startswith("fa"):
            return "Persian"
        return langname

    vtt_files = [f for f in os.listdir(subtitles_dir) if f.endswith(".vtt")]
    print(f"Found {len(vtt_files)} vtt files")

    def lang_name(vtt_file: str) -> str:
        """Returns the language name from a vtt file name."""
        return os.path.splitext(os.path.basename(vtt_file))[0]

    subtitles = [
        {
            "file": f"{url_slug}/subtitles/{file_vtt}",
            "srclang": lang_name(file_vtt),
            "label": lang_label(file_vtt),
        }
        for file_vtt in vtt_files
    ]
    print(f"Subtitles: {subtitles}")
    dict_data = generate_video_json(
        domain_name=domain_name,
        vidname=os.path.splitext(vid_name)[0].replace(".mp4", ""),
        url_slug=url_slug,
        torrentfile=torrent_url,
        mp4file=webseed,
        size_mp4file=size_mp4file,
        duration=duration,
        subtitles=subtitles,
    )
    print("video.json:")
    pprint(dict_data)
    json_data = json.dumps(dict_data, indent=4)
    write_utf8(os.path.join(out_dir, "video.json"), contents=json_data)
    # Generate player files.
    # mklink(PLAYER_DIR, link_path = os.path.join(out_dir, "player"))
    # link_index_html = os.path.join(out_dir, "index.html")
    # src_index_html = os.path.join(PLAYER_DIR, "index.html")
    # mklink(src_index_html, link_path=link_index_html)
    # assert os.path.exists(html_path), "Missing " + os.path.abspath(html_path)
    # if not os.path.exists(REDIRECT_HTML):
    #    print("Missing " + os.path.abspath(html_path))

    src_html = os.path.join(PLAYER_DIR, "index.template.html")
    dst_html = os.path.join(out_dir, "index.html")
    sync_source_file(src_html, dst_html)
    # Debug code from debugging subtitles
    # Copy /player/subtitles to out_dir/subtitles
    # src_subtitles = os.path.join(HERE, "subtitles")
    # dst_subtitles = os.path.join(out_dir, "subtitles")
    # shutil.copytree(src_subtitles, dst_subtitles)
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
    sync_source_file(REDIRECT_HTML, os.path.join(out_dir, "index.html"))
    copy_tree(PLAYER_DIR, f"{out_dir}/player")
    demo_dir = os.path.join(out_dir, "demo")
    os.makedirs(demo_dir, exist_ok=True)
    # shutil.copy clobbers files if they already exist.
    for file in ["subtitles.js", "test.mp4"]:
        src = os.path.join(TESTS_DATA, file)
        dst = os.path.join(demo_dir, file)
        if os.path.exists(src):
            shutil.copy(src, dst)
        else:
            warnings.warn(f"Missing {src}")


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
