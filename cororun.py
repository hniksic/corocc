import types
import threading

_local = threading.local()
_local.current_cont = None

@types.coroutine
def suspend(fn, *args):
    cont = _local.current_cont
    assert cont is not None
    fn(cont, *args)
    cont_retval = yield
    return cont_retval

class suspending:
    __slots__ = ('_cont',)

    async def __aenter__(self):
        cont = _local.current_cont
        assert cont is not None
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

def _step(coro, contval, fut):
    if fut is None:
        resume = _resume_simple
    else:
        resume = _resume_catching

    cont_called = False
    def cont(val=None):
        nonlocal contval, cont_called
        contval = val
        if cont_called:
            raise RuntimeError("coroutine already continued")
        cont_called = True
        if in_step:
            # cont() invoked from inside suspend - just continue
            # with the current step
            contval = val
        else:
            # let step resume the coroutine
            _step(coro, val, fut)

    prev = getattr(_local, 'current_cont', None)
    _local.current_cont = cont
    in_step = True
    try:
        while True:
            suspended = resume(coro, contval, fut)
            if not suspended:
                return
            if not cont_called:
                return
            cont_called = False
    finally:
        _local.current_cont  = prev
        in_step = False

def start(coro, future=None):
    _step(coro, None, future)
