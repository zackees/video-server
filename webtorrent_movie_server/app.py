"""
    Fastapi server
"""

import datetime
import os
import shutil
import threading
from pathlib import Path

from keyvalue_sqlite import KeyValueSqlite  # type: ignore

from fastapi import FastAPI, File, UploadFile, Header, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles


from webtorrent_movie_server.generate_files import (
    create_webtorrent_files,
    init_static_files,
)
from webtorrent_movie_server.settings import (
    DOMAIN_NAME,
    STUN_SERVERS,
    TRACKER_ANNOUNCE_LIST,
    APP_DB,
    DATA_ROOT,
    LOGFILE,
    WWW_ROOT,
    VIDEO_ROOT,
    DOMAIN_URL,
)
from webtorrent_movie_server.version import VERSION

CHUNK_SIZE = 1024 * 1024

print("Starting fastapi webtorrent movie server")

app_state = KeyValueSqlite(APP_DB, "app")
# VIDEO_ROOT = os.path.join(DATA_ROOT, "v")

app = FastAPI()

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
    all_files = list_all_files(DATA_ROOT)
    mp4_files = [f for f in all_files if f.lower().endswith(".mp4")]
    app_data = app_state.to_dict()
    links = [f.replace(WWW_ROOT, DOMAIN_URL) for f in list_all_files(WWW_ROOT)]
    vid_names = [os.path.basename(os.path.dirname(mp4)) for mp4 in mp4_files]
    vid_links = [f"{DOMAIN_URL}/video?name={name}" for name in vid_names]
    out = {
        "version": VERSION,
        "Launched at": str(STARTUP_DATETIME),
        "Current utc time": str(datetime.datetime.utcnow()),
        "Process ID": os.getpid(),
        "Thread ID": get_current_thread_id(),
        "Number of Views": app_data.get("views", 0),
        "App state": app_data,
        "DATA_ROOT": DATA_ROOT,
        "Number of MP4 files": len(mp4_files),
        "MP4 files": mp4_files,
        "All files": list_all_files(DATA_ROOT),
        "Links": links,
        "Vid Links": vid_links,
    }
    return JSONResponse(out)


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
        file=final_path,
        domain_name=DOMAIN_NAME,
        tracker_announce_list=TRACKER_ANNOUNCE_LIST,
        stun_servers=STUN_SERVERS,
        out_dir=out_dir,
    )
    return PlainTextResponse(content=f"wrote file okay at location: {final_path}")


def list_all_files(start_dir: str) -> list[str]:
    """List all files in a directory."""
    files = []
    for dir_name, _, file_list in os.walk(start_dir):
        for filename in file_list:
            files.append(os.path.join(dir_name, filename))
    return files


def touch(fname):
    """Touches file"""
    open(  # pylint: disable=consider-using-with
        fname, encoding="utf-8", mode="a"
    ).close()
    os.utime(fname, None)


@app.get("/video")
async def video_endpoint(name: str, byte_range: str = Header(None)):
    """Video input for streaming file chunks."""
    video_path = Path(os.path.join(VIDEO_ROOT, name, "vid.mp4"))
    if byte_range is not None:
        _start, _end = byte_range.replace("bytes=", "").split("-")
        start: int = int(_start)
        end: int = int(_end) if _end else start + CHUNK_SIZE
        with open(video_path, "rb") as video:
            video.seek(start)
            data = video.read(end - start)
            filesize = str(video_path.stat().st_size)
            headers = {
                "Content-Range": f"bytes {str(start)}-{str(end)}/{filesize}",
                "Accept-Ranges": "bytes",
            }
            return Response(data, status_code=206, headers=headers, media_type="video/mp4")
    else:
        return FileResponse(video_path, media_type="video/mp4")


@app.delete("/clear")
async def clear() -> PlainTextResponse:
    """Clears the stored magnet URI."""
    # app_state.clear()
    # use os.touch to trigger a restart on this server.
    # touch(os.path.join(ROOT, "restart", "restart.file"))
    shutil.rmtree(VIDEO_ROOT, ignore_errors=True)
    os.makedirs(VIDEO_ROOT, exist_ok=True)
    return PlainTextResponse(content="Server queued for restart.")


print("Starting fastapi webtorrent movie server loaded.")

if __name__ == "__main__":
    import webbrowser

    import uvicorn  # type: ignore

    webbrowser.open("http://localhost:80")

    # python -m webbrowser -t "http://localhost"

    # Run the server in debug mode.
    uvicorn.run(app, host="0.0.0.0", port=80)
