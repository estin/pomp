from nose.tools import assert_equal
from pomp.core.item import Item, Field


def test_item():
    class TItem(Item):
        f1 = Field()
        f2 = Field()
        f3 = Field()

    i = TItem()
    assert_equal(['f1', 'f2', 'f3'], list(i.keys()))

    i.f1 = 1
    i.f3 = 3
    assert_equal([1, None, 3], list(i.values()))
