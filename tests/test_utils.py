from pomp.core.utils import iterator


def test_iterator():

    assert hasattr(iterator('a'), '__iter__')
    assert list(iterator('a')) == ['a']

    assert hasattr(iterator(1), '__iter__')

    assert hasattr(iterator(iterator('b')), '__iter__')
