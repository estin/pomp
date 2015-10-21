"""
Concurrent downloaders
"""
import os
import sys
import logging
from functools import partial
from concurrent.futures import ProcessPoolExecutor

from pomp.core.base import BaseDownloader, BaseDownloadException
from pomp.contrib.urllibtools import UrllibDownloadWorker
from pomp.core.utils import Planned


log = logging.getLogger('pomp.contrib.concurrent')


def _run_worker(params, request):
    pid = os.getpid()
    log.debug("Worker pid=%s params=%s", pid, params)
    try:
        # Initialize worker and call get_one method
        return params['worker_class'](
            **params.get('worker_kwargs', {})
        ).get_one(request)
    except Exception:
        log.exception("Exception on worker pid=%s request=%s", pid, request)
        raise


class ConcurrentDownloader(BaseDownloader):
    """Concurrent ProcessPoolExecutor downloader

    :param pool_size: size of ThreadPoolExecutor
    :param timeout: request timeout in seconds
    """
    def __init__(
            self, worker_class,
            worker_kwargs=None, pool_size=5, middlewares=None,):

        # configure executor
        self.executor = ProcessPoolExecutor(max_workers=pool_size)

        # prepare worker params
        self.worker_params = {
            'worker_class': worker_class,
            'worker_kwargs': worker_kwargs or {},
        }

        super(ConcurrentDownloader, self).__init__(
            middlewares=middlewares
        )

    def _done(self, request, done_future, future):
        try:
            response = future.result()
        except Exception as e:
            log.exception('Exception on %s', request)
            done_future.set_result(BaseDownloadException(
                request,
                exception=e,
                exc_info=sys.exc_info(),
            ))
        else:
            done_future.set_result(response)

    def get(self, requests):

        for request in requests:
            # delegate request processing to the executor
            future = self.executor.submit(
                _run_worker, self.worker_params, request
            )

            # build Planned object
            done_future = Planned()

            # when executor finish request - fire done_future
            future.add_done_callback(
                partial(self._done, request, done_future)
            )

            yield done_future


class ConcurrentUrllibDownloader(ConcurrentDownloader):
    """Concurrent ProcessPoolExecutor downloader for fetching data by urllib
    :class:`pomp.contrib.SimpleDownloader`

    :param pool_size: pool size of ProcessPoolExecutor
    :param timeout: request timeout in seconds
    """
    def __init__(self, pool_size=5, timeout=5, middlewares=None,):
        super(ConcurrentUrllibDownloader, self).__init__(
            pool_size=pool_size,
            worker_class=UrllibDownloadWorker,
            worker_kwargs={
                'timeout': timeout
            },
            middlewares=middlewares,
        )
