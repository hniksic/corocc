import types

@types.coroutine
def suspend(fn, *args):
    cont = yield
    fn(cont, *args)
    cont_retval = yield
    return cont_retval

class suspending:
    __slots__ = ('_cont',)

    @types.coroutine
    def __aenter__(self):
        cont = yield
        self._cont = cont
        return cont

    @types.coroutine
    def __aexit__(self, *_):
        self._cont.result = yield

def _resume(coro, val):
    try:
        coro.send(val)
        return False
    except StopIteration:
        return True

_unset = object()

def launch(coro):
    def step(contval):
        while True:
            if _resume(coro, contval):
                break
            contval = _unset
            def cont(val=None):
                nonlocal contval
                if contval is not _unset:
                    raise RuntimeError("coroutine already resumed")
                if in_step:
                    # cont() invoked from inside suspend_coroutine - just
                    # save the value and let drive_gen pick it up
                    contval = val
                else:
                    # resume the driver so it can resume the coroutine
                    step(val)
            in_step = True
            if _resume(coro, cont):
                raise AssertionError("suspend_coroutine stopped")
            if contval is _unset:
                in_step = False
                break
    # start executing the coroutine
    step(None)
