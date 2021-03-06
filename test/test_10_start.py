import pytest

import corocc

async def null_coro(log):
    log(1)

def test_null():
    events = []
    corocc.start(null_coro(events.append))
    assert events == [1]


async def simple_coro(log):
    log(1)
    val = await corocc.suspend(lambda cont: (log(2), cont('retval')))
    log(val)

def test_simple():
    events = []
    corocc.start(simple_coro(events.append))
    assert events == [1, 2, 'retval']


async def unfinished_coro(log, save_cont):
    log(1)
    val = await corocc.suspend(lambda cont: (log(2), cont()))
    log(3)
    await corocc.suspend(lambda cont: (save_cont(cont), log(4)))
    # not logged, the coroutine is not continued
    log(5)

def test_unfinished():
    events = []
    cont_store = []
    corocc.start(unfinished_coro(events.append, cont_store.append))
    assert events == [1, 2, 3, 4]
    cont, = cont_store
    cont()
    assert events == [1, 2, 3, 4, 5]


async def inner(log):
    log('i 1')
    await corocc.suspend(lambda cont: (log('i 2'), cont()))
    log('i 3')

async def outer(log):
    log('o 1')
    await corocc.suspend(lambda cont: (log('o 2'), cont()))
    log('o 3')
    await inner(log)
    log('o 4')

def test_nested():
    events = []
    corocc.start(outer(events.append))
    assert events == ['o 1', 'o 2', 'o 3', 'i 1', 'i 2', 'i 3', 'o 4']


async def inner2(log, save_cont):
    log('i 1')
    await corocc.suspend(lambda cont: (log('i 2'), save_cont(cont)))
    log('i 3')

async def outer2(log, save_cont):
    log('o 1')
    await inner2(log, save_cont)
    log('o 2')

def test_nested_unfinished():
    events = []
    cont_store = []
    corocc.start(outer2(events.append, cont_store.append))
    assert events == ['o 1', 'i 1', 'i 2']
    cont, = cont_store
    cont()
    assert events == ['o 1', 'i 1', 'i 2', 'i 3', 'o 2']


async def cont_again_coro(log, save_cont):
    log(1)
    async with corocc.suspending() as cont:
        log(2)
        save_cont(cont)
        log(3)
    log(4)

def test_cont_again():
    events = []
    cont_store = []
    corocc.start(cont_again_coro(events.append, cont_store.append))
    assert events == [1, 2, 3]
    cont, = cont_store
    cont()
    assert events == [1, 2, 3, 4]
    with pytest.raises(RuntimeError):
        cont()
    assert events == [1, 2, 3, 4]


async def cont_again_now_coro(log):
    log(1)
    async with corocc.suspending() as cont:
        log(2)
        cont()
        log(3)
        cont()
    log(4)

def test_cont_again_now():
    events = []
    with pytest.raises(RuntimeError):
        corocc.start(cont_again_now_coro(events.append))
    assert events == [1, 2, 3]


async def different_cont_again_coro(log):
    log(1)
    async with corocc.suspending() as cont1:
        log(2)
        cont1()  # first call, ok
    async with corocc.suspending() as cont2:
        log(3)
        cont1()  # calling cont1() again, must raise
    log(4)

def test_different_cont_again():
    events = []
    with pytest.raises(RuntimeError):
        corocc.start(different_cont_again_coro(events.append))
    assert events == [1, 2, 3]


async def raise_now(log):
    log(1)
    1/0

def test_raise_now():
    events = []
    with pytest.raises(ZeroDivisionError):
        corocc.start(raise_now(events.append))
    assert events == [1]


async def raise_later(log, save_cont):
    log(1)
    async with corocc.suspending() as cont:
        save_cont(cont)
    log(2)
    1/0

def test_raise_later():
    events = []
    cont_store = []
    corocc.start(raise_later(events.append, cont_store.append))
    assert events == [1]
    cont, = cont_store
    with pytest.raises(ZeroDivisionError):
        cont()
    assert events == [1, 2]


async def send_exc_coro(log, save_cont):
    log(1)
    try:
        async with corocc.suspending() as cont:
            log(2)
            save_cont(cont)
        log(3)
    except ZeroDivisionError:
        log(4)
    except:
        log(5)
    else:
        log(6)
    log(7)
    async with corocc.suspending() as cont:
        save_cont(cont)
    log(8)


def test_send_exc():
    events = []
    cont_store = []
    corocc.start(send_exc_coro(events.append, cont_store.append))
    assert events == [1, 2]
    cont = cont_store.pop()
    cont.throw(ZeroDivisionError())
    assert events == [1, 2, 4, 7]
    cont = cont_store.pop()
    cont()
    assert events == [1, 2, 4, 7, 8]
