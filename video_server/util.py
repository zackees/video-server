"""
Misc utility functions.
"""
import asyncio
import os
import shutil
import subprocess
import urllib.parse
from typing import Tuple

import requests  # type: ignore
from PIL import Image  # type: ignore

from fastapi import UploadFile
from video_server.settings import SERVER_PORT, ENCODER_PRESET
from video_server.log import log
from video_server.asyncwrap import asyncwrap

CHUNK_SIZE = 1024 * 64


def get_video_url(url: str) -> str:
    """Return the video url."""
    if SERVER_PORT == 80:
        return url
    # parse url into parts
    parts = urllib.parse.urlparse(url)
    # replace the port
    new_parts = parts._replace(netloc=f"{parts.hostname}:{SERVER_PORT}")
    # rebuild the url
    url = urllib.parse.urlunparse(new_parts)
    return url


async def async_download(src: UploadFile, dst: str) -> None:
    """Downloads a file to the destination."""
    with open(dst, mode="wb") as filed:
        while (chunk := await src.read(CHUNK_SIZE)) != b"":
            filed.write(chunk)
    await src.close()


def download_file(url: str, outfile: str) -> None:
    """Download a file."""
    req = requests.get(url, timeout=10)
    log.info("Downloading %s to %s", url, outfile)
    with open(outfile, "wb") as filed:
        for chunk in req.iter_content(chunk_size=512 * 1024):
            if chunk:  # filter out keep-alive new chunks
                filed.write(chunk)
        filed.close()


async def make_thumbnail(vidpath: str, out_thumbnail: str) -> None:
    """Makes a thumbnail from the first frame of the video."""
    # Make thumbnail
    cmd = [
        "static_ffmpeg",
        "-i",
        vidpath,
        "-vf",
        "select=eq(n\\,0)",
        "-q:v",
        "3",
        out_thumbnail,
    ]
    log.info("Creating thumbnail with cmd:\n  %s", cmd)
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        log.error("Failed to create thumbnail")
        log.error("stdout: %s", stdout)
        log.error("stderr: %s", stderr)
        raise ValueError("Failed to create thumbnail")
    log.info("Created thumbnail")


def get_image_size(fname: str) -> Tuple[int, int]:
    """Returns the width and the height of the image"""
    with Image.open(fname) as img:
        width, height = img.size
    return width, height


@asyncwrap
def async_get_image_size(fname: str) -> Tuple[int, int]:
    """Async version of get_image_size"""
    return get_image_size(fname)


def encode(videopath: str, crf: int, height: int, outpath: str) -> None:
    """Encodes a video"""
    downmix_stmt = "-ac 1" if height <= 480 else ""
    # trunc(oh*...) fixes issue with libx264 encoder not liking an add number of width pixels.
    cmd = f'static_ffmpeg -hide_banner -i "{videopath}" -vf scale="trunc(oh*a/2)*2:{height}" {downmix_stmt} -movflags +faststart -preset {ENCODER_PRESET} -c:v libx264 -crf {crf} "{outpath}" -y'  # pylint: disable=line-too-long
    log.info("Running:\n  %s", cmd)
    proc = subprocess.Popen(cmd, shell=True)  # pylint: disable=consider-using-with
    proc.wait()
    log.info("Generated file: %s", outpath)


@asyncwrap
def async_encode(videopath: str, crf: int, height: int, outpath: str) -> None:
    """Async version of encode."""
    encode(videopath, crf, height, outpath)


def get_video_height(vidfile: str) -> int:
    """Gets the video height from the video file."""
    # use ffprobe to get the height of the video
    assert os.path.exists(vidfile)
    cmd = f'static_ffprobe "{vidfile}" -show_streams 2>&1'
    stdout = subprocess.check_output(cmd, shell=True)
    lines = stdout.decode().splitlines()
    for line in lines:
        if line.startswith("height"):
            height = int(line.split("=")[1])
            return height
    raise ValueError(f"Missing height in {vidfile}")


@asyncwrap
def async_get_video_height(vidfile: str) -> int:
    """Async version of get_video_height."""
    return get_video_height(vidfile)


def mktorrent(
    vidfile: str, torrent_path: str, tracker_announce_list: list[str], chunk_factor: int
) -> None:
    """Creates a torrent file."""
    # if windows
    if os.name == "nt":
        log.error("mktorrent not supported on windows")
        return
    log.info("Creating torrent for %s", os.path.abspath(vidfile))
    if os.path.exists(torrent_path):
        os.remove(torrent_path)
    # Use which to detect whether the mktorrent binary is available.
    if not shutil.which("mktorrent"):
        raise OSError("mktorrent not found")
    tracker_announce = "-a " + " -a ".join(tracker_announce_list)
    cmd = f'mktorrent "{vidfile}" {tracker_announce} -l {chunk_factor} -o "{torrent_path}"'
    log.info("Running\n    %s", cmd)
    # subprocess.check_output(cmd, shell=True)
    os.system(cmd)
    log.info("Created torrent: %s", os.path.abspath(torrent_path))
    assert os.path.exists(torrent_path), f"Missing expected {torrent_path}"


def query_duration(vidfile: str) -> float:
    """Queries the duration of a video."""
    assert os.path.exists(vidfile)
    cmd = f'static_ffprobe "{vidfile}" -show_format 2>&1'
    stdout = subprocess.check_output(cmd, shell=True)
    lines = stdout.decode().splitlines()
    duration: float | None = None
    for line in lines:
        if line.startswith("duration"):
            duration = float(line.split("=")[1])
            break
    assert duration is not None, f"Missing duration in {vidfile}"
    return duration


def mktorrent_task(  # pylint: disable=too-many-arguments
    vidfile, torrent_path, tracker_announce_list, chunk_factor, webseed, torrent_url
):
    """Creates a torrent file."""
    mktorrent(
        vidfile=vidfile,
        torrent_path=torrent_path,
        tracker_announce_list=tracker_announce_list,
        chunk_factor=chunk_factor,
    )
    size_mp4file = os.path.getsize(vidfile)
    duration: float = query_duration(vidfile)
    height: int = get_video_height(vidfile)
    return dict(
        height=height,
        duration=duration,
        size=size_mp4file,
        file_url=webseed,
        torrent_url=torrent_url,
    )


def has_audio(vidfile: str) -> bool:
    """Checks if a video file has audio."""
    cmd = (
        "ffprobe -v error -select_streams a:0 -show_entries"
        f" stream=codec_type -of default=noprint_wrappers=1:nokey=1 {vidfile}"
    )
    stdout = subprocess.check_output(cmd, shell=True, universal_newlines=True)
    return stdout.strip() == "audio"


class Cleanup:
    """Cancellable cleanup function"""

    def __init__(self, cleanup_fcn) -> None:
        self.cleanup = True
        self.cleanup_fcn = cleanup_fcn

    def cancel(self) -> None:
        """Cancel cleanup."""
        self.cleanup = False

    def __del__(self):
        """Trigger cleanup."""
        if self.cleanup:
            self.cleanup_fcn()
