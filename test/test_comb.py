import pytest

import time
import threading
import concurrent.futures
from concurrent.futures import Future

import corocc

async def background():
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
    await background()
    return n

def test_gather():
    future = _block(corocc.gather(simple_coro(1), simple_coro(2), simple_coro(3)))
    assert future.result() == [1, 2, 3]


async def raise_later_coro():
    await background()
    1/0

def test_gather_raise_later():
    future = _block(
        corocc.gather(simple_coro(1), simple_coro(2), raise_later_coro()))
    with pytest.raises(ZeroDivisionError):
        future.result()


def test_wait_all():
    future = _block(corocc.wait([simple_coro(1), simple_coro(2), simple_coro(3)]))
    done, pending = future.result()
    assert not pending
    assert set(f.result() for f in done) == {1, 2, 3}


async def sleep_coro(delay, n):
    await background()
    time.sleep(delay)
    return n


def test_wait_first():
    pending = {sleep_coro(.03, 3), sleep_coro(.01, 1), sleep_coro(.02, 2)}
    future = _block(corocc.wait(pending, return_when=corocc.FIRST_COMPLETED))
    done, pending = future.result()
    assert len(pending) == 2
    assert len(done) == 1
    f, = done
    assert f.result() == 1

    future = _block(corocc.wait(pending, return_when=corocc.FIRST_COMPLETED))
    done, pending = future.result()
    assert len(pending) == len(done) == 1
    f, = done
    assert f.result() == 2

    future = _block(corocc.wait(pending, return_when=corocc.FIRST_COMPLETED))
    done, pending = future.result()
    assert len(pending) == 0
    assert len(done) == 1
    f, = done
    assert f.result() == 3
