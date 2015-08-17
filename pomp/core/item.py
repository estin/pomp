"""
Item and Field
"""
import inspect
from collections import OrderedDict


class Item(OrderedDict):
    """OrderedDict subclass"""

    def __init__(self, *args, **kwargs):
        # Initialize empty ordered dict
        super(Item, self).__init__(self)

        # Populate ordered dict
        _args = list(args[:])
        _args.reverse()
        fields_by_creation_counter = {}
        for field, obj in inspect.getmembers(self.__class__):
            if isinstance(obj, Field):
                fields_by_creation_counter[obj.counter] = field

        for key in sorted(fields_by_creation_counter):
            field = fields_by_creation_counter[key]
            value = _args.pop() if _args else kwargs.get(field, None)
            super(Item, self).__setitem__(field, value)

    def __setattr__(self, key, value):
        if key in self:
            super(Item, self).__setitem__(key, value)
        super(Item, self).__setattr__(key, value)

    def __getattribute__(self, key):
        value = super(Item, self).__getattribute__(key)

        # if attribute is a item field return it`s value, not a Field object
        if isinstance(value, Field):
            return self[key]

        return value


class Field(object):
    counter = 0

    def __init__(self):
        self.counter = Field.counter
        Field.counter += 1
