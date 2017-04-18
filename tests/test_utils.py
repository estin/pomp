import pytest

from pomp.core.utils import iterator, Planned, CancelledError, NotDoneYetError


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
