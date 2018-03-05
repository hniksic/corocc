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
        return True
    except StopIteration:
        return False

_unset = object()

def _step(coro, contval):
    while True:
        if not _resume(coro, contval):
            return
        contval = _unset
        def cont(val=None):
            nonlocal contval
            if contval is not _unset:
                raise RuntimeError("coroutine already resumed")
            if in_step:
                # cont() invoked from inside suspend - just continue
                # with the current step
                contval = val
            else:
                # resume the coroutine and continue stepping
                _step(coro, val)
        in_step = True
        if not _resume(coro, cont):
            raise AssertionError("suspend didn't yield")
        if contval is _unset:
            in_step = False
            return

def launch(coro):
    _step(coro, None)
