import pytest

import threading
import concurrent.futures
from concurrent.futures import Future

import corocc

async def result_now():
    return 42

def test_future_result_now():
    fut = Future()
    assert not fut.done()
    corocc.start(result_now(), fut)
    assert fut.done()
    assert fut.result() == 42

async def result_later(save_cont):
    async with corocc.suspending() as cont:
        save_cont(cont)
    return 42

def test_future_result_later():
    fut = Future()
    cont_store = []
    corocc.start(result_later(cont_store.append), fut)
    assert not fut.done()
    cont_store[0]()
    assert fut.done()
    assert fut.result() == 42

async def raise_now(log):
    log(1)
    1/0

def test_future_raise_now():
    fut = Future()
    events = []
    corocc.start(raise_now(events.append), fut)
    assert events == [1]
    assert fut.done()
    with pytest.raises(ZeroDivisionError):
        fut.result()

async def raise_later(log, save_cont):
    log(1)
    async with corocc.suspending() as cont:
        save_cont(cont)
    log(2)
    1/0

def test_future_raise_later():
    fut = Future()
    events = []
    cont_store = []
    corocc.start(raise_later(events.append, cont_store.append), fut)
    assert not fut.done()
    assert events == [1]
    cont_store[0]()
    assert events == [1, 2]
    assert fut.done()
    with pytest.raises(ZeroDivisionError):
        fut.result()


async def future_finish_later(log):
    log(1)
    async with corocc.suspending() as cont:
        # continue execution in a different thread
        threading.Timer(0.01, cont).start()
    log(2)
    return 42

def test_future_wait():
    fut = Future()
    events = []
    corocc.start(future_finish_later(events.append), fut)
    assert not fut.done()
    assert events == [1]
    concurrent.futures.wait([fut])
    assert events == [1, 2]
    assert fut.result() == 42
