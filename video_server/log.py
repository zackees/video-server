"""
Instantiates a logging object that can be used to log messages to the console and to a file.
"""

import sys
import logging
import os

from filelock import FileLock, Timeout
from video_server.settings import LOGFILE, LOGFILELOCK


LOGGING_FMT = (
    "%(levelname)s %(asctime)s %(filename)s:%(lineno)s->%(funcName)s - %(message)s"
)
LOG_FILE_MUTEX = FileLock(LOGFILELOCK)


def _log_init():
    retries = 10
    while True:
        try:
            with LOG_FILE_MUTEX.acquire(timeout=1):
                with open(LOGFILE, encoding="utf-8", mode="a") as log_file:
                    log_file.write(f"pid {os.getpid()} starting up log file\n")
            return
        except Timeout:
            retries -= 1
            if retries <= 0:
                sys.stderr.write("COULD NOT ACQUIRE LOCK ON LOG FILE!!\n")
                return


INFO = logging.INFO
DEBUG = logging.DEBUG
WARNING = logging.WARNING
ERROR = logging.ERROR
CRITICAL = logging.CRITICAL


def log_write_impl(message: str) -> None:
    """Write a log message."""
    sys.stdout.write(message)
    try:
        with LOG_FILE_MUTEX.acquire(timeout=0.1):
            with open(LOGFILE, encoding="utf-8", mode="a") as log_file:
                log_file.write(message)
    except Timeout:
        sys.stderr.write(
            "Could not acquire lock on log file for write, message:\n{message}\n"
        )
    try:
        # truncate the file if it is larger than 256k
        if os.path.getsize(LOGFILE) > 1024 * 256:
            with LOG_FILE_MUTEX.acquire(timeout=0):
                with open(LOGFILE, encoding="utf-8", mode="r") as log_file:
                    lines = log_file.readlines()
                with open(LOGFILE, encoding="utf-8", mode="w") as log_file:
                    log_file.writelines(lines[-100:])
    except Timeout:
        pass


def log_read_tail() -> str:
    """Read the last 100 lines of the log file."""
    with LOG_FILE_MUTEX.acquire(timeout=0.1):
        with open(LOGFILE, encoding="utf-8", mode="r") as log_file:
            lines = [line.strip() for line in log_file.readlines()[-1000:]]
            # reverse
            lines = lines[::-1]
            return "\n".join(lines)


class CustomStreamHandler:
    """A stream for logging."""

    def write(self, message: str) -> None:
        """Write the message to the logger."""
        log_write_impl(message)

    def flush(self) -> None:
        """Flush the stream."""


def _create_logger() -> logging.Logger:
    """Create a logger with the given name."""
    # create logger with 'spam_application'
    _log_init()
    out = logging.getLogger("system")
    out.setLevel(DEBUG)
    # create console handler with a higher log level
    strmhandler = logging.StreamHandler(CustomStreamHandler())
    strmhandler.setLevel(INFO)
    # create formatter and add it to the handlers
    formatter = logging.Formatter(LOGGING_FMT)
    strmhandler.setFormatter(formatter)
    # add the handlers to the logger
    out.addHandler(strmhandler)
    return out


log = _create_logger()


def unit_test():
    """Unit test"""
    log.setLevel(CRITICAL)
    log.warning("will this go through as a warning?")
    log.critical("will this go through as a critical?")
    log.error("will this go through as an error?")


if __name__ == "__main__":
    unit_test()
