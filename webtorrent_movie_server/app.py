"""
    Flask app for the ytclip command line tool. Serves an index.html at port 80. Clipping
    api is located at /clip
"""
import datetime
import os
import threading

from fastapi import FastAPI, UploadFile, File
from fastapi.responses import (
    PlainTextResponse,
    RedirectResponse,
)
from fastapi.staticfiles import StaticFiles

from webtorrent_movie_server.version import VERSION

HERE = os.path.dirname(__file__)
app = FastAPI()

STARTUP_DATETIME = datetime.datetime.now()

PASSWORD = os.environ.get("WEBTORRENT_MOVIE_SERVER_PASSWORD", "t6fEOV97VC1m")


def log_error(msg: str) -> None:
    """Logs an error to the print stream."""
    print(msg)


def get_current_thread_id() -> int:
    """Return the current thread id."""
    ident = threading.current_thread().ident
    if ident is None:
        return -1
    return int(ident)


# Mount all the static files.
app.mount("/www", StaticFiles(directory=os.path.join(HERE, "www")), "www")


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


@app.get("/version")
async def api_version() -> PlainTextResponse:
    """Api endpoint for getting the version."""
    return PlainTextResponse(VERSION)


@app.get("/info")
async def api_info() -> PlainTextResponse:
    """Returns the current time and the number of seconds since the server started."""
    now_time = datetime.datetime.now()
    msg = "running\n"
    msg += "Example: localhost/clip\n"
    msg += "VERSION: " + VERSION + "\n"
    msg += f"Launched at         {STARTUP_DATETIME}\n"
    msg += f"Current utc time:   {datetime.datetime.utcnow()}\n"
    msg += f"Current local time: {now_time}\n"
    msg += f"Process ID: { os.getpid()}\n"
    msg += f"Thread ID: { get_current_thread_id() }\n"
    return PlainTextResponse(content=msg)


@app.post("/upload")
async def upload(password: str, file: UploadFile = File(...)) -> PlainTextResponse:
    """Uploads a file to the server."""
    if password != PASSWORD:
        return PlainTextResponse(content="Invalid password")
    try:
        contents = await file.read()
        with open(file.filename, mode="wb") as filed:
            filed.write(contents)
    except Exception as err:  # pylint: disable=broad-except
        content = "There was an error uploading the file because: " + str(err)
        return PlainTextResponse(status_code=500, content=content)
    finally:
        await file.close()
    return PlainTextResponse(content=f"Successfuly uploaded {file.filename}")
