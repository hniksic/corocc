import types

__all__ = 'suspend', 'suspending', 'start', 'Continuation',

_CONT_REQUEST = object()

@types.coroutine
def suspend(fn, *args):
    """Suspend the currently running coroutine and invoke FN with the continuation."""
    cont = yield _CONT_REQUEST
    fn(cont, *args)
    cont_retval = yield
    return cont_retval

class suspending:
    """Provide the continuation to the code entering the context manager:

    async with corocc.suspending() as cont:
        ... # store cont somewhere, or call it
        # suspension happens at this point
    """

    __slots__ = ('_cont',)

    @types.coroutine
    def __aenter__(self):
        cont = yield _CONT_REQUEST
        self._cont = cont
        return cont

    @types.coroutine
    def __aexit__(self, _t, v, _tb):
        # if there is an exception, raise it immediately, don't wait
        # until resumption
        if v is not None:
            raise v
        self._cont.result = yield

def _resume_simple(coro_deliver, val, _):
    try:
        coro_deliver(val)
        return True
    except StopIteration:
        return False

def _resume_catching(coro_deliver, val, fut):
    try:
        coro_deliver(val)
    except StopIteration as e:
        fut.set_result(e.value)
        return False
    except Exception as e:
        fut.set_exception(e)
        return False
    return True


def _resume_with_cont(coro, cont):
    try:
        ret = coro.send(cont)
    except StopIteration:
        raise AssertionError("suspend didn't yield")
    if ret is _CONT_REQUEST:
        raise RuntimeError("nested suspending() inside in the same coroutine "
                           "is not allowed")


class Continuation:
    # using __slots__ actually makes a noticable impact on performance
    __slots__ = ('_invoked', '_can_resume', '_coro', '_fut', 'start_data',
                 '_contval', '_coro_deliver', 'result')

    def __call__(self, val=None):
        if self._invoked:
            raise RuntimeError("coroutine already resumed")
        self._invoked = True
        coro = self._coro
        if self._can_resume:
            # resume the coroutine with the provided value
            _step(coro, coro.send, val, self._fut, self.start_data)
        else:
            # if cont() was invoked from inside suspend, do not step,
            # just continue with the current step and resume there
            self._contval = val
            self._coro_deliver = coro.send

    def throw(self, e):
        # Almost-pasted implementation of __call__ for efficiency of
        # __call__ invocation.
        if self._invoked:
            raise RuntimeError("coroutine already resumed")
        self._invoked = True
        coro = self._coro
        if self._can_resume:
            _step(coro, coro.throw, e, self._fut, self.start_data)
        else:
            self._contval = e
            self._coro_deliver = coro.throw


def _step(coro, coro_deliver, contval, fut, start_data):
    resume = _resume_simple if fut is None else _resume_catching

    while True:
        if not resume(coro_deliver, contval, fut):
            return

        cont = Continuation()
        cont._invoked = False
        cont.start_data = start_data
        cont._coro = coro
        cont._fut = fut
        cont.start_data = start_data
        # prevent Continuation from trying to resume the coroutine
        # while still running
        cont._can_resume = False
        _resume_with_cont(coro, cont)
        if not cont._invoked:
            cont._can_resume = True
            return
        contval = cont._contval
        coro_deliver = cont._coro_deliver

def start(coro, *, future=None, data=None):
    """
    Start executing CORO, allowing it to suspend itself and continue
    execution.
    """
    _step(coro, coro.send, None, future, data)
