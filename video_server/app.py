"""
    Fastapi server
"""

# pylint: disable=fixme,broad-except,logging-fstring-interpolation,too-many-locals,redefined-builtin,invalid-name,too-many-branches,too-many-return-statements
import asyncio
import datetime
import hashlib
import os
import shutil
import threading
import time
import traceback
import subprocess
import json
from tempfile import TemporaryDirectory
from typing import Optional, Tuple

import uvicorn  # type: ignore
import httpx
from fastapi import BackgroundTasks, FastAPI, File, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
    Response,
    StreamingResponse,
)
from fastapi.security import HTTPBasic
from fastapi.staticfiles import StaticFiles
from filelock import FileLock, Timeout
from PIL import Image  # type: ignore
from httpx import AsyncClient
from keyvalue_sqlite import KeyValueSqlite  # type: ignore
from starlette.background import BackgroundTask

from video_server.asyncwrap import asyncwrap
from video_server.db import (
    db_list_all_files,
    path_to_url,
    to_video_dir,
    can_login,
    add_bad_login,
)
from video_server.generate_files import (
    init_static_files,
    create_metadata_files,
    async_create_metadata_files,
)
from video_server.log import log
from video_server.models import Video
from video_server.rss import rss
from video_server.settings import (  # STUN_SERVERS,; TRACKER_ANNOUNCE_LIST,
    APP_DB,
    DATA_ROOT,
    DISABLE_AUTH,
    DOMAIN_NAME,
    FILE_PORT,
    IS_TEST,
    LOGFILE,
    PASSWORD,
    PROJECT_ROOT,
    SERVER_PORT,
    STARTUP_LOCK,
    STUN_SERVERS,
    TRACKER_ANNOUNCE_LIST,
    VIDEO_ROOT,
    WEBTORRENT_CHUNK_FACTOR,
    WWW_ROOT,
    HEIGHTS,
    ENCODING_CRF,
)

from video_server.util import (
    get_video_url,
    async_download,
    make_thumbnail,
    async_get_image_size,
    async_encode,
    async_get_video_height,
    Cleanup,
    download_file,
)
from video_server.version import VERSION

# from fastapi.responses import StreamingResponse
# from starlette.requests import Request


class RssResponse(Response):  # pylint: disable=too-few-public-methods
    """Returns an RSS response from a query."""

    media_type = "application/xml"
    charset = "utf-8"


HTTP_SERVER = AsyncClient(base_url=f"http://localhost:{FILE_PORT}/")

log.info("Starting fastapi webtorrent movie server")


app_state = KeyValueSqlite(APP_DB, "app")
# VIDEO_ROOT = os.path.join(DATA_ROOT, "v")
startup_lock = FileLock(STARTUP_LOCK)


app = FastAPI()

security = HTTPBasic()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STARTUP_DATETIME = datetime.datetime.now()


def get_current_thread_id() -> int:
    """Return the current thread id."""
    ident = threading.current_thread().ident
    if ident is None:
        return -1
    return int(ident)


def is_authorized(request: Request) -> bool:
    """Check if the user is authorized."""
    if DISABLE_AUTH:
        return True
    cookie_password = request.cookies.get("password")
    return digest_equals(cookie_password, PASSWORD)


def digest_equals(password, password_compare) -> bool:
    """Compare the password."""
    if password is None:
        return False
    return (
        hashlib.sha256(password.encode()).hexdigest()
        == hashlib.sha256(password_compare.encode()).hexdigest()
    )


@app.on_event("startup")
def startup_event():
    """Event handler for when the app starts up."""
    log.info("Startup event")
    try:
        with startup_lock.acquire(timeout=10):
            init_static_files(WWW_ROOT)
    except Timeout:
        log.error("Startup lock timeout")


@app.on_event("shutdown")
def shutdown_event():
    """Event handler for when the app shuts down."""
    log.info("Application shutdown")


