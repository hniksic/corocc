import time, threading

import cororun

def resume_later(cont):
    threading.Timer(.05, cont).start()

async def thread_coro(log):
    log(('a', threading.current_thread()))
    await cororun.suspend(resume_later)
    log(('b', threading.current_thread()))
    await cororun.suspend(resume_later)
    log(('c', threading.current_thread()))

def test_thread():
    events = []
    cororun.start(thread_coro(events.append))
    assert len(events) == 1
    assert events[0][0] == 'a'
    time.sleep(.2)
    assert [x for (x, _y) in events] == ['a', 'b', 'c']
    assert len(set(y for (_x, y) in events)) == 3
