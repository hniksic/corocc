import types

@types.coroutine
def suspend_coroutine(fn):
    cont = yield
    fn(cont)
    cont_retval = yield
    return cont_retval

def _resume(coro, val):
    try:
        coro.send(val)
        return False
    except StopIteration:
        return True

_unset = object()

def launch(coro):
    def drive_gen():
        # start executing the coroutine
        coro.send(None)
        while True:
            contval = _unset
            def cont(val=None):
                nonlocal contval
                if contval is not _unset:
                    raise RuntimeError("coroutine already resumed")
                if in_driver:
                    # cont() invoked from inside suspend_coroutine - just
                    # save the value and let drive_gen pick it up
                    contval = val
                else:
                    # resume the driver so it can resume the coroutine
                    _resume(driver, val)
            in_driver = True
            if _resume(coro, cont):
                raise AssertionError("suspend_coroutine stopped")
            if contval is _unset:
                in_driver = False
                contval = yield
            if _resume(coro, contval):
                # coroutine has completed execution
                break
    driver = drive_gen()
    _resume(driver, None)


# Usage example 1:

async def test_simple():
    print('simple 1')
    val = await suspend_coroutine(lambda cont: (print('  xxx'), cont(42)))
    print('simple 2', val)
    await suspend_coroutine(lambda cont: (print('  yyy'), cont()))
    print('simple 3')
    await suspend_coroutine(lambda cont: print('  zzz'))
    # not printed, the coroutine is not continued
    print('simple 4')

launch(test_simple())


# Usage example 2:

async def inner():
    print('  inner 1')
    await suspend_coroutine(lambda cont: (print('    zzz'), cont()))
    print('  inner 2')

async def test_nested():
    print('nested 1')
    await suspend_coroutine(lambda cont: (print('  xxx'), cont()))
    print('nested 2')
    await inner()
    print('nested 3')

launch(test_nested())


# Usage example 3:

import threading

def resume_later(cont):
    threading.Timer(1, cont).start()

async def test_threaded():
    print(1, threading.current_thread())
    await suspend_coroutine(resume_later)
    print(2, threading.current_thread())
    await suspend_coroutine(resume_later)
    print(3, threading.current_thread())

launch(test_threaded())