# Mount all the static files.
app.mount("/www", StaticFiles(directory=WWW_ROOT, html=True), "www")


@app.get("/", include_in_schema=False)
async def index() -> RedirectResponse:
    """By default redirect to the fastapi docs."""
    return RedirectResponse(url="/docs", status_code=302)


# Redirect to favicon.ico
@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> RedirectResponse:
    """Returns favico file."""
    return RedirectResponse(url="/www/favicon.ico")


@app.post("/login", tags=["Public"])
def login(password: str) -> PlainTextResponse:
    """Use the login password to get a cookie."""
    if DISABLE_AUTH:
        return PlainTextResponse("Login ok - auth disabled so any password is ok")
    if not can_login():
        return PlainTextResponse(
            "Too many failed login attempts. Please try again later."
        )
    try:
        if not digest_equals(password, PASSWORD):
            add_bad_login()
            resp = PlainTextResponse("Bad login.")
            resp.delete_cookie(key="password")
            return resp
        # Set cookie for password
        resp = PlainTextResponse("Login successful", status_code=200)
        resp.set_cookie(key="password", value=PASSWORD, httponly=True)
        return resp
    except Exception as exc:
        stack_trace = traceback.format_exc()
        return PlainTextResponse(f"{exc}\n\n{stack_trace}:", status_code=500)


@app.get("/info")
async def api_info(request: Request) -> JSONResponse:
    """Returns the current time and the number of seconds since the server started."""
    if not is_authorized(request):
        return JSONResponse({"error": "Not Authorized"}, status_code=401)
    app_data = app_state.to_dict()
    links = [get_video_url(video.url) for video in Video.select()]
    out = {
        "version": VERSION,
        "Launched at": str(STARTUP_DATETIME),
        "Current utc time": str(datetime.datetime.utcnow()),
        "Process ID": os.getpid(),
        "Thread ID": get_current_thread_id(),
        "Number of Views": app_data.get("views", 0),
        "App state": app_data,
        "PROJECT_ROOT": PROJECT_ROOT,
        "DATA_ROOT": DATA_ROOT,
        "WWW_ROOT": WWW_ROOT,
        "VIDEO_ROOT": VIDEO_ROOT,
        "LOGFILE": LOGFILE,
        "Links": links,
        "DOMAIN_NAME": DOMAIN_NAME,
    }
    return JSONResponse(out)


@app.get("/videos")
async def list_videos() -> PlainTextResponse:
    """Reveals the videos that are available."""
    links = [get_video_url(video.url) for video in Video.select()]
    return PlainTextResponse(content="\n".join(links))


@app.put("/add_view/{id}")
async def add_view(
    id: int,  # pylint: disable=redefined-builtin,invalid-name
) -> PlainTextResponse:
    """Adds a view to the app state."""
    try:
        Video.update(views=Video.views + 1).where(Video.id == id).execute()
        return PlainTextResponse("View added")
    except Exception as exc:
        return PlainTextResponse(f"Error adding view because {exc}")


@app.get("/rss")
async def rss_feed() -> RssResponse:
    """Returns an RSS feed of the videos."""
    return RssResponse(rss(channel_name="Video Channel"))


@app.get("/json")
async def json_feed() -> JSONResponse:
    """Returns an RSS feed of the videos."""
    out = []
    for video in Video.select():
        out.append(video.asjson())
    return JSONResponse(out)


@app.get("/list_all_files")
def list_all_files(request: Request) -> JSONResponse:
    """List all files in a directory."""
    if not is_authorized(request):
        return JSONResponse({"error": "Not Authorized"}, status_code=401)
    urls = [path_to_url(file) for file in db_list_all_files()]
    return JSONResponse(urls)


