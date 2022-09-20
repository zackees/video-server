"""Async related tools"""

import atexit
import asyncio
from functools import partial, wraps
from concurrent.futures import ThreadPoolExecutor

DEFAULT_EXECUTOR = ThreadPoolExecutor(max_workers=12)


def asyncwrap(func):
    """Wrap a function to run in an async loop"""

    @wraps(func)
    async def run(*args, loop=None, executor=None, **kwargs):  # pylint: disable=unused-argument
        if loop is None:
            loop = asyncio.get_event_loop()
        pfunc = partial(func, *args, **kwargs)
        executor = executor or DEFAULT_EXECUTOR
        return await loop.run_in_executor(executor, pfunc)

    return run


@atexit.register
def close_executor():
    """Waits until the executor is closed"""
    DEFAULT_EXECUTOR.shutdown(wait=False)
