import pickle
from pomp.contrib.item import Item, Field


class TItem(Item):
    f1 = Field()
    f2 = Field()
    f3 = Field()


def test_item():

    # item as a dict
    i = TItem()
    assert ['f1', 'f2', 'f3'] == list(i.keys())

    i.f1 = 1
    i.f3 = 3
    assert [1, None, 3] == list(i.values())

    # item as a object
    i = TItem('f1', f3='f3', f2='f2')
    assert i.f1 == 'f1'
    assert i.f2 == 'f2'
    assert i.f3 == 'f3'
    assert ['f1', 'f2', 'f3'] == list(i.keys())

    # change attributes
    i.f1 = 'f1_new'
    i.f2 = 'f2_new'
    assert i.f1 == 'f1_new'
    assert i.f2 == 'f2_new'
    assert i.f3 == 'f3'
    assert ['f1', 'f2', 'f3'] == list(i.keys())

    # pickling
    assert i == pickle.loads(pickle.dumps(i))