@app.post("/upload")
async def upload(  # pylint: disable=too-many-branches,too-many-arguments,too-many-statements
    request: Request,
    title: str,
    description: str = "",
    file: UploadFile = File(...),
    thumbnail: UploadFile = File(None),
    subtitles_zip: Optional[UploadFile] = File(None),
    do_encode: bool = False,
) -> PlainTextResponse:
    """Uploads a file to the server."""
    if not is_authorized(request):
        return PlainTextResponse("error: Not Authorized", status_code=401)
    # TODO: Use stream files, large files exhaust the ram.
    # This can be fixed by applying the following fix:
    # https://github.com/tiangolo/fastapi/issues/58
    # check to see if the video titles exists
    if Video.select().where(Video.title == title).exists():
        return PlainTextResponse(
            content=f'Video with title "{title}" already exists', status_code=409
        )
    # Check that the upload file is valid
    file_ext = os.path.splitext(file.filename)  # type: ignore
    if len(file_ext) != 2:
        return PlainTextResponse(
            content=f"Invalid file extension for {file}", status_code=415
        )
    ext = file_ext[1].lower()
    # Check if the file is a valid type
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
    log.info(f"Uploading file: {file.filename}")  # type: ignore
    video_dir = to_video_dir(title)
    try:
        os.makedirs(video_dir)
        # pylint: disable-next=unused-variable
        cleanup = Cleanup(cleanup_fcn=lambda: shutil.rmtree(video_dir))
    except FileExistsError:
        return PlainTextResponse(
            content=f'Video with title "{title}" already exists', status_code=409
        )
    subtitle_dir = os.path.join(video_dir, "subtitles")
    # final_path = os.path.join(video_dir, "vid.mp4")
    with TemporaryDirectory() as temp_dir:
        temp_path: str = os.path.join(temp_dir, "vid.mp4")
        await async_download(file, temp_path)
        height = await async_get_video_height(temp_path)
        final_path: str = os.path.join(video_dir, f"{height}.mp4")
        shutil.move(temp_path, final_path)

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
        thumbnail_width, thumbnail_height = await async_get_image_size(out_thumbnail)
        if thumbnail_width > 1280 or thumbnail_height > 720:
            return PlainTextResponse(
                status_code=415,
                content=(
                    f"Invalid thumbnail size, can't be larger than 1280x720, instead it was "
                    f"{thumbnail_width}x{thumbnail_height}"
                ),
            )
    else:
        try:
            await make_thumbnail(vidpath=final_path, out_thumbnail=out_thumbnail)
        except ValueError as exc:
            return PlainTextResponse(
                status_code=415,
                content=f"Error making thumbnail: {exc}",
            )

    relpath = os.path.relpath(final_path, WWW_ROOT)
    url = path_to_url(os.path.dirname(relpath))
    vid_id = Video.create(
        title=title, url=url, description=description, path=final_path, iframe=url
    ).id
    native_size = await async_get_video_height(final_path)
    vidfiles: list[str] = []
    vidfiles.append(final_path)
    if do_encode:
        base_path = os.path.dirname(final_path)
        for height in HEIGHTS:
            if native_size != height and height < native_size:
                outpath = os.path.join(base_path, f"{height}.mp4")
                vidfiles.append(outpath)
                await async_encode(
                    videopath=final_path,
                    crf=ENCODING_CRF,
                    height=height,
                    outpath=outpath,
                )
    await async_create_metadata_files(
        vid_id=vid_id,
        vid_title=title,
        vidfiles=vidfiles,
        domain_name=DOMAIN_NAME,
        tracker_announce_list=TRACKER_ANNOUNCE_LIST,
        stun_servers=STUN_SERVERS,
        out_dir=video_dir,
        chunk_factor=WEBTORRENT_CHUNK_FACTOR,
    )
    cleanup.cancel()
    return PlainTextResponse(f"Created video at {get_video_url(url)}")


