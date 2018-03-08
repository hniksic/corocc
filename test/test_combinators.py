import threading

import cororun

async def resume_threaded():
    async with cororun.suspending() as cont:
        threading.Thread(target=cont).start()

async def simple_coro(n):
    await resume_threaded()
    return n

async def gather_coro(log, when_done):
    log(await cororun.gather(simple_coro(1), simple_coro(2), simple_coro(3)))
    when_done()

def test_gather():
    events = []
    done = threading.Event()
    cororun.start(gather_coro(events.append, done.set))
    done.wait()
    assert events == [[1, 2, 3]]
