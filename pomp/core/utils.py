import sys
import types
import itertools

import defer


PY3 = False if sys.version_info < (3, 0) else True
ITERATOR_TYPES = (
    list, tuple, set,
    types.GeneratorType, itertools.chain,
)


def iterator(var):
    if isinstance(var, ITERATOR_TYPES):
        return var

    return (var,)


def isstring(obj):
    if not PY3:
        return isinstance(obj, basestring)  # noqa
    return isinstance(obj, str)


class DeferredList(defer.Deferred):

    def __init__(self, deferredList):
        """Initialize a DeferredList"""
        self.result_list = [None] * len(deferredList)
        super(DeferredList, self).__init__()

        self.finished_count = 0

        for index, deferred in enumerate(deferredList):
            if isinstance(deferred, defer.Deferred):
                deferred.add_callbacks(
                    self._cb_deferred,
                    self._cb_deferred,
                    callback_args=(index,),
                    errback_args=(index,)
                )
            else:  # if request allready done
                self.finished_count += 1
                self.result_list[index] = deferred

        # check are deferreds or results was passed to __init__
        try:
            self.check_and_fire()
        except defer.AlreadyCalledDeferred:
            pass

    def _cb_deferred(self, result, index):
        """(internal) Callback for when one of my deferreds fires.
        """
        self.result_list[index] = result

        self.finished_count += 1
        self.check_and_fire()  # check is done and fire
        return result

    def check_and_fire(self):
        if self.finished_count == len(self.result_list):
            self.callback(self.result_list)
