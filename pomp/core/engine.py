"""
Engine
"""
import sys
import types
import logging
import itertools
import threading

from pomp.core.item import Item
from pomp.core.base import (
    BaseEngine, BaseCommand, BaseQueue, BaseHttpRequest, BaseDownloadException,
)
from pomp.core.utils import (
    iterator, isstring,  Planned,
)

try:
    import Queue as queue
except ImportError:
    import queue


log = logging.getLogger('pomp.engine')


class StopCommand(BaseCommand):
    pass


class SimpleQueue(BaseQueue):

    def __init__(self, use_lifo=False):
        self.q = queue.Queue() if use_lifo else queue.LifoQueue()

    def get_requests(self):
        r = self.q.get()
        return r

    def put_requests(self, requests):
        self.q.put(requests)


class Pomp(BaseEngine):
    """Configuration object

    Main goal of class is to glue together all parts of application:

    - Downloader implementation with middlewares
    - Item pipelines
    - Crawler

    :param downloader: :class:`pomp.core.base.BaseDownloader`
    :param pipelines: list of item pipelines
                      :class:`pomp.core.base.BasePipeline`
    :param queue: external queue, instance of :class:`pomp.core.base.BaseQueue`
    :param breadth_first: use BFO order or DFO order, sensibly if used internal
                          queue only
    """
    DEFAULT_QUEUE_CLASS = SimpleQueue

    def __init__(
            self, downloader, pipelines=None, queue=None, breadth_first=False):
        self.downloader = downloader
        self.pipelines = pipelines or tuple()
        self.queue = queue or self.DEFAULT_QUEUE_CLASS(
            use_lifo=not breadth_first
        )

    def response_callback(self, crawler, response):
        try:
            if not isinstance(response, BaseDownloadException):
                return self.on_response(crawler, response)
        except Exception as e:
            log.exception("On response processing")
            self.downloader._process_exception(
                BaseDownloadException(
                    response,
                    exception=e,
                    exc_info=sys.exc_info(),
                )
            )

    def on_response(self, crawler, response):

        result = crawler.process(response)

        if isinstance(result, types.GeneratorType):
            requests_from_items = []
            for items in result:
                requests_from_items += self._process_result(
                    crawler, iterator(items)
                )
        else:
            requests_from_items = self._process_result(
                crawler, iterator(result)
            )

        if requests_from_items:
            # chain result of crawler extract_items and next_requests methods
            _requests = crawler.next_requests(response)
            if _requests:
                next_requests = itertools.chain(
                    requests_from_items,
                    iterator(_requests),
                )
            else:
                next_requests = requests_from_items
        else:
            next_requests = crawler.next_requests(response)

        return next_requests

    def _process_result(self, crawler, items):
        # requests may be yield with items
        next_requests = list(filter(
            lambda i: isinstance(i, BaseHttpRequest) or isstring(i),
            items,
        ))

        # filter items by instance type
        items = filter(
            lambda i: isinstance(i, Item),
            items,
        )

        # pipe items
        for pipe in self.pipelines:
            items = list(filter(
                None,
                map(
                    lambda i: pipe.process(crawler, i),
                    items
                ),
            ))

        return next_requests

    def process_requests(self, requests, crawler):
        for response in self.downloader.process(requests, crawler):
            if isinstance(response, Planned):
                def _(r):
                    self._put_requests(
                        self.response_callback(crawler, r.result())
                    )
                    self._request_done()
                response.add_done_callback(_)
            else:
                self._put_requests(
                    self.response_callback(
                        crawler, response
                    )
                )
                self._request_done()

    def prepare(self, crawler):
        log.info('Prepare downloader: %s', self.downloader)
        self.downloader.prepare()
        self.in_progress = 0

        log.info('Start crawler: %s', crawler)

        for pipe in self.pipelines:
            log.info('Start pipe: %s', pipe)
            pipe.start(crawler)

        # add ENTRY_REQUESTS to the queue
        next_requests = getattr(crawler, 'ENTRY_REQUESTS', None)
        if next_requests:
            self._put_requests(
                iterator(next_requests)
            )

        # configure queue semaphore
        self.queue_semaphore = self.get_queue_semaphore()

    def finish(self, crawler):
        for pipe in self.pipelines:
            log.info('Stop pipe: %s', pipe)
            pipe.stop(crawler)
        log.info('Stop crawler: %s', crawler)

    def pump(self, crawler):
        """Start crawling

        :param crawler: isntance of :class:`pomp.core.base.BaseCrawler`
        """
        self.prepare(crawler)

        while True:

            # do not fetch from queue request more than downloader can process
            if self.queue_semaphore:
                self.queue_semaphore.acquire(blocking=True)

            next_requests = self.queue.get_requests()
            if isinstance(next_requests, StopCommand):
                break
            self.process_requests(
                iterator(next_requests), crawler,
            )

        self.finish(crawler)

    def _put_requests(self, requests):
        if not requests:
            return
        for request in requests:
            self.in_progress += 1
            self.queue.put_requests(request)

    def _request_done(self):
        if self.queue_semaphore:
            self.queue_semaphore.release()

        self.in_progress -= 1
        if self.in_progress == 0:
            # work done
            self.queue.put_requests(StopCommand())

    def get_queue_semaphore(self):
        workers_count = self.downloader.get_workers_count()
        if workers_count > 1:
            return threading.BoundedSemaphore(workers_count)
