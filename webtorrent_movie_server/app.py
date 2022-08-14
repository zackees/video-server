"""
    Fastapi server
"""

# pylint: disable=fixme

import datetime
import os
from httpx import AsyncClient
import secrets
import shutil
import threading
# from fastapi.responses import StreamingResponse
from typing import Optional

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from keyvalue_sqlite import KeyValueSqlite  # type: ignore
import asyncio

from webtorrent_movie_server.db import (
    db_add_video,
    db_list_all_files,
    db_query_videos,
    path_to_url,
)
from webtorrent_movie_server.generate_files import (
    create_webtorrent_files,
    init_static_files,
)
from webtorrent_movie_server.settings import (
    APP_DB,
    DATA_ROOT,
    DOMAIN_NAME,
    LOGFILE,
    PROJECT_ROOT,
    STUN_SERVERS,
    TRACKER_ANNOUNCE_LIST,
    VIDEO_ROOT,
    WWW_ROOT,
)
from webtorrent_movie_server.version import VERSION

HTTP_SERVER = AsyncClient(base_url='http://localhost:8000/')

print("Starting fastapi webtorrent movie server")

app_state = KeyValueSqlite(APP_DB, "app")
# VIDEO_ROOT = os.path.join(DATA_ROOT, "v")

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

PASSWORD = os.environ.get(
    "WEBTORRENT_MOVIE_SERVER_PASSWORD"
)  # TODO: implement this  # pylint: disable=fixme


LOG = open(LOGFILE, encoding="utf-8", mode="a")  # pylint: disable=consider-using-with


def log_error(msg: str) -> None:
    """Logs an error to the print stream."""
    # print(msg)
    print(msg)
    LOG.write(msg + "\n")


def get_current_thread_id() -> int:
    """Return the current thread id."""
    ident = threading.current_thread().ident
    if ident is None:
        return -1
    return int(ident)


def authorize(credentials: HTTPBasicCredentials = Depends(security)):
    """Authorize the user."""
    is_user_ok = secrets.compare_digest(
        credentials.username, os.getenv("LOGIN", "LOGIN")
    )
    is_pass_ok = secrets.compare_digest(
        credentials.password, os.getenv("PASSWORD", "PASSWORD")
    )

    if not (is_user_ok and is_pass_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Basic"},
        )


@app.on_event("startup")
async def startup_event():
    """Event handler for when the app starts up."""
    print("Startup event")
    LOG.write("Startup event\n")
    init_static_files(WWW_ROOT)


@app.on_event("shutdown")
def shutdown_event():
    """Event handler for when the app shuts down."""
    print("Application shutdown")
    LOG.write("Application shutdown\n")
    LOG.close()


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


@app.get("/info")
async def api_info() -> JSONResponse:
    """Returns the current time and the number of seconds since the server started."""
    app_data = app_state.to_dict()
    if "localhost" in DOMAIN_NAME:
        domain_url = f"http://{DOMAIN_NAME}"
    else:
        domain_url = f"https://{DOMAIN_NAME}"
    videos = sorted(db_query_videos())
    links = [f"{domain_url}/v/{video}" for video in videos]
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
        "Videos": videos,
    }
    return JSONResponse(out)


@app.get("/videos")
async def list_videos() -> PlainTextResponse:
    """Uploads a file to the server."""
    videos = db_query_videos()
    # video_paths = [os.path.join(VIDEO_ROOT, video) for video in videos]
    if "localhost" in DOMAIN_NAME:
        domain_url = f"http://{DOMAIN_NAME}"
    else:
        domain_url = f"https://{DOMAIN_NAME}"
    vid_urls = [f"{domain_url}/v/{video}" for video in videos]
    return PlainTextResponse(content="\n".join(vid_urls))


@app.get("/list_all_files")
def list_all_files() -> JSONResponse:
    """List all files in a directory."""
    urls = [path_to_url(file) for file in db_list_all_files()]
    return JSONResponse(urls)


def touch(fname):
    """Touches file"""
    open(  # pylint: disable=consider-using-with
        fname, encoding="utf-8", mode="a"
    ).close()
    os.utime(fname, None)


@app.post("/upload")
async def upload(  # pylint: disable=too-many-branches
    title: str,
    file: UploadFile = File(...),
    subtitles_zip: Optional[UploadFile] = File(None),
) -> PlainTextResponse:
    """Uploads a file to the server."""
    # TODO: Use stream files, large files exhaust the ram.
    # This can be fixed by applying the following fix:
    # https://github.com/tiangolo/fastapi/issues/58
    return await db_add_video(title, file, subtitles_zip)


def video_path(video: str) -> str:
    """Returns the path to the video."""
    return os.path.join(VIDEO_ROOT, video, "vid.mp4")


@app.patch("/regenerate")
def regenerate() -> JSONResponse:
    """Regenerate the files."""
    vid_files = [video_path(v) for v in db_query_videos()]
    for vidf in vid_files:
        # get name and split extension
        name = os.path.splitext(os.path.basename(vidf))[0]
        create_webtorrent_files(
            vidfile=vidf,
            vid_name=name,
            domain_name=DOMAIN_NAME,
            tracker_announce_list=TRACKER_ANNOUNCE_LIST,
            stun_servers=STUN_SERVERS,
            out_dir=os.path.dirname(vidf),
        )
    return JSONResponse(content=vid_files)


@app.delete("/clear")
async def clear() -> PlainTextResponse:
    """Clears the stored magnet URI."""
    # app_state.clear()
    # use os.touch to trigger a restart on this server.
    # touch(os.path.join(ROOT, "restart", "restart.file"))
    await asyncio.to_thread(lambda: shutil.rmtree(VIDEO_ROOT, ignore_errors=True))
    os.makedirs(VIDEO_ROOT, exist_ok=True)
    return PlainTextResponse(content="Clear ok")


@app.api_route("/{path:path}", methods=["GET"])
async def proxy_request(path: str, response: Response):
    req = HTTP_SERVER.build_request("GET", path)
    r = await HTTP_SERVER.send(req)
    return Response(content=r.content, headers=r.headers, status_code=r.status_code)


print("Starting fastapi webtorrent movie server loaded.")

if __name__ == "__main__":
    import webbrowser

    import uvicorn  # type: ignore

    webbrowser.open("http://localhost:80")

    # python -m webbrowser -t "http://localhost"

    # Run the server in debug mode.
    uvicorn.run(app, host="0.0.0.0", port=80)
