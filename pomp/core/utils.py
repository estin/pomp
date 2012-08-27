import types


def iterator(var):

    if isinstance(var, types.GeneratorType):
        return var

    if isinstance(var, types.ListType) or isinstance(var, types.TupleType):
        return iter(var)

    return iter((var,))
