# corocc

The `corocc` module implements execution of coroutines with explicit
suspend and continuation, inspired by Kotlin.

This is useful for integrating coroutines with environments that can't
run a full PEP 3156 event loop, but that still provide support for
executing callbacks.

See [the blog post](https://morestina.net/blog/1253/continuations) for
additional details.

## Examples:

An equivalent of `asyncio.sleep()` which continues the current
coroutine in a different thread:

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

A `sleep` coroutine that works inside a GLib main loop:

```python
async def sleep(delay):
    async with corocc.suspending() as cont:
        GLib.timeout_add(delay * 1000, cont)
```

## License

`corocc` is distributed under the terms of the MIT license, see
[LICENSE-MIT](LICENSE-MIT) for details.  Contributing changes is
assumed to signal agreement with these licensing terms.
