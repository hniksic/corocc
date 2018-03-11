import types
import threading
import time

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


class Continuation:
    """
    Object that can be invoked to continue a suspended coroutine.
    Continuations are one-shot, invoking a continuation more than once
    results in a RuntimeError.
    """
    # using __slots__ actually makes a noticable impact on performance
    __slots__ = ('_driver', '_invoked_in', '_contval', '_coro_deliver',
                 'result')

    def __call__(self, value=None):
        """Continue the coroutine with the provided value, or None."""
        if self._invoked_in is not None:
            raise RuntimeError("coroutine already resumed")
        here = threading.current_thread()
        self._invoked_in = here
        driver = self._driver
        if driver._step_thread is not here:
            # resume the coroutine with the provided value
            while driver.coro_running:
                time.sleep(.0001)
            driver.step(driver.coro.send, value)
        else:
            # if cont() was invoked from inside suspend, do not step,
            # just continue with the current step and resume there
            self._contval = value
            self._coro_deliver = driver.coro.send

    def throw(self, e):
        """Continue the coroutine with the provided exception."""
        # Almost-pasted implementation of __call__ for efficiency of
        # __call__ invocation.
        if self._invoked_in is not None:
            raise RuntimeError("coroutine already resumed")
        here = threading.current_thread()
        self._invoked_in = here
        driver = self._driver
        if driver._step_thread is not here:
            while driver.coro_running:
                time.sleep(.0001)
            driver.step(driver.coro.throw, e)
        else:
            self._contval = e
            self._coro_deliver = driver.coro.throw


class _Driver:
    __slots__ = ('coro', 'future', 'start_data', 'resumefn', 'coro_running',
                 '_step_thread')

    def step(self, coro_deliver, contval):
        here = self._step_thread = threading.current_thread()
        future = self.future
        coro = self.coro

        while True:
            if not self.resumefn(coro_deliver, contval, future):
                return

            cont = Continuation()
            cont._driver = self
            cont._invoked_in = None
            self._resume_with_cont(coro, cont)
            if cont._invoked_in is not here:
                # The continuation was not invoked, or was invoked in a
                # different thread.  Our job is done for this iteration, the
                # continuation will call us again.  Set _step_thread to
                # something that is not a thread, so that the continuation
                # always calls step().
                self._step_thread = None
                return
            # The continuation was invoked immediately, so the suspension
            # didn't really happen.  Continue.
            contval = cont._contval
            coro_deliver = cont._coro_deliver

    def _resume_with_cont(self, coro, cont):
        self.coro_running = True
        try:
            ret = coro.send(cont)
        except StopIteration:
            raise AssertionError("suspend didn't yield")
        finally:
            self.coro_running = False
        if ret is _CONT_REQUEST:
            raise RuntimeError("nested suspending() inside in the same coroutine "
                               "is not allowed")


def start(coro, *, future=None, data=None):
    """
    Start executing CORO, allowing it to suspend itself and continue
    execution.
    """
    d = _Driver()
    d.coro = coro
    d.future = future
    d.start_data = data
    if future is None:
        d.resumefn = _resume_simple
    else:
        d.resumefn = _resume_catching
    d.coro_running = False
    d.step(coro.send, None)
