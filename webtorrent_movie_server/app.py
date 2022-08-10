"""
    Fastapi server
"""
import secrets
import datetime
import os
import shutil
import threading
from typing import List

from keyvalue_sqlite import KeyValueSqlite  # type: ignore

from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBasic, HTTPBasicCredentials


from webtorrent_movie_server.generate_files import (
    create_webtorrent_files,
    init_static_files,
)
from webtorrent_movie_server.settings import (
    DOMAIN_NAME,
    PROJECT_ROOT,
    STUN_SERVERS,
    TRACKER_ANNOUNCE_LIST,
    APP_DB,
    DATA_ROOT,
    LOGFILE,
    WWW_ROOT,
    VIDEO_ROOT,
)
from webtorrent_movie_server.version import VERSION

CHUNK_SIZE = 1024 * 1024

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


# @app.get('/api/access/auth', dependencies=[Depends(authorize)])
# def auth():
#    return {"Granted": True}


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

# if os.path.exists(FILES_DIR):
#    app.mount("/files", StaticFiles(directory='/var/data'), "www")


# Redirect to index.html
# @app.get("/")
# async def index(request: Request) -> RedirectResponse:
#    """Returns index.html file"""
#    params = {item[0]: item[1] for item in request.query_params.multi_items()}
#    query = ""
#    for key, value in params.items():
#        if query == "":
#            query += "?"
#        query += f"{key}={value}&"
#    return RedirectResponse(url=f"/www/index.html{query}", status_code=302)


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
    videos = sorted(query_videos())
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


def query_videos() -> List[str]:
    """Returns a list of videos in the video directory."""
    videos = [
        d for d in os.listdir(VIDEO_ROOT) if os.path.isdir(os.path.join(VIDEO_ROOT, d))
    ]
    return sorted(videos)


@app.get("/list_videos")
async def list_videos() -> JSONResponse:
    """Uploads a file to the server."""
    videos = query_videos()
    # video_paths = [os.path.join(VIDEO_ROOT, video) for video in videos]
    if "localhost" in DOMAIN_NAME:
        domain_url = f"http://{DOMAIN_NAME}"
    else:
        domain_url = f"https://{DOMAIN_NAME}"
    video_urls = [f"{domain_url}/v/{video}" for video in videos]
    return JSONResponse(content=video_urls)


@app.get("/list_all_files")
def list_all_files() -> JSONResponse:
    """List all files in a directory."""
    if "localhost" in DOMAIN_NAME:
        domain_url = f"http://{DOMAIN_NAME}"
    else:
        domain_url = f"https://{DOMAIN_NAME}"

    files = []
    for dir_name, _, file_list in os.walk(WWW_ROOT):
        for filename in file_list:
            files.append(f"{domain_url}/{dir_name}/{filename}")
    return JSONResponse(files)


def touch(fname):
    """Touches file"""
    open(  # pylint: disable=consider-using-with
        fname, encoding="utf-8", mode="a"
    ).close()
    os.utime(fname, None)


@app.post("/upload")
async def upload(  # pylint: disable=too-many-branches
    file: UploadFile = File(...),
) -> PlainTextResponse:
    """Uploads a file to the server."""
    if not file.filename.lower().endswith(".mp4"):
        return PlainTextResponse(
            status_code=415, content="Invalid file type, must be mp4"
        )
    if not os.path.exists(DATA_ROOT):
        return PlainTextResponse(
            status_code=500,
            content=f"File upload not enabled because DATA_ROOT {DATA_ROOT} does not exist",
        )
    # Use the name of the file as the folder for the new content.

    print(f"Uploading file: {file.filename}")
    out_dir = os.path.join(
        VIDEO_ROOT, os.path.splitext(os.path.basename(file.filename))[0]
    )
    os.makedirs(out_dir, exist_ok=True)
    final_path = os.path.join(out_dir, "vid.mp4")
    with open(final_path, mode="wb") as filed:
        while (chunk := await file.read(1024 * 64)) != b"":
            filed.write(chunk)
    await file.close()
    # TODO: Final check, use ffprobe to check if it is a valid mp4 file that can be  # pylint: disable=fixme
    # streamed.
    create_webtorrent_files(
        vidfile=final_path,
        domain_name=DOMAIN_NAME,
        tracker_announce_list=TRACKER_ANNOUNCE_LIST,
        stun_servers=STUN_SERVERS,
        out_dir=out_dir,
    )
    return PlainTextResponse(content=f"wrote file okay at location: {final_path}")


def video_path(video: str) -> str:
    """Returns the path to the video."""
    return os.path.join(VIDEO_ROOT, video, "vid.mp4")


@app.patch("/regenerate")
def regenerate() -> JSONResponse:
    """Regenerate the files."""
    vid_files = [video_path(v) for v in query_videos()]
    for vidf in vid_files:
        create_webtorrent_files(
            vidfile=vidf,
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
    shutil.rmtree(VIDEO_ROOT, ignore_errors=True)
    os.makedirs(VIDEO_ROOT, exist_ok=True)
    return PlainTextResponse(content="Clear ok")


print("Starting fastapi webtorrent movie server loaded.")

if __name__ == "__main__":
    import webbrowser

    import uvicorn  # type: ignore

    webbrowser.open("http://localhost:80")

    # python -m webbrowser -t "http://localhost"

    # Run the server in debug mode.
    uvicorn.run(app, host="0.0.0.0", port=80)
