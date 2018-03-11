import threading

from ._base import start, suspending

__all__ = 'gather', \
          'wait', 'FIRST_COMPLETED', 'FIRST_EXCEPTION', 'ALL_COMPLETED',

_Future = None
def _get_future_impl():
    global _Future
    if _Future is None:
        import concurrent.futures
        _Future = concurrent.futures.Future
    return _Future

async def gather(*coros):
    """
    Wait for coroutines to complete and return a list of their results.
    Results are in a list, in the same order as the coroutines.
    """
    if not coros:
        return []
    results = {}
    finished = False
    on_done_mutex = threading.Lock()
    future_impl = _get_future_impl()

    async with suspending() as cont:
        def on_done(fut):
            nonlocal finished
            if finished:
                return
            try:
                fut_result = fut.result()
            except Exception as e:
                with on_done_mutex:
                    if finished:
                        return
                    finished = True
                cont.throw(e)
                return
            with on_done_mutex:
                if finished:
                    return
                results[fut._coro] = fut_result
                all_complete = len(results) == len(coros)
                if all_complete:
                    finished = True
            if all_complete:
                cont()
        for coro in coros:
            fut = future_impl()
            start(coro, future=fut)
            fut._coro = coro
            fut.add_done_callback(on_done)

    return [results[coro] for coro in coros]


# values copied from concurrent.futures, which then also match asyncio
ALL_COMPLETED = 'ALL_COMPLETED'
FIRST_COMPLETED = 'FIRST_COMPLETED'
FIRST_EXCEPTION = 'FIRST_EXCEPTION'

async def wait(coros_or_futures, return_when=ALL_COMPLETED):
    """
    Wait for coroutines or futures to complete.
    Returns a pair of sets of futures, done and pending.
    If return_when is FIRST_COMPLETED, return as soon as any coroutine completes.
    If return_when is FIRST_EXCEPTION, the coroutine returns as soon as any
    coroutine completes by raising an exception. If no coroutine raises an
    exception, FIRST_EXCEPTION is equivalent to ALL_COMPLETED.
    """
    pending = set()
    done = set()
    finished = False
    future_impl = _get_future_impl()

    def on_done(fut):
        nonlocal finished
        if finished:
            return

        pending.remove(fut)
        done.add(fut)
        if not pending:
            finished = True
            cont()
            return

        if return_when == 'FIRST_EXCEPTION':
            try:
                fut.result()
            except Exception:
                finished = True
                cont()
                return

        if return_when == 'FIRST_COMPLETED':
            finished = True
            cont()

    async with suspending() as cont:
        for fut in coros_or_futures:
            if not isinstance(fut, future_impl):
                new_fut = future_impl()
                start(fut, future=new_fut)
                fut = new_fut
            pending.add(fut)

        # Must be a separate loop, as done callbacks can start executing
        # immediately, and we want pending to be initialized by then
        for fut in list(pending):
            fut.add_done_callback(on_done)

    # Point of suspension/resumption.  "finished = True" cannot be here
    # because we on_done must not invoke cont twice even when the done
    # callback is invoked before the suspension even happened.
    return done, pending
