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
# pylint: disable=logging-fstring-interpolation
# pylint: disable=logging-not-lazy

import hashlib
import json
import os
import shutil
import warnings
from distutils.dir_util import copy_tree  # pylint: disable=deprecated-module
from concurrent.futures import ThreadPoolExecutor

from video_server.asyncwrap import asyncwrap

from video_server.io import read_utf8, sanitize_path, write_utf8
from video_server.lang import lang_label
from video_server.settings import (
    NUMBER_OF_ENCODING_THREADS,
    WEBTORRENT_ENABLED,
)
from video_server.util import mktorrent_task
from video_server.log import log

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


def mklink(src: str, link_path: str) -> None:
    """Creates a symbolic link."""
    # If this fails here on win32 then turn on "developer mode".
    if os.path.exists(link_path):
        os.remove(link_path)
    os.symlink(src, link_path, target_is_directory=os.path.isdir(src))


def create_metadata_files(
    vid_id: int,
    vid_title: str,
    vidfiles: list[str],
    domain_name: str,
    tracker_announce_list: list[str],
    stun_servers: str,  # pylint: disable=unused-argument
    out_dir: str,
    chunk_factor: int,
) -> str:
    """Generates the webtorrent files for a given video file."""
    assert tracker_announce_list
    os.makedirs(out_dir, exist_ok=True)
    html_path = os.path.join(out_dir, "index.html")
    http_type = "http" if "localhost" in domain_name else "https"
    vidname = sanitize_path(vid_title)
    base_video_path = f"{http_type}://{domain_name}/v/{vidname}"
    tasks = []
    # for height in ENCODING_HEIGHTS:
    for vidfile in vidfiles:
        # height = get_video_height(vidfile)
        basename = os.path.splitext(os.path.basename(vidfile))[0]
        task = executor.submit(
            mktorrent_task,
            vidfile=vidfile,
            torrent_path=f"{basename}.torrent",
            tracker_announce_list=tracker_announce_list,
            chunk_factor=chunk_factor,
            webseed=f"{base_video_path}/{basename}.mp4",
            torrent_url=f"{base_video_path}/{basename}.torrent",
        )
        tasks.append(task)
    completed_vids: list[dict] = [task.result() for task in tasks]
    vidfolder = os.path.dirname(vid_title)
    subtitles_dir = os.path.join(vidfolder, "subtitles")
    log.info(f"Subtitles dir: {subtitles_dir}")
    url_slug = f"/v/{vidname}"
    vtt_files = []
    if os.path.exists(subtitles_dir):
        vtt_files = [f for f in os.listdir(subtitles_dir) if f.endswith(".vtt")]
    log.info(f"Found {len(vtt_files)} vtt files")

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
    log.info(f"Subtitles: {subtitles}")
    video_json = {
        "title": vid_title,
        "id": vid_id,
        "urlslug": url_slug,
        "url": base_video_path,
        "domain": domain_name,
        "videos": completed_vids,
        "subtitles": subtitles,
        "poster": f"{base_video_path}/thumbnail.jpg",
        "webtorrent": {
            "enabled": WEBTORRENT_ENABLED,
            "eager_webseed": True,
        },
    }
    json_data = json.dumps(video_json, indent=4)
    write_utf8(os.path.join(out_dir, "video.json"), contents=json_data)
    src_html = os.path.join(PLAYER_DIR, "index.template.html")
    dst_html = os.path.join(out_dir, "index.html")
    sync_source_file(src_html, dst_html)
    return html_path


@asyncwrap
def async_create_metadata_files(
    vid_id: int,
    vid_title: str,
    vidfiles: list[str],
    domain_name: str,
    tracker_announce_list: list[str],
    stun_servers: str,  # pylint: disable=unused-argument
    out_dir: str,
    chunk_factor: int,
) -> str:
    """Creates the webtorrent files for a given video file."""
    return create_metadata_files(
        vid_id=vid_id,
        vid_title=vid_title,
        vidfiles=vidfiles,
        domain_name=domain_name,
        tracker_announce_list=tracker_announce_list,
        stun_servers=stun_servers,
        out_dir=out_dir,
        chunk_factor=chunk_factor,
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
    for file in ["test.mp4"]:
        src = os.path.join(TESTS_DATA, file)
        dst = os.path.join(demo_dir, file)
        if os.path.exists(src):
            shutil.copy(src, dst)
        else:
            warnings.warn(f"Missing {src}")
