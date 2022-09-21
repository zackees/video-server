"""
    Fastapi server
"""

# pylint: disable=fixme,broad-except
import asyncio
import datetime
import os
import shutil
import threading
from typing import Optional
import hashlib
import traceback

from httpx import AsyncClient
import httpx
from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, RedirectResponse
from fastapi.security import HTTPBasic
from fastapi.staticfiles import StaticFiles
from keyvalue_sqlite import KeyValueSqlite  # type: ignore

# from fastapi.responses import StreamingResponse
# from starlette.requests import Request

from starlette.background import BackgroundTask

from video_server.db import (
    db_add_video,
    db_list_all_files,
    db_query_videos,
    path_to_url,
)
from video_server.generate_files import (
    init_static_files,
)
from video_server.settings import (
    APP_DB,
    DATA_ROOT,
    DOMAIN_NAME,
    LOGFILE,
    PROJECT_ROOT,
    # STUN_SERVERS,
    # TRACKER_ANNOUNCE_LIST,
    VIDEO_ROOT,
    WWW_ROOT,
)
from video_server.version import VERSION

HTTP_SERVER = AsyncClient(base_url="http://localhost:8000/")

print("Starting fastapi webtorrent movie server")
DISABLE_AUTH = os.environ.get("DISABLE_AUTH", "0") == "1"

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
    "PASSWORD",
    "68fe2a982d12423ca59b699758684def",
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


@app.post("/login", tags=["Public"])
def login(password: str) -> PlainTextResponse:
    """Use the login password to get a cookie."""
    try:
        if not digest_equals(password, PASSWORD):
            # TODO: Fail after 3 tries
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
    """Reveals the videos that are available."""
    videos = db_query_videos()
    # video_paths = [os.path.join(VIDEO_ROOT, video) for video in videos]
    if "localhost" in DOMAIN_NAME:
        domain_url = f"http://{DOMAIN_NAME}"
    else:
        domain_url = f"https://{DOMAIN_NAME}"
    vid_urls = [f"{domain_url}/v/{video}" for video in videos]
    return PlainTextResponse(content="\n".join(vid_urls))


@app.get("/list_all_files")
def list_all_files(request: Request) -> JSONResponse:
    """List all files in a directory."""
    if not is_authorized(request):
        return JSONResponse({"error": "Not Authorized"}, status_code=401)
    urls = [path_to_url(file) for file in db_list_all_files()]
    return JSONResponse(urls)


def touch(fname):
    """Touches file"""
    open(fname, encoding="utf-8", mode="a").close()  # pylint: disable=consider-using-with
    os.utime(fname, None)


@app.post("/upload")
async def upload(  # pylint: disable=too-many-branches
    request: Request,
    title: str,
    file: UploadFile = File(...),
    subtitles_zip: Optional[UploadFile] = File(None),
    do_encode: bool = False,
) -> PlainTextResponse:
    """Uploads a file to the server."""
    if not is_authorized(request):
        return PlainTextResponse("error: Not Authorized", status_code=401)
    # TODO: Use stream files, large files exhaust the ram.
    # This can be fixed by applying the following fix:
    # https://github.com/tiangolo/fastapi/issues/58
    return await db_add_video(title, file, subtitles_zip, do_encode=do_encode)


def video_path(video: str) -> str:
    """Returns the path to the video."""
    return os.path.join(VIDEO_ROOT, video, "vid.mp4")


@app.delete("/clear")
async def clear(request: Request) -> PlainTextResponse:
    """Clears the stored magnet URI."""
    if not is_authorized(request):
        return PlainTextResponse("error: Not Authorized", status_code=401)
    # app_state.clear()
    # use os.touch to trigger a restart on this server.
    # touch(os.path.join(ROOT, "restart", "restart.file"))
    await asyncio.to_thread(lambda: shutil.rmtree(VIDEO_ROOT, ignore_errors=True))
    os.makedirs(VIDEO_ROOT, exist_ok=True)
    return PlainTextResponse(content="Clear ok")


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


app.add_route("/{path:path}", _reverse_proxy, ["GET", "POST"])


print("Starting fastapi webtorrent movie server loaded.")

if __name__ == "__main__":
    import webbrowser

    import uvicorn  # type: ignore

    webbrowser.open("http://localhost:80")

    # python -m webbrowser -t "http://localhost"

    # Run the server in debug mode.
    uvicorn.run(app, host="0.0.0.0", port=80)
