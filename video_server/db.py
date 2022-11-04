"""
Database abstraction layer.
"""

# pylint: disable=too-many-arguments,too-many-return-statements,too-many-locals,logging-fstring-interpolation,disable=no-value-for-parameter
# flake8: noqa: E231
import os
from typing import List
from datetime import datetime, timedelta
from video_server.io import sanitize_path

from video_server.settings import (
    DOMAIN_NAME,
    VIDEO_ROOT,
    WWW_ROOT,
    MAX_BAD_LOGINS,
    MAX_BAD_LOGINS_RESET_TIME,
)
from video_server.models import db_proxy, BadLogin


def can_login() -> bool:
    """Returns true if the user can attempt to login."""
    # remove all bad login attempts older than MAX_BAD_LOGINS_RESET_TIME
    with db_proxy.atomic():
        oldest_allowed = datetime.now() - timedelta(seconds=MAX_BAD_LOGINS_RESET_TIME)
        oldest = BadLogin.select().where(BadLogin.created < oldest_allowed)
        for bad_login in oldest:  # pylint: disable=not-an-iterable
            bad_login.delete_instance()
        num_bad_logins = BadLogin.select().count()
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


def db_list_all_files() -> List[str]:
    """Dumps all files in the http directory."""
    files = []
    for dir_name, _, file_list in os.walk(WWW_ROOT):
        for filename in file_list:
            file = os.path.join(dir_name, filename)
            files.append(file)
    return files


def to_video_dir(title: str) -> str:
    """Returns the video directory for a title."""
    return os.path.join(VIDEO_ROOT, sanitize_path(title))
