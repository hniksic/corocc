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

def _resume_simple(coro, val, _):
    try:
        coro.send(val)
        return True
    except StopIteration:
        return False

def _resume_catching(coro, val, fut):
    try:
        result = coro.send(val)
    except StopIteration as e:
        fut.set_result(e.value)
        return False
    except Exception as e:
        fut.set_exception(e)
        return False
    return True

_unset = object()

def _step(coro, contval, fut):
    if fut is None:
        resume = _resume_simple
    else:
        resume = _resume_catching
    while True:
        if not resume(coro, contval, fut):
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
                # let step resume the coroutine
                _step(coro, val, fut)
        in_step = True
        if not _resume_simple(coro, cont, None):
            raise AssertionError("suspend didn't yield")
        if contval is _unset:
            in_step = False
            return

def start(coro, future=None):
    _step(coro, None, future)