@app.post("/upload_url")
def upload_url(  # pylint: disable=too-many-statements
    request: Request, url: str
) -> PlainTextResponse:
    """Uploads a file to the server."""
    if not is_authorized(request):
        return PlainTextResponse("error: Not Authorized", status_code=401)
    cmd = f"yt-dlp {url} -J"
    log.info(f"Running command:\n  {cmd}")
    stdout = subprocess.check_output(cmd, shell=True, universal_newlines=True)
    info = json.loads(stdout)
    formats = info.get("formats")
    title = info.get("title")
    thumbnail = info.get("thumbnail")
    has_drm = info.get("__has_drm")
    if not formats:
        return PlainTextResponse(
            "Can't download video - No formats found", status_code=406
        )
    if not title:
        return PlainTextResponse(
            "Can't download video - No title found", status_code=406
        )
    if not thumbnail:
        return PlainTextResponse(
            "Can't download video - No thumbnail found", status_code=406
        )
    if has_drm:
        return PlainTextResponse(
            "Can't download video - DRM protected", status_code=406
        )
    video_dir = to_video_dir(title)
    try:
        os.makedirs(video_dir)
        cleanup = Cleanup(cleanup_fcn=lambda: shutil.rmtree(video_dir))
    except FileExistsError:
        return PlainTextResponse(
            f"error: Video with title '{title}' already exists", status_code=409
        )
    # Gather the mp4 format videos
    vidinfos: list[Tuple[int, str | None]] = []
    for fmts in formats:
        if "mp4" in fmts.get("ext", ""):
            key = int(fmts.get("height", 0))
            tmp_id: str | None = fmts.get("format_id")
            vidinfos.append((key, tmp_id))
    # sort so that the largest is first
    vidinfos.sort(key=lambda x: x[0])
    sizemap: dict[int, str | None] = {key: None for key in HEIGHTS}
    # Match the resolutions to the videos, rounding up when
    # necessary.
    sorted_heights = list(HEIGHTS)
    sorted_heights.sort(reverse=True)
    for key in sorted_heights:
        for i, resolution in enumerate(vidinfos):
            if resolution[0] >= key:
                vid_data = vidinfos[i][1]
                if vid_data in sizemap.values():
                    continue
                sizemap[key] = vid_data
                break
    if not [x for x in sizemap.values() if x]:
        return PlainTextResponse(
            "Can't download video - No suitable formats found", status_code=501
        )
    # Download videos and store their paths in the downloaded_files.
    downloaded_files: list[str] = []
    for resolution in sizemap.keys():  # type: ignore
        id = sizemap[resolution]  # type: ignore
        if id is not None:
            filename = os.path.join(video_dir, f"{resolution}.mp4")
            cmd = f'yt-dlp --no-check-certificate {url} -f "{id}" -o "{filename}"'
            log.info(f"Running command:\n  {cmd}")
            stdout = subprocess.check_output(cmd, shell=True, universal_newlines=True)
            log.info(stdout)
            downloaded_files.append(filename)
            log.info(f"Downloaded {filename}")
    log.info(f"Done downloading: {url}")
    subtitle_dir = os.path.join(  # noqa: F841  # pylint: disable=unused-variable
        video_dir, "subtitles"
    )
    final_path = os.path.join(video_dir, "vid.mp4")
    relpath = os.path.relpath(final_path, WWW_ROOT)
    url = path_to_url(os.path.dirname(relpath))
    thumbnail_ext = os.path.splitext(thumbnail)[1]
    with TemporaryDirectory() as tmpdir:
        tmpfile = os.path.join(tmpdir, f"thumbnail{thumbnail_ext}")
        download_file(thumbnail, tmpfile)
        if thumbnail_ext != ".jpg":
            # convert to jpg
            img = Image.open(tmpfile)
            img.save(os.path.join(tmpdir, "thumbnail.jpg"), "JPEG")
            shutil.copy(
                os.path.join(tmpdir, "thumbnail.jpg"),
                os.path.join(video_dir, "thumbnail.jpg"))
        else:
            shutil.copy(tmpfile, os.path.join(video_dir, "thumbnail.jpg"))
    vid_id = Video.create(
        title=title,
        url=url,
        description="TODO - Implement description scraping",
        path=final_path,
        iframe=url,
    ).id
    create_metadata_files(
        vid_id=vid_id,
        vid_title=title,
        vidfiles=downloaded_files,
        domain_name=DOMAIN_NAME,
        tracker_announce_list=TRACKER_ANNOUNCE_LIST,
        stun_servers=STUN_SERVERS,
        out_dir=video_dir,
        chunk_factor=WEBTORRENT_CHUNK_FACTOR,
    )
    cleanup.cancel()
    return PlainTextResponse(f"Created video at {get_video_url(url)}")


