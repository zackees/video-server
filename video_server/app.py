"""
    Fastapi server
"""

# pylint: disable=fixme,broad-except,logging-fstring-interpolation
import asyncio
import datetime
import hashlib
import os
import shutil
import threading
import time
import traceback
from typing import Optional

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
from httpx import AsyncClient
from keyvalue_sqlite import KeyValueSqlite  # type: ignore
from starlette.background import BackgroundTask

from video_server.asyncwrap import asyncwrap
from video_server.db import (
    db_add_video,
    db_list_all_files,
    path_to_url,
    to_video_dir,
    can_login,
    add_bad_login,
)
from video_server.generate_files import init_static_files
from video_server.log import log
from video_server.models import Video
from video_server.rss import rss
from video_server.settings import (  # STUN_SERVERS,; TRACKER_ANNOUNCE_LIST,
    APP_DB,
    IS_TEST,
    LOGFILE,
    PROJECT_ROOT,
    STARTUP_LOCK,
    VIDEO_ROOT,
    WWW_ROOT,
    DISABLE_AUTH,
    PASSWORD,
    DATA_ROOT,
)
from video_server.version import VERSION

# from fastapi.responses import StreamingResponse
# from starlette.requests import Request


class RssResponse(Response):  # pylint: disable=too-few-public-methods
    """Returns an RSS response from a query."""

    media_type = "application/xml"
    charset = "utf-8"


HTTP_SERVER = AsyncClient(base_url="http://localhost:8000/")

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
    links = [video.url for video in Video.select()]
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
    }
    return JSONResponse(out)


@app.get("/videos")
async def list_videos() -> PlainTextResponse:
    """Reveals the videos that are available."""
    links = [video.url for video in Video.select()]
    return PlainTextResponse(content="\n".join(links))


@app.put("/add_view/{id}")
async def add_view(id: int) -> PlainTextResponse:  # pylint: disable=redefined-builtin,invalid-name
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
async def upload(  # pylint: disable=too-many-branches,too-many-arguments
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
    return await db_add_video(
        title=title,
        description=description,
        file=file,
        thumbnail=thumbnail,
        subtitles_zip=subtitles_zip,
        do_encode=do_encode,
    )


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

    background_tasks.add_task(delete_files_task)
    return PlainTextResponse(content="Deleted ok")


if IS_TEST:

    @app.delete("/clear")
    async def clear(password: str) -> PlainTextResponse:
        """Clears the stored magnet URI."""
        if not DISABLE_AUTH and not digest_equals(password, PASSWORD):
            return PlainTextResponse("error: Not Authorized", status_code=401)
        await asyncio.to_thread(lambda: shutil.rmtree(VIDEO_ROOT, ignore_errors=True))
        os.makedirs(VIDEO_ROOT, exist_ok=True)
        return PlainTextResponse(content="Clear ok")

    @app.get('/log')
    async def log_file():
        """Returns the log file."""
        logfile = open(LOGFILE, encoding='utf-8', mode='r')
        return StreamingResponse(logfile, media_type='text/plain')


async def _reverse_proxy(request: Request):
    url = httpx.URL(path=request.url.path, query=request.url.query.encode("utf-8"))
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


if __name__ == "__main__":
    import webbrowser
    import subprocess

    import uvicorn  # type: ignore

    webbrowser.open("http://localhost:80")

    # python -m webbrowser -t "http://localhost"

    cmd = f"http-server {DATA_ROOT}/www -p 8000 --cors=* -c-1"
    print(f"Starting http-server: {cmd}")
    with subprocess.Popen(cmd, shell=True):
        # Run the server in debug mode.
        uvicorn.run(app, host="0.0.0.0", port=80)
