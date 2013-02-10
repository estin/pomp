import types


def iterator(var):

    if isinstance(var, types.GeneratorType):
        return var

    if isinstance(var, list) or isinstance(var, tuple):
        return iter(var)

    return iter((var,))


def isstring(obj):
    try:
        return isinstance(obj, basestring)
    except NameError:
        return isinstance(obj, str)
