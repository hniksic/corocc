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
    saved_cont = []
    cororun.start(unfinished_coro(events.append, saved_cont.append))
    assert events == [1, 2]
    cont, = saved_cont
    assert not hasattr(cont, 'result')
    cont(3)
    assert events == [1, 2, 3]
    assert cont.result == 3
