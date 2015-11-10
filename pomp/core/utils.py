import sys
import types
import logging
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


# Planned like Future
# Possible future states (for internal use by the futures package).
PENDING = 'PENDING'
RUNNING = 'RUNNING'
# The future was cancelled by the user...
CANCELLED = 'CANCELLED'
# ...and _Waiter.add_cancelled() was called by a worker.
CANCELLED_AND_NOTIFIED = 'CANCELLED_AND_NOTIFIED'
FINISHED = 'FINISHED'

_FUTURE_STATES = [
    PENDING,
    RUNNING,
    CANCELLED,
    CANCELLED_AND_NOTIFIED,
    FINISHED
]

_STATE_TO_DESCRIPTION_MAP = {
    PENDING: "pending",
    RUNNING: "running",
    CANCELLED: "cancelled",
    CANCELLED_AND_NOTIFIED: "cancelled",
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
        self._exception = None
        self._waiters = []
        self._done_callbacks = []

    def _invoke_callbacks(self):
        for callback in self._done_callbacks:
            try:
                callback(self)
            except Exception:  # pragma: no cover
                log.exception('exception calling callback for %r', self)

    def __repr__(self):  # pragma: no cover
        if self._state == FINISHED:
            if self._exception:
                return '<Planned at %s state=%s raised %s>' % (
                    hex(id(self)),
                    _STATE_TO_DESCRIPTION_MAP[self._state],
                    self._exception.__class__.__name__,
                )
            else:
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
        if self._state in [RUNNING, FINISHED]:
            return False

        if self._state in [CANCELLED, CANCELLED_AND_NOTIFIED]:
            return True

        self._state = CANCELLED
        self._invoke_callbacks()
        return True

    def cancelled(self):
        """Return True if the future was cancelled."""
        return self._state in [CANCELLED, CANCELLED_AND_NOTIFIED]

    def running(self):
        """Return True if the future is currently executing."""
        return self._state == RUNNING

    def done(self):
        """Return True of the future was cancelled or finished executing."""
        return self._state in [CANCELLED, CANCELLED_AND_NOTIFIED, FINISHED]

    def __get_result(self):
        if self._exception:
            raise self._exception
        else:
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
        if self._state not in [CANCELLED, CANCELLED_AND_NOTIFIED, FINISHED]:
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
        if self._state in [CANCELLED, CANCELLED_AND_NOTIFIED]:
            raise CancelledError()
        elif self._state == FINISHED:
            return self.__get_result()
        else:
            raise NotDoneYetError()

    def exception(self):
        """Return the exception raised by the call that the future represents.

        Returns:
            The exception raised by the call that the future represents or None
            if the call completed without raising.

        Raises:
            CancelledError: If the future was cancelled.
        """

        if self._state in [CANCELLED, CANCELLED_AND_NOTIFIED]:
            raise CancelledError()
        elif self._state == FINISHED:
            return self._exception

    # The following methods should only be used by Executors and in tests.
    def set_running_or_notify_cancel(self):
        """Mark the future as running or process any cancel notifications.

        Should only be used by Executor implementations and unit tests.

        If the future has been cancelled (cancel() was called and returned
        True) then any threads waiting on the future completing (though calls
        to as_completed() or wait()) are notified and False is returned.

        If the future was not cancelled then it is put in the running state
        (future calls to running() will return True) and True is returned.

        This method should be called by Executor implementations before
        executing the work associated with this future. If this method returns
        False then the work should not be executed.

        Returns:
            False if the Planned was cancelled, True otherwise.

        Raises:
            RuntimeError: if this method was already called or if set_result()
                or set_exception() was called.
        """
        if self._state == CANCELLED:
            self._state = CANCELLED_AND_NOTIFIED
            for waiter in self._waiters:
                waiter.add_cancelled(self)
            return False
        elif self._state == PENDING:
            self._state = RUNNING
            return True
        else:
            log.critical(
                'Planned %s in unexpected state: %s',
                id(self),
                self._state,
            )
            raise RuntimeError('Planned in unexpected state')

    def set_result(self, result):
        """Sets the return value of work associated with the future.

        Should only be used by Executor implementations and unit tests.
        """
        self._result = result
        self._state = FINISHED
        for waiter in self._waiters:
            waiter.add_result(self)
        self._invoke_callbacks()

    def set_exception(self, exception):
        """Sets the result of the future as being the given exception.

        Should only be used by Executor implementations and unit tests.
        """
        self._exception = exception
        self._state = FINISHED
        for waiter in self._waiters:
            waiter.add_exception(self)
        self._invoke_callbacks()
