import pytest

import threading
import concurrent.futures
from concurrent.futures import Future

import corocc

async def resume_threaded():
    async with corocc.suspending() as cont:
        threading.Thread(target=cont).start()

def _block(coro):
    # utility function shared by several tests: start the coroutine,
    # block until it's done, and return the future containing its
    # result
    future = Future()
    corocc.start(coro, future=future)
    concurrent.futures.wait([future])
    return future

async def simple_coro(n):
    await resume_threaded()
    return n

def test_gather():
    future = _block(corocc.gather(simple_coro(1), simple_coro(2), simple_coro(3)))
    assert future.result() == [1, 2, 3]


async def raise_later_coro():
    await resume_threaded()
    1/0

def test_gather_raise_later():
    future = _block(
        corocc.gather(simple_coro(1), simple_coro(2), raise_later_coro()))
    with pytest.raises(ZeroDivisionError):
        future.result()
