import cororun

async def simple_coro(log):
    log(1)
    val = await cororun.suspend(lambda cont: (log(2), cont('retval')))
    log(val)

def test_simple():
    events = []
    cororun.launch(simple_coro(events.append))
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
    last_cont = []
    cororun.launch(unfinished_coro(events.append, last_cont.append))
    assert events == [1, 2, 3, 4]
    last_cont[0]()
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
    cororun.launch(outer(events.append))
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
    last_cont = []
    cororun.launch(outer2(events.append, last_cont.append))
    assert events == ['o 1', 'i 1', 'i 2']
    last_cont[0]()
    assert events == ['o 1', 'i 1', 'i 2', 'i 3', 'o 2']
