import pytest

from pomp.core.utils import (
    iterator, switch_to_asyncio, Planned, CancelledError, NotDoneYetError,
)


def test_iterator():

    assert hasattr(iterator('a'), '__iter__')
    assert list(iterator('a')) == ['a']

    assert hasattr(iterator(1), '__iter__')

    assert hasattr(iterator(iterator('b')), '__iter__')


def test_planned():

    planned = Planned()

    assert not planned.cancelled()
    assert not planned.done()

    with pytest.raises(NotDoneYetError):
        planned.result()

    def cb1(result):
        pass

    def cb2(result):
        raise RuntimeError("some test exception")

    planned.add_done_callback(cb1)
    planned.add_done_callback(cb2)

    planned.set_result('ok')

    assert not planned.cancelled()
    assert planned.done()
    assert planned.result() == 'ok'

    planned = Planned()
    planned.cancel()

    with pytest.raises(CancelledError):
        planned.result()


def test_switch_to_asyncio():

    def method():  # asyncio: async
        # asyncio: future = dict()
        x()  # asyncio: y(REPLACE)  # noqa
        z()  # asyncio: await  # noqa
        l = m()  # asyncio: await  # noqa
        i = l()  # asyncio: await _co(REPLACE) # noqa
        return k()  # asyncio: await  # noqa

    result = '\n'.join(switch_to_asyncio(method))
    TO_CHECK = (
        'async def method()',
        'future = dict()',
        'y(x())',
        'await z()',
        'l = await m()',
        'i = await _co(l())',
        'return await k()',
    )
    for check in TO_CHECK:
        assert check in result
