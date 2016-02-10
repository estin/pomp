"""
Concurrent downloaders
"""
import os
import sys
import signal
import logging
import itertools
from functools import partial
from concurrent.futures import ProcessPoolExecutor

from pomp.core.base import (
    BaseCrawler, BaseDownloader, BaseCrawlException,
)
from pomp.contrib.urllibtools import UrllibDownloadWorker
from pomp.core.utils import iterator, Planned


log = logging.getLogger('pomp.contrib.concurrent')


def _run_download_worker(params, request):
    pid = os.getpid()
    log.debug("Download worker pid=%s params=%s", pid, params)
    try:
        # Initialize worker and call get_one method
        return params['worker_class'](
            **params.get('worker_kwargs', {})
        ).get_one(request)
    except Exception:
        log.exception(
            "Exception on download worker pid=%s request=%s", pid, request
        )
        raise


def _run_crawler_worker(params, response):
    pid = os.getpid()
    log.debug("Crawler worker pid=%s params=%s", pid, params)
    try:
        # Initialize crawler worker
        worker = params['worker_class'](**params.get('worker_kwargs', {}))

        # process response
        items = worker.extract_items(response)
        next_requests = worker.next_requests(response)

        if next_requests:
            return list(
                itertools.chain(
                    iterator(items),
                    iterator(next_requests),
                )
            )
        return list(iterator(items))

    except Exception:
        log.exception(
            "Exception on crawler worker pid=%s request=%s", pid, response
        )
        raise


class ConcurrentMixin(object):

    def _done(self, request, done_future, future):
        try:
            response = future.result()
        except Exception as e:
            log.exception('Exception on %s', request)
            done_future.set_result(BaseCrawlException(
                request,
                exception=e,
                exc_info=sys.exc_info(),
            ))
        else:
            done_future.set_result(response)


class ConcurrentDownloader(BaseDownloader, ConcurrentMixin):
    """Concurrent ProcessPoolExecutor downloader

    :param pool_size: size of ThreadPoolExecutor
    :param timeout: request timeout in seconds
    """
    def __init__(
            self, worker_class,
            worker_kwargs=None, pool_size=5,):

        # configure executor
        self.pool_size = pool_size
        self.executor = ProcessPoolExecutor(max_workers=self.pool_size)

        # prepare worker params
        self.worker_params = {
            'worker_class': worker_class,
            'worker_kwargs': worker_kwargs or {},
        }

        # ctrl-c support for python2.x
        # trap sigint
        signal.signal(signal.SIGINT, lambda s, f: s)

        super(ConcurrentDownloader, self).__init__()

    def get(self, requests):

        requests = list(requests)
        for request in requests:

            # delegate request processing to the executor
            future = self.executor.submit(
                _run_download_worker, self.worker_params, request,
            )

            # build Planned object
            done_future = Planned()

            # when executor finish request - fire done_future
            future.add_done_callback(
                partial(self._done, request, done_future)
            )

            yield done_future

    def get_workers_count(self):
        return self.pool_size

    def stop(self):
        self.executor.shutdown()


class ConcurrentUrllibDownloader(ConcurrentDownloader):
    """Concurrent ProcessPoolExecutor downloader for fetching data with urllib
    :class:`pomp.contrib.SimpleDownloader`

    :param pool_size: pool size of ProcessPoolExecutor
    :param timeout: request timeout in seconds
    """
    def __init__(self, pool_size=5, timeout=5):
        super(ConcurrentUrllibDownloader, self).__init__(
            pool_size=pool_size,
            worker_class=UrllibDownloadWorker,
            worker_kwargs={
                'timeout': timeout
            },
        )


class ConcurrentCrawler(BaseCrawler, ConcurrentMixin):
    """Concurrent ProcessPoolExecutor crawler

    :param pool_size: pool size of ProcessPoolExecutor
    :param timeout: request timeout in seconds
    """

    def __init__(self, worker_class, worker_kwargs=None, pool_size=5):

        # configure executor
        self.pool_size = pool_size
        self.executor = ProcessPoolExecutor(max_workers=self.pool_size)

        # prepare worker params
        self.worker_params = {
            'worker_class': worker_class,
            'worker_kwargs': worker_kwargs or {},
        }

        # inherit ENTRY_REQUESTS from worker_class
        self.ENTRY_REQUESTS = getattr(worker_class, 'ENTRY_REQUESTS', None)

    def process(self, response):
        # delegate response processing to the executor
        future = self.executor.submit(
            _run_crawler_worker, self.worker_params, response,
        )

        # build Planned object
        done_future = Planned()

        # when executor finish response processing - fire done_future
        future.add_done_callback(
            partial(self._done, response, done_future)
        )

        return done_future
