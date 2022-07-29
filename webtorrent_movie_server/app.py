"""
    Fastapi server
"""

import datetime
import os
import threading

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from keyvalue_sqlite import KeyValueSqlite  # type: ignore

from webtorrent_movie_server.version import VERSION

DEFAULT_TRACKER_LIST = ["wss://webtorrent-tracker.onrender.com"]

print("Starting fastapi webtorrent movie server")

FILES_DIR = os.environ.get("FILES_DIR", "/var/data")

HERE = os.path.dirname(__file__)
ROOT = os.path.dirname(HERE)
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(ROOT, "data"))
os.makedirs(DATA_DIR, exist_ok=True)
app_state = KeyValueSqlite(os.path.join(DATA_DIR, "app.sqlite"), "app")

app = FastAPI()

STARTUP_DATETIME = datetime.datetime.now()

PASSWORD = os.environ.get(
    "WEBTORRENT_MOVIE_SERVER_PASSWORD"
)  # TODO: implement this  # pylint: disable=fixme


LOGFILE = os.path.join(DATA_DIR, "log.txt")
LOG = open(LOGFILE, encoding="utf-8", mode="a")  # pylint: disable=consider-using-with


def log_error(msg: str) -> None:
    """Logs an error to the print stream."""
    print(msg)


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


@app.on_event("shutdown")
def shutdown_event():
    """Event handler for when the app shuts down."""
    print("Application shutdown")
    LOG.write("Application shutdown\n")
    LOG.close()


# Mount all the static files.
app.mount("/www",StaticFiles(directory=os.path.join(HERE, "www")), "www")
app.mount("/files",StaticFiles(directory=FILES_DIR), "files")


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


@app.post("/upload")
async def upload(  # pylint: disable=too-many-branches
    file: UploadFile = File(...),
) -> PlainTextResponse:
    """Uploads a file to the server."""
    if not file.filename.lower().endswith(".mp4"):
        return PlainTextResponse(status_code=415, content="Invalid file type, must be mp4")
    print(f"Uploading file: {file.filename}")
    final_path = os.path.join(DATA_DIR, file.filename)
    with open(final_path, mode="wb") as filed:
        while (chunk := await file.read(1024 * 64)) != b"":
            filed.write(chunk)
    file.close()
    return PlainTextResponse(content=f"wrote file okay at location: {final_path}")


@app.get("/accessMagnetURI")
async def api_add_view(add_view: bool = True) -> JSONResponse:
    """Get the stored magnet URI and optionally increment the number of views."""
    magnet_uri = app_state.get("magnetURI")
    if magnet_uri is not None and add_view:
        app_state.atomic_add("views", 1)
    out = {
        "views": app_state.get("views", 0),
        "magnetURI": magnet_uri or "None",
        "add_view": add_view,
    }
    return JSONResponse(content=out)


@app.get("/info")
async def api_info() -> JSONResponse:
    """Returns the current time and the number of seconds since the server started."""
    app_data = app_state.to_dict()
    out = {
        "version": VERSION,
        "Launched at": str(STARTUP_DATETIME),
        "Current utc time": str(datetime.datetime.utcnow()),
        "Process ID": os.getpid(),
        "Thread ID": get_current_thread_id(),
        "Number of Views": app_data.get("views", 0),
        "App state": app_data,
    }
    return JSONResponse(out)


@app.get("/stats")
async def api_views() -> JSONResponse:
    """Returns the current number of views."""
    app_data = app_state.to_dict()
    views = str(app_data.get("views", 0))
    return JSONResponse({"views": views})


def touch(fname):
    """Touches file"""
    open(fname, encoding="utf-8", mode="a").close()  # pylint: disable=consider-using-with
    os.utime(fname, None)


@app.get("/clear")
async def clear() -> PlainTextResponse:
    """Clears the stored magnet URI."""
    app_state.clear()
    # use os.touch to trigger a restart on this server.
    touch(os.path.join(ROOT, "restart", "restart.file"))
    return PlainTextResponse(content="Server queued for restart.")


print("Starting fastapi webtorrent movie server loaded.")

if __name__ == "__main__":
    import webbrowser

    import uvicorn  # type: ignore

    webbrowser.open("http://localhost:80")

    # python -m webbrowser -t "http://localhost"

    # Run the server in debug mode.
    uvicorn.run(app, host="0.0.0.0", port=80)
