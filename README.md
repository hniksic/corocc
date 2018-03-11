# corocc

The `corocc` module implements execution of coroutines with explicit
suspend and continuation, inspired by Kotlin.

This is useful for integrating coroutines with environments that can't
run a full PEP 3156 event loop, but that still provide support for
executing callbacks.

See [the blog post](https://morestina.net/blog/1253/continuations) for
details about the topic.

## Examples:

`corocc` allows a coroutine to willingly suspend itself and, before
suspension, get a reference to a callable that will continue its
execution.  Here is a very simple example that just stores the
continuation in a global variable:

```python
import corocc

async def always_suspending():
    global cont
    i = 1
    while True:
        async with corocc.suspending() as cont:
            print('suspension', i)
            i += 1

>>> corocc.start(always_suspending())
suspension 1
>>> cont()
suspension 2
>>> cont()
suspension 3
...
```

This doesn't look too useful since driving a coroutine from the
outside can be achieved with the `send` coroutine method.  But
`corocc` allows for the coroutine to continue itself, _without_
relying on an outside agent to "drive" it.

For example, this is an equivalent of `asyncio.sleep()` which
continues the current coroutine in a different thread:

```python
import corocc, threading

async def thread_sleep(delay):
    async with corocc.suspending() as cont:
        t = threading.Timer(delay, cont)
        t.start()

async def greet():
    print('hello...')
    await thread_sleep(1)
    print('...world')

>>> corocc.start(greet())
hello...
>>> ...world
```

An equivalent coroutine that uses the GLib main loop:

```python
async def glib_sleep(delay):
    async with corocc.suspending() as cont:
        GLib.timeout_add(delay * 1000, cont)
```

## License

`corocc` is distributed under the terms of the MIT license, see
[LICENSE-MIT](LICENSE-MIT) for details.  Contributing changes is
assumed to signal agreement with these licensing terms.
