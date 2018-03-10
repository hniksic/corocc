import types

__all__ = 'suspend', 'suspending', 'start',

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
    def __aexit__(self, _t, v, _tb):
        # if there is an exception, raise it immediately, don't wait
        # until resumption
        if v is not None:
            raise v
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

def _step(coro, contval, fut, start_ctx):
    resume = _resume_simple if fut is None else _resume_catching

    while True:
        if not resume(coro, contval, fut):
            return

        cont_invoked = [False]
        def cont(val=None, __invoked=cont_invoked):
            nonlocal contval
            if __invoked[0]:
                raise RuntimeError("coroutine already resumed")
            __invoked[0] = True
            contval = val
            if not in_step:
                # resume the coroutine with the provided value
                _step(coro, val, fut, start_ctx)
            # if cont() was invoked from inside suspend, do not step,
            # just continue with the current step and resume there
        cont.start_ctx = start_ctx

        in_step = True
        if not _resume_simple(coro, cont, None):
            raise AssertionError("suspend didn't yield")
        if not cont_invoked[0]:
            in_step = False
            return

def start(coro, *, future=None, ctx=None):
    _step(coro, None, future, ctx)
