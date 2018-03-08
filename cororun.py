import types
import threading

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

def _step(coro, contval, fut):
    resume = _resume_simple if fut is None else _resume_catching

    while True:
        if not resume(coro, contval, fut):
            return

        cont_invoked = [False]
        def cont(val=None, _invoked=cont_invoked):
            nonlocal contval
            if cont_invoked[0]:
                raise RuntimeError("coroutine already resumed")
            cont_invoked[0] = True
            contval = val
            if not in_step:
                # resume the coroutine with the provided value
                _step(coro, val, fut)
            # if cont() was invoked from inside suspend, do not step,
            # just continue with the current step and resume there

        in_step = True
        if not _resume_simple(coro, cont, None):
            raise AssertionError("suspend didn't yield")
        if not cont_invoked[0]:
            in_step = False
            return

def start(coro, future=None):
    _step(coro, None, future)


_Future = None
def _make_future():
    global _Future
    if _Future is None:
        import concurrent.futures
        _Future = concurrent.futures.Future
    return _Future()

async def gather(*coros):
    if not coros:
        return []
    results = {}
    mutex = threading.Lock()
    async with suspending() as cont:
        def on_done(fut):
            with mutex:
                results[fut._coro] = fut.result()
                finished = len(results) == len(coros)
            if finished:
                cont()
        for coro in coros:
            fut = _make_future()
            start(coro, fut)
            fut._coro = coro
            fut.add_done_callback(on_done)
    return [results[coro] for coro in coros]
