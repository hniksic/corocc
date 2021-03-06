import pytest

import corocc

async def simple_coro(log):
    log(1)
    async with corocc.suspending() as cont:
        log(2)
        cont(3)
    log(cont.result)

def test_simple():
    events = []
    corocc.start(simple_coro(events.append))
    assert events == [1, 2, 3]


async def unfinished_coro(log, save_cont):
    log(1)
    async with corocc.suspending() as cont:
        log(2)
        save_cont(cont)
    log(cont.result)

def test_unfinished():
    events = []
    cont_store = []
    corocc.start(unfinished_coro(events.append, cont_store.append))
    assert events == [1, 2]
    cont, = cont_store
    assert not hasattr(cont, 'result')
    cont(3)
    assert events == [1, 2, 3]
    assert cont.result == 3


async def cont_now(log):
    log(1)
    async with corocc.suspending() as cont:
        log(2)
        cont()
        log(3)
    log(4)


def test_cont_now():
    events = []
    corocc.start(cont_now(events.append))
    assert events == [1, 2, 3, 4]


async def nested_suspending(log):
    log(1)
    async with corocc.suspending():
        log(2)
        async with corocc.suspending():
            log(3)
        log(4)
    log(5)


def test_nested_suspending():
    events = []
    with pytest.raises(RuntimeError):
        corocc.start(nested_suspending(events.append))
    assert events == [1, 2]
