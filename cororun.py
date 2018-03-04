import types

@types.coroutine
def suspend(fn, *args):
    cont = yield
    fn(cont, *args)
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
    def driver_gen():
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
    driver = driver_gen()
    _resume(driver, None)
