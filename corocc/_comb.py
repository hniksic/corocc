import threading

from ._base import start, suspending

__all__ = 'gather',

_Future = None
def _make_future():
    global _Future
    if _Future is None:
        import concurrent.futures
        _Future = concurrent.futures.Future
    return _Future()

async def gather(*coros):
    """A coroutine aggregating results from the given coroutines.
    Once all the coroutines have completed, this coroutine returns a list of
    their results, given in the same order as the coroutines.
    """
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
            start(coro, future=fut)
            fut._coro = coro
            fut.add_done_callback(on_done)
    return [results[coro] for coro in coros]
