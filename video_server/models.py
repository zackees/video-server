"""
Models for the database ORM
"""

import atexit
import os
from datetime import datetime
from filelock import FileLock

from peewee import DatabaseProxy  # type: ignore
from peewee import (
    CharField,
    DateTimeField,
    IntegerField,  # type: ignore
    Model,
    PrimaryKeyField,
    FloatField,
)
from playhouse.shortcuts import model_to_dict  # type: ignore
from playhouse.sqlite_ext import SqliteExtDatabase  # type: ignore

from video_server.log import log
from video_server.settings import DATA_ROOT, STARTUP_LOCK

__all__ = ["db_proxy"]  # type: ignore

DB_PATH = os.path.join(DATA_ROOT, "vids.sqlite3")
DB_TIMEOUT = 10

db_proxy: DatabaseProxy = DatabaseProxy()

db_dir = os.path.dirname(DB_PATH)
# if dir doesn't exist
if not os.path.exists(db_dir):
    log.info("Creating db directory %s", db_dir)
    os.makedirs(db_dir, exist_ok=True)
pragmas = (
    ("cache_size", -1024 * 16),  # 16MB page-cache.
    ("journal_mode", "wal2"),
    ("foreign_keys", "on"),
    ("synchronous", 1),
)
log.info("Using database %s", DB_PATH)
sqlite_db = SqliteExtDatabase(
    str(DB_PATH),
    timeout=DB_TIMEOUT,
    pragmas=pragmas,
    check_same_thread=False,  # Allows multiple threads to access the database.
)
sqlite_db.connect()
atexit.register(sqlite_db.close)
db_proxy.initialize(sqlite_db)


class BaseModel(Model):
    """A base model that will use our Sqlite database."""

    class Meta:  # pylint: disable=too-few-public-methods
        """Meta class."""

        database = db_proxy

    def asdict(self) -> dict:
        """Serialize to dict."""
        return model_to_dict(self, recurse=False, backrefs=True, max_depth=1)

    def asjson(self):
        """Serialize to json."""
        data = self.asdict()
        for key, val in data.items():
            if isinstance(val, datetime):
                data[key] = val.isoformat()
            else:
                data[key] = str(val)
        return data


class Video(BaseModel):
    """Model used for the video"""

    id = PrimaryKeyField()
    title = CharField(null=False, unique=True, index=True)
    description = CharField(null=False, default="")
    url = CharField(null=False, unique=True, index=True)
    path = CharField(null=False, unique=True)
    published = DateTimeField(index=True, default=datetime.now)
    updated = DateTimeField(index=True, default=datetime.now)
    # status = EnumField(choices=["new", "processing", "done", "error"])
    views = IntegerField(default=0)
    iframe = CharField(null=False, default="")
    duration = FloatField(default=0)


class BadLogin(BaseModel):
    """Login model."""

    created = DateTimeField(index=True, default=datetime.now)


with FileLock(STARTUP_LOCK).acquire(timeout=10):
    db_proxy.create_tables([Video, BadLogin], safe=True)
