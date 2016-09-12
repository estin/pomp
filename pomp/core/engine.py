"""
Engine
"""
import sys
import types
import logging
import itertools
import threading

from pomp.core.base import (
    BaseEngine, BaseCommand, BaseQueue, BaseHttpRequest, BaseCrawlException,
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

    def get_requests(self, count=None):
        r = self.q.get()
        return r

    def put_requests(self, requests):
        self.q.put(requests)


class Pomp(BaseEngine):
    """Configuration object

    This class glues together all parts of a Pomp instance:

    - Downloader implementation and middleware
    - Item pipelines
    - Crawler

    :param downloader: :class:`pomp.core.base.BaseDownloader`
    :param middlewares: list of middlewares, instances
                        of :class:`BaseMiddleware`
    :param pipelines: list of item pipelines
                      :class:`pomp.core.base.BasePipeline`
    :param queue: external queue, instance of :class:`pomp.core.base.BaseQueue`
    :param breadth_first: use BFO order or DFO order, sensibly if used internal
                          queue only
    """
    DEFAULT_QUEUE_CLASS = SimpleQueue

    def __init__(
            self, downloader, middlewares=None, pipelines=None,
            queue=None, breadth_first=False):
        self.downloader = downloader

        self.middlewares = middlewares or []
        if isinstance(self.middlewares, tuple):
            self.middlewares = list(self.middlewares)

        self.pipelines = pipelines or tuple()
        self.queue = queue or self.DEFAULT_QUEUE_CLASS(
            use_lifo=not breadth_first
        )
        self.queue_lock = None
        self.queue_semaphore_value = None
        self.workers_count = None
        self._is_internal_queue = isinstance(
            self.queue, self.DEFAULT_QUEUE_CLASS,
        )

    def response_callback(self, crawler, response):
        try:
            if not isinstance(response, BaseCrawlException):
                return self.on_response(crawler, response)
        except Exception as e:
            log.exception("On response processing")
            self._exception_middlewares(
                BaseCrawlException(
                    request=response.request,
                    response=response,
                    exception=e,
                    exc_info=sys.exc_info(),
                ),
                crawler,
            )

    def on_parse_result(self, crawler, result, response):
        requests_from_items = ()
        if isinstance(result, types.GeneratorType):
            for items in result:
                requests_from_items = itertools.chain(
                    requests_from_items,
                    self._process_items(
                        crawler, iterator(items), response=response,
                    )
                )
        else:
            requests_from_items = self._process_items(
                crawler, iterator(result), response=response,
            )

        next_requests = crawler.next_requests(response)

        if requests_from_items:
            if next_requests:
                # chain result of crawler extract_items
                # and next_requests methods
                next_requests = itertools.chain(
                    requests_from_items,
                    iterator(next_requests),
                )
            else:
                next_requests = requests_from_items

        return next_requests

    def on_response(self, crawler, response):

        result = crawler.process(response)

        if isinstance(result, Planned):
            planned = Planned()

            def _(r):
                result = r.result()

                if isinstance(result, BaseCrawlException):
                    self._exception_middlewares(result, crawler)
                    planned.set_result(None)
                else:
                    planned.set_result(
                        self.on_parse_result(crawler, result, response)
                    )

            result.add_done_callback(_)
            return planned

        else:
            return self.on_parse_result(crawler, result, response)

    def process_requests(self, requests, crawler):

        # execute requests by downloader
        for response in self.downloader.process(
                # process requests by middlewares
                self._req_middlewares(requests, crawler), crawler):

            if response is None:
                # response was rejected by middlewares
                pass

            elif isinstance(response, Planned):  # async behaviour
                def _(r):
                    # put new requests to queue
                    response = r.result()
                    self._put_requests(
                        # process response by crawler
                        self.response_callback(
                            crawler,
                            # pass response to middlewares
                            self._resp_middlewares(response, crawler),
                        ),
                        response=response,
                        crawler=crawler,
                    )
                response.add_done_callback(_)

            else:  # sync behavior
                # put new requests to queue
                self._put_requests(
                    # process response by crawler
                    self.response_callback(
                        crawler,
                        # pass response to middlewares
                        self._resp_middlewares(response, crawler),
                    ),
                    response=response,
                    crawler=crawler,
                )

    def prepare(self, crawler):
        # prepare middleware chain
        self.request_middlewares = self.middlewares
        self.response_middlewares = self.middlewares[:]
        self.response_middlewares.reverse()

        log.info('Prepare downloader: %s', self.downloader)
        self.downloader.prepare()
        self.in_progress = 0

        log.info('Start crawler: %s', crawler)

        for pipe in self.pipelines:
            log.info('Start pipe: %s', pipe)
            try:
                pipe.start(crawler)
            except Exception as e:
                log.exception("On pipe start")
                self._exception_middlewares(
                    BaseCrawlException(
                        request=None,
                        response=None,
                        exception=e,
                        exc_info=sys.exc_info(),
                    ),
                    crawler,
                )

        # configure queue semaphore
        self.queue_lock = self.get_queue_lock()

    def finish(self, crawler):
        self.downloader.stop()
        for pipe in self.pipelines:
            log.info('Stop pipe: %s', pipe)
            try:
                pipe.stop(crawler)
            except Exception as e:
                log.exception("On pipe stop")
                self._exception_middlewares(
                    BaseCrawlException(
                        request=None,
                        response=None,
                        exception=e,
                        exc_info=sys.exc_info(),
                    ),
                    crawler,
                )
        log.info('Stop crawler: %s', crawler)

    def pump(self, crawler):
        """Start crawling

        :param crawler: instance of :class:`pomp.core.base.BaseCrawler`
        """
        self.prepare(crawler)

        # add ENTRY_REQUESTS to the queue
        next_requests = getattr(crawler, 'ENTRY_REQUESTS', None)
        if next_requests:
            self._put_requests(
                iterator(next_requests), None, request_done=False,
            )

        while True:

            # pre-lock
            if self.queue_lock:
                self.queue_lock.acquire(True)

            next_requests = self.queue.get_requests(
                count=self.queue_semaphore_value
            )

            if isinstance(next_requests, StopCommand):
                break

            self.process_requests(
                iterator(next_requests), crawler,
            )

            # block loop if requests in process more than downloader
            # can fetch
            if self.queue_lock:
                if self.queue_semaphore_value <= 0:
                    self.queue_lock.acquire(True)
                elif self.queue_lock.locked():
                    self.queue_lock.release()

        self.finish(crawler)

    def get_queue_lock(self):
        workers_count = self.downloader.get_workers_count()
        if workers_count >= 1:
            self.workers_count = workers_count
            self.queue_semaphore_value = workers_count
            return threading.Lock()

    def _process_items(self, crawler, items, response=None):

        for item in items:

            if not item:
                continue

            # yield item as request
            if isinstance(item, BaseHttpRequest) or isstring(item):
                yield item
            else:
                # proccess item as data item by pipes
                for pipe in self.pipelines:
                    try:
                        item = pipe.process(crawler, item)
                    except Exception as e:
                        log.exception("On pipe process")
                        self._exception_middlewares(
                            BaseCrawlException(
                                request=response.request,
                                response=response,
                                exception=e,
                                exc_info=sys.exc_info(),
                            ),
                            crawler,
                        )
                    else:
                        # item filtered - stop pipe processing
                        if not item:
                            log.debug(
                                "Stop item processing. Pipeline %s on %s",
                                pipe, item,
                            )
                            break

    def _req_middlewares(self, requests, crawler):
        # pass requests to middlewares
        for request in requests:

            # decrement count of available requests to fetch
            if self.queue_lock:
                self.queue_semaphore_value -= 1

            for middleware in self.request_middlewares:
                try:
                    request = middleware.process_request(
                        request,
                        crawler,
                        self.downloader,
                    )
                except Exception as e:
                    log.exception(
                        'Exception on process %s by %s', request, middleware)

                    # yield exception instance instead of request
                    # do not break request-response processing logic
                    yield BaseCrawlException(
                        request=request,
                        response=None,
                        exception=e,
                        exc_info=sys.exc_info(),
                    )

                    # mark to stop request processing
                    request = None

                # stop middleware chain
                if not request:
                    log.debug(
                        "Stop request processing. Middleware %s on %s",
                        middleware, request,
                    )
                    break

            if request:
                yield request

    def _resp_middlewares(self, response, crawler):
        # pass response to middlewares
        is_error = isinstance(response, BaseCrawlException)
        func = 'process_response' if not is_error else 'process_exception'

        for middleware in self.response_middlewares:
            try:
                value = getattr(middleware, func)(
                    response, crawler, self.downloader,
                )
            except Exception as e:
                log.exception(
                    'Exception on process %s by %s', response, middleware)
                response = self._exception_middlewares(
                    BaseCrawlException(
                        request=response.request,
                        response=response,
                        exception=e,
                        exc_info=sys.exc_info(),
                    ),
                    crawler,
                )
                value = None  # stop processing response by middlewares
            if not value:
                log.debug(
                    "Stop response processing. Middleware %s on %s",
                    middleware, response,
                )
                break
            response = value

        return response

    def _exception_middlewares(self, exception, crawler):
        value = None
        for middleware in self.response_middlewares:
            try:
                value = middleware.process_exception(
                    exception, crawler, self.downloader,
                )
                if value is None:  # stop processing exception
                    log.debug(
                        "Stop exception processing. Middleware %s on %s",
                        middleware, value,
                    )
                    break
            except Exception:
                log.exception(
                    'Exception on process %s by %s', exception, middleware
                )
        return value

    def _put_requests(
            self, requests, response=None, crawler=None, request_done=True):

        def _put(items):
            if items:
                for item in items:
                    self.in_progress += 1
                    self.queue.put_requests(item)
            if request_done:
                self._request_done(response, crawler)

        if isinstance(requests, Planned):
            def _(r):
                _put(r.result())
            requests.add_done_callback(_)
        else:
            _put(requests)

    def _request_done(self, response, crawler):
        if self.queue_lock:
            # increment counter, but not more then workers count
            self.queue_semaphore_value = min(
                self.workers_count,
                self.queue_semaphore_value + 1,
            )
            if self.queue_semaphore_value > 0 and self.queue_lock.locked():
                self.queue_lock.release()

        self.in_progress -= 1

        # send StopCommand if all jobs are done and running on internal queue
        if self._is_internal_queue and self.in_progress == 0:
            # work done
            self.queue.put_requests(StopCommand())

        # response processing complete
        try:
            crawler.on_processing_done(response)
        except Exception as e:
            log.exception("On done processing exception")
            self._exception_middlewares(
                BaseCrawlException(
                    request=response.request,
                    response=response,
                    exception=e,
                    exc_info=sys.exc_info(),
                ),
                crawler,
            )
