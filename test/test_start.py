import pytest

import cororun

async def null_coro(log):
    log(1)

def test_null():
    events = []
    cororun.start(null_coro(events.append))
    assert events == [1]


async def simple_coro(log):
    log(1)
    val = await cororun.suspend(lambda cont: (log(2), cont('retval')))
    log(val)

def test_simple():
    events = []
    cororun.start(simple_coro(events.append))
    assert events == [1, 2, 'retval']


async def unfinished_coro(log, save_cont):
    log(1)
    val = await cororun.suspend(lambda cont: (log(2), cont()))
    log(3)
    await cororun.suspend(lambda cont: (save_cont(cont), log(4)))
    # not logged, the coroutine is not continued
    log(5)

def test_unfinished():
    events = []
    cont_store = []
    cororun.start(unfinished_coro(events.append, cont_store.append))
    assert events == [1, 2, 3, 4]
    cont_store[0]()
    assert events == [1, 2, 3, 4, 5]


async def inner(log):
    log('i 1')
    await cororun.suspend(lambda cont: (log('i 2'), cont()))
    log('i 3')

async def outer(log):
    log('o 1')
    await cororun.suspend(lambda cont: (log('o 2'), cont()))
    log('o 3')
    await inner(log)
    log('o 4')

def test_nested():
    events = []
    cororun.start(outer(events.append))
    assert events == ['o 1', 'o 2', 'o 3', 'i 1', 'i 2', 'i 3', 'o 4']


async def inner2(log, save_cont):
    log('i 1')
    await cororun.suspend(lambda cont: (log('i 2'), save_cont(cont)))
    log('i 3')

async def outer2(log, save_cont):
    log('o 1')
    await inner2(log, save_cont)
    log('o 2')

def test_nested_unfinished():
    events = []
    cont_store = []
    cororun.start(outer2(events.append, cont_store.append))
    assert events == ['o 1', 'i 1', 'i 2']
    cont_store[0]()
    assert events == ['o 1', 'i 1', 'i 2', 'i 3', 'o 2']


async def cont_again_coro(log, save_cont):
    log(1)
    async with cororun.suspending() as cont:
        log(2)
        save_cont(cont)
        log(3)
    log(4)

def test_cont_again():
    events = []
    cont_store = []
    cororun.start(cont_again_coro(events.append, cont_store.append))
    assert events == [1, 2, 3]
    cont_store[0]()
    assert events == [1, 2, 3, 4]
    with pytest.raises(RuntimeError):
        cont_store[0]()
    assert events == [1, 2, 3, 4]


async def cont_again_now_coro(log):
    log(1)
    async with cororun.suspending() as cont:
        log(2)
        cont()
        log(3)
        cont()
    log(4)

def test_cont_again():
    events = []
    with pytest.raises(RuntimeError):
        cororun.start(cont_again_now_coro(events.append))
    assert events == [1, 2, 3]


async def raise_now(log):
    log(1)
    1/0

def test_raise_now():
    events = []
    with pytest.raises(ZeroDivisionError):
        cororun.start(raise_now(events.append))
    assert events == [1]


async def raise_later(log, save_cont):
    log(1)
    async with cororun.suspending() as cont:
        save_cont(cont)
    log(2)
    1/0

def test_raise_later():
    events = []
    cont_store = []
    cororun.start(raise_later(events.append, cont_store.append))
    assert events == [1]
    cont = cont_store[0]
    with pytest.raises(ZeroDivisionError):
        cont()
    assert events == [1, 2]
