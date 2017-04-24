import sys
import types
import logging
import inspect
import itertools


PY3 = False if sys.version_info < (3, 0) else True
ITERATOR_TYPES = (
    list, tuple, set,
    types.GeneratorType, itertools.chain,
)

log = logging.getLogger(__name__)


def iterator(var):
    if isinstance(var, ITERATOR_TYPES):
        return var

    return (var,)


def isstring(obj):
    if not PY3:
        return isinstance(obj, basestring)  # noqa
    return isinstance(obj, str)


def switch_to_asyncio(method, skip_spaces=4):
    for line in inspect.getsourcelines(method)[0]:
        if '# asyncio:' not in line:
            yield line[skip_spaces:]
        else:
            indent = ' ' * (len(line) - len(line.lstrip()))
            line = line.replace('# noqa', '').strip()
            line, directive = line.split('# asyncio:')
            if 'REPLACE' in directive:
                prefix = ''
                if line.startswith('return'):
                    line = line.replace('return', '')
                    prefix = 'return '
                elif ' = ' in line:
                    left, right = line.split(' = ')
                    line = '{} = {}'.format(left.strip(), directive.replace("REPLACE", right.strip()).strip())  # noqa
                    yield '{0}{1} # by: {2}'.format(
                        indent,
                        line.strip(),
                        directive.strip(),
                    )[skip_spaces:]
                else:
                    yield '{0}{1} # by: {2}'.format(
                        indent,
                        directive.replace("REPLACE", line.strip()).strip(),
                        directive.strip(),
                    )[skip_spaces:]
            else:
                prefix = ''
                if line.startswith('return'):
                    line = line.replace('return', '')
                    prefix = 'return '
                elif ' = ' in line:
                    left, right = line.split(' = ')
                    directive = '{} = {} {}'.format(
                        left.strip(), directive.strip(), right.strip(),
                    )
                    line = ''
                yield '{0}{1}{2} {3} # by: {2}'.format(
                    indent,
                    prefix,
                    directive.strip(),
                    line.strip(),
                )[skip_spaces:]


# Planned like Future
# Possible future states (for internal use by the futures package).
PENDING = 'PENDING'
# The future was cancelled by the user...
CANCELLED = 'CANCELLED'
FINISHED = 'FINISHED'

_FUTURE_STATES = [
    PENDING,
    CANCELLED,
    FINISHED
]

_STATE_TO_DESCRIPTION_MAP = {
    PENDING: "pending",
    CANCELLED: "cancelled",
    FINISHED: "finished"
}


class Error(Exception):
    """Base class for all planned-related exceptions."""
    pass


class CancelledError(Error):
    """The Planned was cancelled."""
    pass


class NotDoneYetError(Error):
    """The Planned was not completed."""
    pass


class Planned(object):
    """Clone of `Future object`_, but without thread conditions (locks).

    Represents the result of an asynchronous computation.

    .. _Future object: https://docs.python.org/3/library
                       /concurrent.futures.html#concurrent.futures.Future
    """

    def __init__(self):
        """Initializes the future"""
        self._state = PENDING
        self._result = None
        self._done_callbacks = []

    def _invoke_callbacks(self):
        for callback in self._done_callbacks:
            try:
                callback(self)
            except Exception:  # pragma: no cover
                log.exception('exception calling callback for %r', self)

    def __repr__(self):  # pragma: no cover
        if self._state == FINISHED:
            return '<Planned at %s state=%s returned %s>' % (
                hex(id(self)),
                _STATE_TO_DESCRIPTION_MAP[self._state],
                self._result.__class__.__name__,
            )
        return '<Planned at %s state=%s>' % (
            hex(id(self)),
            _STATE_TO_DESCRIPTION_MAP[self._state]
        )

    def cancel(self):
        """Cancel the future if possible.

        Returns True if the future was cancelled, False otherwise. A future
        cannot be cancelled if it is running or has already completed.
        """
        if self._state in (FINISHED, ):
            return False

        if self._state in (CANCELLED, ):
            return True

        self._state = CANCELLED
        self._invoke_callbacks()
        return True

    def cancelled(self):
        """Return True if the future was cancelled."""
        return self._state in (CANCELLED, )

    def done(self):
        """Return True of the future was cancelled or finished executing."""
        return self._state in (CANCELLED, FINISHED, )

    def __get_result(self):
        return self._result

    def add_done_callback(self, fn):
        """Attaches a callable that will be called when the future finishes.

        Args:
            fn: A callable that will be called with this future as its only
                argument when the future completes or is cancelled. If the
                future has already completed or been cancelled then the
                callable will be called immediately. These
                callables are called in the order that they were added.
        """
        if self._state not in (CANCELLED, FINISHED):
            self._done_callbacks.append(fn)
            return
        fn(self)

    def result(self):
        """Return the result of the call that the future represents.

        Returns:
            The result of the call that the future represents.

        Raises:
            CancelledError: If the future was cancelled.
            Exception: If the call raised then that exception will be raised.
        """
        if self._state in (CANCELLED, ):
            raise CancelledError()
        elif self._state == FINISHED:
            return self.__get_result()
        else:
            raise NotDoneYetError()

    def set_result(self, result):
        """Sets the return value of work associated with the future.

        Should only be used by Executor implementations and unit tests.
        """
        self._result = result
        self._state = FINISHED
        self._invoke_callbacks()
