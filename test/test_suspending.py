import cororun

async def simple_coro(log):
    log(1)
    async with cororun.suspending() as cont:
        log(2)
        cont(3)
    log(cont.result)

def test_simple():
    events = []
    cororun.start(simple_coro(events.append))
    assert events == [1, 2, 3]


async def unfinished_coro(log, save_cont):
    log(1)
    async with cororun.suspending() as cont:
        log(2)
        save_cont(cont)
    log(cont.result)

def test_unfinished():
    events = []
    cont_store = []
    cororun.start(unfinished_coro(events.append, cont_store.append))
    assert events == [1, 2]
    cont, = cont_store
    assert not hasattr(cont, 'result')
    cont(3)
    assert events == [1, 2, 3]
    assert cont.result == 3


async def cont_now(log):
    log(1)
    async with cororun.suspending() as cont:
        log(2)
        cont()
        log(3)
    log(4)


def test_cont_now():
    events = []
    cororun.start(cont_now(events.append))
    assert events == [1, 2, 3, 4]
