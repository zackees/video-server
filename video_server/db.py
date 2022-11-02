"""
Database abstraction layer.
"""

# pylint: disable=too-many-arguments,too-many-return-statements,too-many-locals,logging-fstring-interpolation,disable=no-value-for-parameter
# flake8: noqa: E231
import asyncio
import os
import shutil
from typing import List, Optional, Tuple
from datetime import datetime, timedelta

from fastapi import File, UploadFile
from fastapi.responses import PlainTextResponse
from PIL import Image  # type: ignore
from peewee import ModelSelect  # type: ignore

from video_server.asyncwrap import asyncwrap
from video_server.generate_files import async_create_webtorrent_files
from video_server.io import sanitize_path
from video_server.settings import (
    DATA_ROOT,
    DOMAIN_NAME,
    STUN_SERVERS,
    TRACKER_ANNOUNCE_LIST,
    VIDEO_ROOT,
    WWW_ROOT,
    MAX_BAD_LOGINS,
    MAX_BAD_LOGINS_RESET_TIME,
    WEBTORRENT_CHUNK_FACTOR,
)
from video_server.util import get_video_url
from video_server.models import Video, db_proxy, BadLogin
from video_server.log import log

CHUNK_SIZE = 1024 * 1024


def can_login() -> bool:
    """Returns true if the user can attempt to login."""
    # remove all bad login attempts older than MAX_BAD_LOGINS_RESET_TIME
    with db_proxy.atomic():
        oldest_allowed = datetime.now() - timedelta(seconds=MAX_BAD_LOGINS_RESET_TIME)
        oldest = BadLogin.select().where(BadLogin.created < oldest_allowed)
        for bad_login in oldest:  # pylint: disable=not-an-iterable
            bad_login.delete_instance()
        num_bad_logins = (
            BadLogin.select().count()
        )
        return num_bad_logins < MAX_BAD_LOGINS


def add_bad_login() -> None:
    """Add a bad login."""
    BadLogin.create()


def path_to_url(path: str) -> str:
    """Returns the path to the www directory."""
    if "localhost" in DOMAIN_NAME:
        domain_url = f"http://{DOMAIN_NAME}"
    else:
        domain_url = f"https://{DOMAIN_NAME}"
    path = path.replace("\\", "/")  # Normalize forward slash
    rel_path = path.replace(WWW_ROOT, "")
    if rel_path.startswith("/"):
        rel_path = rel_path[1:]
    file = f"{domain_url}/{rel_path}"
    return file


def db_list_all_files() -> List[str]:
    """Dumps all files in the http directory."""
    files = []
    for dir_name, _, file_list in os.walk(WWW_ROOT):
        for filename in file_list:
            file = os.path.join(dir_name, filename)
            files.append(file)
    return files


async def async_download(src: UploadFile, dst: str) -> None:
    """Downloads a file to the destination."""
    with open(dst, mode="wb") as filed:
        while (chunk := await src.read(1024 * 64)) != b"":
            filed.write(chunk)
    await src.close()
    return None


def to_video_dir(title: str) -> str:
    """Returns the video directory for a title."""
    return os.path.join(VIDEO_ROOT, sanitize_path(title))


def get_image_size(fname) -> Tuple[int, int]:
    """Returns the width and the height of the image"""
    with Image.open(fname) as img:
        width, height = img.size
    return width, height

async def make_thumbnail(final_path, out_thumbnail):
    """Makes a thumbnail from the first frame of the video."""
    # Make thumbnail
    cmd = [
        "static_ffmpeg",
        "-i",
        final_path,
        "-vf",
        "select=eq(n\\,0)",
        "-q:v",
        "3",
        out_thumbnail,
    ]
    # os.system('ffmpeg -i inputfile.mkv -vf "select=eq(n\,0)" -q:v 3 output_image.jpg')
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
        return PlainTextResponse(
            status_code=500,
            content="Failed to create thumbnail",
        )
    log.info("Created thumbnail")

