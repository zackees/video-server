"""
Database abstraction layer.
"""

import os
import shutil
from typing import List, Optional

from fastapi import File, UploadFile
from fastapi.responses import PlainTextResponse


from video_server.generate_files import async_create_webtorrent_files
from video_server.settings import (
    DATA_ROOT,
    DOMAIN_NAME,
    STUN_SERVERS,
    TRACKER_ANNOUNCE_LIST,
    VIDEO_ROOT,
    WWW_ROOT,
)
from video_server.io import sanitze_path
from video_server.asyncwrap import asyncwrap

CHUNK_SIZE = 1024 * 1024


def path_to_url(full_path: str) -> str:
    """Returns the path to the www directory."""
    if "localhost" in DOMAIN_NAME:
        domain_url = f"http://{DOMAIN_NAME}"
    else:
        domain_url = f"https://{DOMAIN_NAME}"
    full_path = full_path.replace("\\", "/")  # Normalize forward slash
    rel_path = full_path.replace(WWW_ROOT, "")
    if rel_path.startswith("/"):
        rel_path = rel_path[1:]
    file = f"{domain_url}/{rel_path}"
    return file


def db_query_videos() -> List[str]:
    """Returns a list of videos in the video directory."""
    videos = [d for d in os.listdir(VIDEO_ROOT) if os.path.isdir(os.path.join(VIDEO_ROOT, d))]
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
    file: UploadFile = File(...),
    subtitles_zip: Optional[UploadFile] = File(None),
    do_encode: bool = False,
) -> PlainTextResponse:
    """Uploads a file to the server."""
    file_ext = os.path.splitext(file.filename)
    if len(file_ext) != 2:
        return PlainTextResponse(content=f"Invalid file extension for {file}", status_code=415)
    ext = file_ext[1].lower()
    if ext in ["mp4", "mkv", "webm"]:
        return PlainTextResponse(
            status_code=415, content="Invalid file type, must be mp4, mkv or webm"
        )
    if not os.path.exists(DATA_ROOT):
        return PlainTextResponse(
            status_code=500,
            content=f"File upload not enabled because DATA_ROOT {DATA_ROOT} does not exist",
        )
    # Use the name of the file as the folder for the new content.
    print(f"Uploading file: {file.filename}")
    # Sanitize the titles to be a valid folder name
    video_dir = to_video_dir(title)
    subtitle_dir = os.path.join(video_dir, "subtitles")
    if os.path.exists(video_dir):
        return PlainTextResponse(status_code=409, content=f"Video {title} already exists")
    os.makedirs(video_dir)
    final_path = os.path.join(video_dir, "vid.mp4")
    await async_download(file, final_path)
    if subtitles_zip is not None:
        print(f"Uploading subtitles: {subtitles_zip.filename}")
        await async_download(subtitles_zip, os.path.join(video_dir, "subtitles.zip"))

        @asyncwrap
        def async_unpack_subtitles():
            shutil.unpack_archive(os.path.join(video_dir, "subtitles.zip"), subtitle_dir)
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
    url = path_to_url(os.path.dirname(final_path))
    return PlainTextResponse(content=f"Video Created!: {url}")
