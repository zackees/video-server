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
import subprocess
import warnings
from distutils.dir_util import copy_tree  # pylint: disable=deprecated-module
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor

from video_server.asyncwrap import asyncwrap

from video_server.io import read_utf8, sanitize_path, write_utf8
from video_server.lang import lang_label
from video_server.settings import (
    ENCODING_HEIGHTS,
    ENCODING_CRF,
    NUMBER_OF_ENCODING_THREADS,
    ENCODER_PRESET,
    WEBTORRENT_ENABLED,
)
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


def mktorrent(
    vidfile: str, torrent_path: str, tracker_announce_list: List[str], chunk_factor: int
) -> None:
    """Creates a torrent file."""
    # if windows
    if os.name == "nt":
        log.error("mktorrent not supported on windows")
        return
    if os.path.exists(torrent_path):
        os.remove(torrent_path)
    # Use which to detect whether the mktorrent binary is available.
    if not shutil.which("mktorrent"):
        raise OSError("mktorrent not found")
    tracker_announce = "-a " + " -a ".join(tracker_announce_list)
    cmd = f'mktorrent "{vidfile}" {tracker_announce} -l {chunk_factor} -o "{torrent_path}"'
    log.info(f"Running\n    {cmd}")
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
    cmd = f'static_ffmpeg -hide_banner -i "{videopath}" -vf scale="trunc(oh*a/2)*2:{height}" {downmix_stmt} -movflags +faststart -preset {ENCODER_PRESET} -c:v libx264 -crf {crf} "{outpath}" -y'  # pylint: disable=line-too-long
    log.info(f"Running:\n  {cmd}")
    proc = subprocess.Popen(cmd, shell=True)
    proc.wait()
    log.info("Generated file: " + outpath)


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
) -> str:
    """Generates the webtorrent files for a given video file."""
    assert tracker_announce_list
    os.makedirs(out_dir, exist_ok=True)
    original_video_height = get_video_height(vidfile)
    html_path = os.path.join(out_dir, "index.html")
    http_type = "http" if "localhost" in domain_name else "https"
    vidpath = sanitize_path(vid_name)

    base_video_path = f"{http_type}://{domain_name}/v/{vidpath}"

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
        webseed = f"{base_video_path}/{height}.mp4"
        torrent_url = f"{base_video_path}/{height}.torrent"
        return dict(
            height=height,
            duration=duration,
            size=size_mp4file,
            file_url=webseed,
            torrent_url=torrent_url,
        )

    tasks = []
    for height in ENCODING_HEIGHTS:
        if do_encode:
            if height > original_video_height:
                continue  # Don't encode if the height is greater than the original.
        height = original_video_height if not do_encode else height
        basename = os.path.join(out_dir, f"{height}")
        task = executor.submit(
            encoding_task,
            vidfile,
            ENCODING_CRF,
            height,
            basename + ".mp4",
            basename + ".torrent",
        )
        tasks.append(task)
        if not do_encode:
            break  # It's just a copy, so we only need to do one encoding.

    completed_vids: list[dict] = [task.result() for task in tasks]
    vidfolder = os.path.dirname(vidfile)
    subtitles_dir = os.path.join(vidfolder, "subtitles")
    log.info(f"Subtitles dir: {subtitles_dir}")
    url_slug = f"/v/{vidpath}"
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
        "note": "This is a sample and should be overriden during the video creation process",
        "name": vidpath,
        "urlslug": url_slug,
        "url": base_video_path,
        "domain": domain_name,
        "videos": completed_vids,
        "subtitles": subtitles,
        "poster": f"{base_video_path}/thumbnail.jpg",
        "todo": "Let's also have bitchute: <URL> and rumble <URL>",
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
def async_create_webtorrent_files(
    vid_name: str,
    vidfile: str,
    domain_name: str,
    tracker_announce_list: List[str],
    stun_servers: str,
    out_dir: str,
    chunk_factor: int = 17,
    do_encode: bool = False,
) -> str:
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
    for file in ["test.mp4"]:
        src = os.path.join(TESTS_DATA, file)
        dst = os.path.join(demo_dir, file)
        if os.path.exists(src):
            shutil.copy(src, dst)
        else:
            warnings.warn(f"Missing {src}")