@app.delete("/delete")
async def delete(
    password: str, title: str, background_tasks: BackgroundTasks
) -> PlainTextResponse:
    """Clears the stored magnet URI."""
    if not DISABLE_AUTH and not digest_equals(password, PASSWORD):
        return PlainTextResponse("error: Not Authorized", status_code=401)
    vid_dir = to_video_dir(title.strip())
    if not os.path.exists(vid_dir):
        return PlainTextResponse(f"error: {vid_dir} does not exist", status_code=404)

    @asyncwrap
    def delete_files_task():
        """Deletes the files."""
        max_tries = 100
        for retry in range(max_tries):
            try:
                shutil.rmtree(vid_dir)
                break
            except Exception as exc:
                log.warning(f"Error deleting {vid_dir}: {exc}")
                time.sleep(retry)
        else:
            log.error(f"Failed to delete {vid_dir} after {max_tries} tries.")

    if not Video.select().where(Video.title == title).exists():
        return PlainTextResponse(f"error: {title} does not exist", status_code=404)
    Video.delete().where(Video.title == title).execute()
    background_tasks.add_task(delete_files_task)
    return PlainTextResponse(content="Deleted ok")


if IS_TEST:

    @app.delete("/clear")
    async def clear(password: str) -> PlainTextResponse:
        """Clears the stored magnet URI."""
        if not DISABLE_AUTH and not digest_equals(password, PASSWORD):
            return PlainTextResponse("error: Not Authorized", status_code=401)
        Video.delete().execute()  # pylint: disable=no-value-for-parameter
        await asyncio.to_thread(lambda: shutil.rmtree(VIDEO_ROOT, ignore_errors=True))
        os.makedirs(VIDEO_ROOT, exist_ok=True)
        return PlainTextResponse(content="Clear ok")

    @app.get("/log")
    async def log_file():
        """Returns the log file."""
        logfile = open(  # pylint: disable=consider-using-with
            LOGFILE, encoding="utf-8", mode="r"
        )
        return StreamingResponse(logfile, media_type="text/plain")


async def _reverse_proxy(request: Request):
    url = httpx.URL(
        path=request.url.path, port=FILE_PORT, query=request.url.query.encode("utf-8")
    )
    rp_req = HTTP_SERVER.build_request(
        request.method, url, headers=request.headers.raw, content=await request.body()
    )
    rp_resp = await HTTP_SERVER.send(rp_req, stream=True)
    return StreamingResponse(
        rp_resp.aiter_raw(),
        status_code=rp_resp.status_code,
        headers=rp_resp.headers,
        background=BackgroundTask(rp_resp.aclose),
    )


# All the routes that aren't covered by app are forwareded to the
# http web server.
app.add_route("/{path:path}", _reverse_proxy, ["GET", "POST"])


def main():
    """Starts the server."""
    import webbrowser  # pylint: disable=import-outside-toplevel

    webbrowser.open(f"http://localhost:{SERVER_PORT}")
    cmd = f"http-server {DATA_ROOT}/www -p {FILE_PORT} --cors=* -c-1"
    with subprocess.Popen(cmd, shell=True):
        uvicorn.run(app, host="0.0.0.0", port=SERVER_PORT)


if __name__ == "__main__":
    main()
