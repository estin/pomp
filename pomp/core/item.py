"""
Item
"""
import inspect
from collections import OrderedDict


class Item(OrderedDict):

    def __init__(self, *args, **kwargs):
        # Initialize empty ordered dict
        super(Item, self).__init__(self)

        # Populate ordered dict
        _args = list(args[:])
        _args.reverse()
        for field, obj in inspect.getmembers(self.__class__):
            if isinstance(obj, Field):
                value = _args.pop() if _args else kwargs.get(field, None)
                super(Item, self).__setitem__(field, value)

    def __setattr__(self, key, value):
        if key in self:
            super(Item, self).__setitem__(key, value)
        super(Item, self).__setattr__(key, value)


class Field(object):
    pass
