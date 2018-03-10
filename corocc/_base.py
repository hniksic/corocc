import types

__all__ = 'suspend', 'suspending', 'start', 'Continuation',

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

class Continuation:
    # using __slots__ actually makes a noticable impact on performance
    __slots__ = ('_invoked', '_can_resume', '_coro', '_fut', 'start_ctx',
                 '_contval', 'result')

    def __call__(self, val=None):
        if self._invoked:
            raise RuntimeError("coroutine already resumed")
        self._invoked = True
        self._contval = val
        if self._can_resume:
            # resume the coroutine with the provided value
            _step(self._coro, val, self._fut, self.start_ctx)
        # if cont() was invoked from inside suspend, do not step,
        # just continue with the current step and resume there

def _step(coro, contval, fut, start_ctx):
    resume = _resume_simple if fut is None else _resume_catching

    while True:
        if not resume(coro, contval, fut):
            return

        cont = Continuation()
        cont._invoked = False
        cont.start_ctx = start_ctx
        cont._coro = coro
        cont._fut = fut
        cont.start_ctx = start_ctx
        # prevent Continuation from trying to resume the coroutine
        # while still running
        cont._can_resume = False
        if not _resume_simple(coro, cont, None):
            raise AssertionError("suspend didn't yield")
        if not cont._invoked:
            cont._can_resume = True
            return
        contval = cont._contval

def start(coro, *, future=None, ctx=None):
    _step(coro, None, future, ctx)
