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

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import warnings
from distutils.dir_util import copy_tree  # pylint: disable=deprecated-module
from pprint import pprint
from typing import List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor

from video_server.asyncwrap import asyncwrap

from video_server.io import read_utf8, sanitze_path, write_utf8
from video_server.lang import lang_label
from video_server.settings import (
    DOMAIN_NAME,
    STUN_SERVERS,
    TRACKER_ANNOUNCE_LIST,
    ENCODING_HEIGHTS,
    ENCODING_CRF,
    NUMBER_OF_ENCODING_THREADS,
    ENCODER_QUALITY,
)

# WORK IN PROGRESS
HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(HERE)
TESTS_DATA = os.path.join(PROJECT_ROOT, "tests", "test_data")
PLAYER_DIR = os.path.join(HERE, "player")
HTML_TEMPLATE = read_utf8(os.path.join(HERE, "template.html"))
REDIRECT_HTML = os.path.join(HERE, "redirect.html")

executor = ThreadPoolExecutor(max_workers=NUMBER_OF_ENCODING_THREADS)


def filemd5(filename):
    """Gets the md5 of a file."""
    with open(filename, mode="rb") as filed:
        d = hashlib.md5()
        for buf in iter(lambda: filed.read(128 * d.block_size), b""):
            d.update(buf)
    return d.hexdigest()


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


def encode(videopath: str, crf: int, height: int, outpath: str) -> None:
    """Encodes a video"""
    downmix_stmt = "-ac 1" if height <= 480 else ""
    # trunc(oh*...) fixes issue with libx264 encoder not liking an add number of width pixels.
    cmd = f'static_ffmpeg -hide_banner -i "{videopath}" -vf scale="trunc(oh*a/2)*2:{height}" {downmix_stmt} -movflags +faststart -preset {ENCODER_QUALITY} -c:v libx264 -crf {crf} "{outpath}" -y'  # pylint: disable=line-too-long
    print(f"Running:\n  {cmd}")
    proc = subprocess.Popen(cmd, shell=True)
    proc.wait()
    print("Generated file: " + outpath)


def get_video_height(vidfile: str) -> int:
    """Gets the video height from the video file."""
    # use ffprobe to get the height of the video
    cmd = f'static_ffprobe "{vidfile}" -show_streams 2>&1'
    stdout = subprocess.check_output(cmd, shell=True)
    lines = stdout.decode().splitlines()
    for line in lines:
        if line.startswith("height"):
            height = int(line.split("=")[1])
            return height
    raise ValueError(f"Missing height in {vidfile}")


def create_webtorrent_files(
    vid_name: str,
    vidfile: str,
    domain_name: str,
    tracker_announce_list: List[str],
    stun_servers: str,  # pylint: disable=unused-argument
    out_dir: str,
    chunk_factor: int = 17,
    do_encode: bool = False,
) -> Tuple[str, str]:
    """Generates the webtorrent files for a given video file."""
    assert tracker_announce_list
    os.makedirs(out_dir, exist_ok=True)
    original_video_height = get_video_height(vidfile)
    html_path = os.path.join(out_dir, "index.html")
    http_type = "http" if "localhost" in domain_name else "https"
    vidpath = sanitze_path(vid_name)
    tasks = []
    for height in ENCODING_HEIGHTS:
        torrent_path = os.path.join(out_dir, f"{height}.torrent")
        outpath = os.path.join(out_dir, f"{height}.mp4")

        def encoding_task(vidfile, crf, height, outpath, torrent_path):
            if do_encode:
                encode(videopath=vidfile, crf=crf, height=height, outpath=outpath)
            else:
                shutil.copy(vidfile, outpath)
            mktorrent(
                vidfile=outpath,
                torrent_path=torrent_path,
                tracker_announce_list=tracker_announce_list,
                chunk_factor=chunk_factor,
            )
            size_mp4file = os.path.getsize(outpath)
            duration: float = query_duration(outpath)
            webseed = f"{http_type}://{domain_name}/v/{vidpath}/{height}.mp4"
            torrent_url = f"{http_type}://{domain_name}/v/{vidpath}/{height}.torrent"
            return dict(
                height=height,
                duration=duration,
                size=size_mp4file,
                file_url=webseed,
                torrent_url=torrent_url,
            )

        task = executor.submit(
            encoding_task,
            vidfile,
            ENCODING_CRF,
            original_video_height if not do_encode else height,
            outpath,
            torrent_path,
        )
        tasks.append(task)
        if not do_encode:
            break  # It's just a copy, so we only need to do one encoding.

    completed_vids: list[dict] = [task.result() for task in tasks]
    vidfolder = os.path.dirname(vidfile)
    subtitles_dir = os.path.join(vidfolder, "subtitles")
    print(f"Subtitles dir: {subtitles_dir}")
    url_slug = f"/v/{vidpath}"
    vtt_files = []
    if os.path.exists(subtitles_dir):
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
    video_json = {
        "note": "This is a sample and should be overriden during the video creation process",
        "name": vidpath,
        "urlslug": url_slug,
        "domain": domain_name,
        "videos": completed_vids,
        "subtitles": subtitles,
        "todo": "Let's also have bitchute: <URL> and rumble <URL>",
        "webtorrent": {
            "enabled": True,
            "eager_webseed": True,
        },
    }

    print("video.json:")
    pprint(video_json)
    json_data = json.dumps(video_json, indent=4)
    write_utf8(os.path.join(out_dir, "video.json"), contents=json_data)
    src_html = os.path.join(PLAYER_DIR, "index.template.html")
    dst_html = os.path.join(out_dir, "index.html")
    sync_source_file(src_html, dst_html)
    return (html_path, torrent_path)


@asyncwrap
def async_create_webtorrent_files(
    vid_name: str,
    vidfile: str,
    domain_name: str,
    tracker_announce_list: List[str],
    stun_servers: str,
    out_dir: str,
    chunk_factor: int = 17,
    do_encode: bool = False,
) -> Tuple[str, str]:
    """Creates the webtorrent files for a given video file."""
    return create_webtorrent_files(
        vid_name=vid_name,
        vidfile=vidfile,
        domain_name=domain_name,
        tracker_announce_list=tracker_announce_list,
        stun_servers=stun_servers,
        out_dir=out_dir,
        chunk_factor=chunk_factor,
        do_encode=do_encode,
    )


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
        files = [f for f in files if f.lower().endswith(".mp4") or f.lower().endswith(".webm")]
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
            # strip extension
            vidname = os.path.splitext(os.path.basename(movie_file))[0]
            iframe_src, torrent_path = create_webtorrent_files(
                vid_name=vidname,
                vidfile=movie_file,
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
