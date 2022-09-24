"""
Database abstraction layer.
"""

# pylint: disable=too-many-arguments,too-many-return-statements,too-many-locals,logging-fstring-interpolation
# flake8: noqa: E231

import os
import shutil
from typing import List, Optional
from datetime import datetime, timedelta

from fastapi import File, UploadFile
from fastapi.responses import PlainTextResponse

from peewee import ModelSelect  # type: ignore

from video_server.asyncwrap import asyncwrap
from video_server.generate_files import async_create_webtorrent_files
from video_server.io import sanitze_path
from video_server.settings import (
    DATA_ROOT,
    DOMAIN_NAME,
    STUN_SERVERS,
    TRACKER_ANNOUNCE_LIST,
    VIDEO_ROOT,
    WWW_ROOT,
    MAX_BAD_LOGINS,
    MAX_BAD_LOGINS_RESET_TIME,
)

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
        num_bad_logins = BadLogin.select().count()  # pylint: disable=no-value-for-parameter
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


def db_query_videos() -> List[str]:
    """Returns a list of videos in the video directory."""
    videos = [
        d for d in os.listdir(VIDEO_ROOT) if os.path.isdir(os.path.join(VIDEO_ROOT, d))
    ]
    return sorted(videos)


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
    return os.path.join(VIDEO_ROOT, sanitze_path(title))


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
    else:
        pixel_data_jpg_1x1_black = [
            137,
            80,
            78,
            71,
            13,
            10,
            26,
            10,
            0,
            0,
            0,
            13,
            73,
            72,
            68,
            82,
            0,
            0,
            0,
            1,
            0,
            0,
            0,
            1,
            8,
            2,
            0,
            0,
            0,
            144,
            119,
            83,
            222,
            0,
            0,
            0,
            1,
            115,
            82,
            71,
            66,
            0,
            174,
            206,
            28,
            233,
            0,
            0,
            0,
            12,
            73,
            68,
            65,
            84,
            24,
            87,
            99,
            136,
            89,
            39,
            8,
            0,
            2,
            133,
            1,
            28,
            26,
            189,
            185,
            242,
            0,
            0,
            0,
            0,
            73,
            69,
            78,
            68,
            174,
            66,
            96,
            130,
        ]
        with open(out_thumbnail, "wb") as filed:
            filed.write(bytes(pixel_data_jpg_1x1_black))
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
    # TODO: Final check, use ffprobe to check if it is a valid mp4 file that can be  # pylint: disable=fixme
    # streamed.
    await async_create_webtorrent_files(
        vid_name=title,
        vidfile=final_path,
        domain_name=DOMAIN_NAME,
        tracker_announce_list=TRACKER_ANNOUNCE_LIST,
        stun_servers=STUN_SERVERS,
        out_dir=video_dir,
        do_encode=do_encode,
    )
    relpath = os.path.relpath(final_path, DATA_ROOT)  
    url = path_to_url(os.path.dirname(relpath))
    Video.create(
        title=title, url=url, description=description, path=final_path, iframe=url
    )
    return PlainTextResponse(content=f"Video Created!: {url}")
