import corocc

def raise_stopiteration():
    raise StopIteration

class GenImpl:
    def __iter__(self):
        return self

    def __next__(self):
        self._cont()
        if not hasattr(self, '_nextval'):
            self._cont = raise_stopiteration
            raise StopIteration
        val = self._nextval
        del self._nextval
        return val

    @staticmethod
    async def _yield(val):
        async with corocc.suspending() as cont:
            self = cont.start_data
            self._nextval = val
            self._cont = cont

def generator(corofn):
    def impl(*args, **kwds):
        gen = GenImpl()
        coro = corofn(*args, **kwds)
        gen._cont = lambda: corocc.start(coro, data=gen)
        return gen
    return impl

yield_ = GenImpl._yield


if __name__ == '__main__':
    @generator
    async def sample():
        await yield_(1)
        await yield_(2)

    print(list(sample()))
