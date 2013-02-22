import types
import defer


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


class DeferredList(defer.Deferred):

    def __init__(self, deferredList):
        """Initialize a DeferredList"""
        self.result_list = [None] * len(deferredList)
        super(DeferredList, self).__init__()

        self.finished_count = 0

        for index, deferred in enumerate(deferredList):
            deferred.add_callbacks(
                self._cb_deferred,
                self._cb_deferred,
                callback_args=(index,),
                errback_args=(index,)
            )

    def _cb_deferred(self, result, index):
        """(internal) Callback for when one of my deferreds fires.
        """
        self.result_list[index] = result

        self.finished_count += 1
        if self.finished_count == len(self.result_list):
            self.callback(self.result_list)

        return result