async def db_add_video(  # pylint: disable=too-many-branches
    title: str,
    description: str,
    file: UploadFile = File(...),
    thumbnail: UploadFile = File(None),
    subtitles_zip: Optional[UploadFile] = File(None),
    do_encode: bool = False,
) -> PlainTextResponse:
    """Uploads a file to the server."""
    file_ext = os.path.splitext(file.filename)
    if len(file_ext) != 2:
        return PlainTextResponse(
            content=f"Invalid file extension for {file}", status_code=415
        )
    ext = file_ext[1].lower()
    if do_encode:
        if ext not in [".mp4", ".mkv", ".webm"]:
            return PlainTextResponse(
                status_code=415,
                content=f"Invalid file type, must be mp4, mkv or webm, instead it was {ext}",
            )
    else:
        if ext != ".mp4":
            return PlainTextResponse(
                status_code=415,
                content=f"Invalid file type, must be mp4, instead it was {ext}",
            )
    if not os.path.exists(DATA_ROOT):
        return PlainTextResponse(
            status_code=500,
            content=f"File upload not enabled because DATA_ROOT {DATA_ROOT} does not exist",
        )
    vid: ModelSelect = Video.select().where(Video.title == title)
    if vid.exists():
        return PlainTextResponse(
            status_code=409, content=f"Video {title} already exists"
        )
    video_dir = to_video_dir(title)
    os.makedirs(video_dir)

    # Use the name of the file as the folder for the new content.
    log.info(f"Uploading file: {file.filename}")
    # Sanitize the titles to be a valid folder name
    subtitle_dir = os.path.join(video_dir, "subtitles")

    final_path = os.path.join(video_dir, "vid.mp4")
    await async_download(file, final_path)
    if subtitles_zip is not None:
        log.info(f"Uploading subtitles: {subtitles_zip.filename}")
        await async_download(subtitles_zip, os.path.join(video_dir, "subtitles.zip"))

        @asyncwrap
        def async_unpack_subtitles():
            shutil.unpack_archive(
                os.path.join(video_dir, "subtitles.zip"), subtitle_dir
            )
            os.remove(os.path.join(video_dir, "subtitles.zip"))

        await async_unpack_subtitles()

    # Make thumbnail
    out_thumbnail = os.path.join(video_dir, "thumbnail.jpg")
    if thumbnail:
        log.info(f"Thumbnail: {thumbnail.filename}")
        thumbnail_name_ext = os.path.splitext(thumbnail.filename)
        if len(thumbnail_name_ext) != 2:
            return PlainTextResponse(
                content=f"Invalid file extension for {thumbnail}", status_code=415
            )
        thumbnail_ext = thumbnail_name_ext[1].lower()
        if thumbnail_ext != ".jpg":
            return PlainTextResponse(
                status_code=415,
                content=f"Invalid thumbnail type, must be .jpg, instead it was {thumbnail_ext}",
            )
        await async_download(thumbnail, out_thumbnail)
        thumbnail_width, thumbnail_height = get_image_size(out_thumbnail)
        if thumbnail_width > 1280 or thumbnail_height > 720:
            return PlainTextResponse(
                status_code=415,
                content=(
                    f"Invalid thumbnail size, can't be larger than 1280x720, instead it was "
                    f"{thumbnail_width}x{thumbnail_height}"
                ),
            )
    else:
        await make_thumbnail(final_path, out_thumbnail)
    # TODO: Final check, use ffprobe to check if it is a valid mp4 file that can be  # pylint: disable=fixme
    # streamed.

    relpath = os.path.relpath(final_path, WWW_ROOT)
    url = path_to_url(os.path.dirname(relpath))
    vid_id = Video.create(
        title=title, url=url, description=description, path=final_path, iframe=url
    ).id

    await async_create_webtorrent_files(
        vid_name=title,
        vid_id=vid_id,
        vidfile=final_path,
        domain_name=DOMAIN_NAME,
        tracker_announce_list=TRACKER_ANNOUNCE_LIST,
        stun_servers=STUN_SERVERS,
        out_dir=video_dir,
        chunk_factor=WEBTORRENT_CHUNK_FACTOR,
        do_encode=do_encode,
    )

    return PlainTextResponse(content=f"Video Created!: {get_video_url(url)}")
