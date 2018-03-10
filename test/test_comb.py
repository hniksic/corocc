import pytest

import threading
import concurrent.futures
from concurrent.futures import Future

import corocc

async def resume_threaded():
    async with corocc.suspending() as cont:
        threading.Thread(target=cont).start()

async def simple_coro(n):
    await resume_threaded()
    return n

async def gather_coro(log, when_done):
    log(await corocc.gather(simple_coro(1), simple_coro(2), simple_coro(3)))
    when_done()

def test_gather():
    events = []
    done = threading.Event()
    corocc.start(gather_coro(events.append, done.set))
    done.wait()
    assert events == [[1, 2, 3]]


async def raise_coro():
    await resume_threaded()
    1/0


async def gather_raise_coro():
    return await corocc.gather(simple_coro(1), simple_coro(2), raise_coro())

def test_gather_raise():
    future = Future()
    corocc.start(gather_raise_coro(), future=future)
    concurrent.futures.wait([future])
    with pytest.raises(ZeroDivisionError):
        future.result()
