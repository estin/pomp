"""
Engine
"""
import sys
import types
import logging
import threading

from pomp.core.base import (
    BaseEngine,
    BaseCommand,
    BaseQueue,
    BaseRequest,
    BaseResponse,
    BaseHttpResponse,
    BaseCrawlException,
)
from pomp.core.utils import iterator

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
    LOCK_FACTORY = threading.Lock

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

    def response_callback(self, crawler, response):  # asyncio: async
        try:
            if not isinstance(response, BaseCrawlException):
                self.on_response(crawler, response)  # asyncio: await
            else:
                self._request_done(response, crawler)  # asyncio: await
        except Exception as e:
            log.exception("On response processing")
            self._exception_middlewares(  # asyncio: await
                BaseCrawlException(
                    request=response.get_request(),
                    response=response,
                    exception=e,
                    exc_info=sys.exc_info(),
                ),
                crawler,
            )

    def on_parse_result(self, crawler, result, response):  # asyncio: async
        if isinstance(result, types.GeneratorType):
            for items in result:
                for request in self._process_items(crawler, iterator(items), response=response):  # asyncio: async  # noqa
                    self._put_requests(   # asyncio: await
                        iterator(request),
                        crawler=crawler,
                        response=response,
                    )
        else:
            for request in self._process_items(crawler, iterator(result), response=response):  # asyncio: async  # noqa
                self._put_requests(   # asyncio: await
                    iterator(request),
                    crawler=crawler,
                    response=response,
                )

        next_requests = (
            crawler.next_requests(response)  # asyncio: await _co(REPLACE)
        )

        if hasattr(next_requests, '__anext__'):  # support async generators
            for request in next_requests:  # asyncio: async
                self._put_requests(  # asyncio: await
                    iterator(request),
                    crawler=crawler,
                    response=response,
                )
        else:
            self._put_requests(  # asyncio: await
                iterator(next_requests),
                crawler=crawler,
                response=response,
            )

        self._request_done(response, crawler)  # asyncio: await

    def on_response(self, crawler, response):  # asyncio: async

        try:
            result = crawler.process(response)  # asyncio: await _co(REPLACE)
        except Exception as e:
            self._exception_middlewares(e, crawler)  # asyncio: await
            result = None

        if hasattr(result, 'add_done_callback'):  # if Planned or Future object

            def _(r):
                result = r.result()
                if isinstance(result, BaseCrawlException):
                    def x():  # asyncio: async
                        self._exception_middlewares(result, crawler)  # asyncio: await  # noqa
                        self._request_done(response, crawler)  # asyncio: await  # noqa
                    x()  # asyncio: ensure_future(REPLACE)
                else:
                    self.on_parse_result(crawler, result, response)  # asyncio: ensure_future(REPLACE)  # noqa

            result.add_done_callback(_)

        else:
            self.on_parse_result(crawler, result, response)  # asyncio: await

    def process_requests(self, requests, crawler):  # asyncio: async

        # process requests by middlewares
        for request in self._req_middlewares(requests, crawler):  # asyncio: async  # noqa

            if isinstance(request, BaseCrawlException):
                self._resp_middlewares(request, crawler)  # asyncio: await
                continue

            # execute requests by downloader
            try:
                response = self.downloader.process(crawler, request)  # asyncio: _wrap_to_future(REPLACE)  # noqa
            except Exception as e:
                log.exception("On downloader process")
                self._exception_middlewares(  # asyncio: await
                    BaseCrawlException(
                        request=request,
                        response=None,
                        exception=e,
                        exc_info=sys.exc_info(),
                    ),
                    crawler,
                )
                self._request_done(None, crawler)  # asyncio: await
                continue

            if isinstance(response, (BaseResponse, BaseCrawlException)):
                # process response by crawler
                self.response_callback(  # asyncio: await
                    crawler,
                    # pass response to middlewares
                    self._resp_middlewares(response, crawler)  # asyncio: await  # noqa
                )
            else:  # async behaviour
                def _(r):
                    def x():  # asyncio: async
                        response = self._resp_middlewares(r.result(), crawler)  # asyncio: await  # noqa
                        self.response_callback(crawler, response)  # asyncio: ensure_future(REPLACE) # noqa
                    x()  # asyncio: ensure_future(REPLACE)
                response.add_done_callback(_)

    def prepare(self, crawler):  # asyncio: async
        # prepare middleware chain
        self.request_middlewares = self.middlewares
        self.response_middlewares = self.middlewares[:]
        self.response_middlewares.reverse()

        log.info('Prepare downloader: %s', self.downloader)
        self.downloader.start(crawler)  # asyncio: await _co(REPLACE)
        self.in_progress = 0

        log.info('Start crawler: %s', crawler)

        for pipe in self.pipelines:
            log.info('Start pipe: %s', pipe)
            try:
                pipe.start(crawler)  # asyncio: await _co(REPLACE)
            except Exception as e:
                log.exception("On pipe start")
                self._exception_middlewares(  # asyncio: await
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

    def finish(self, crawler):  # asyncio: async
        try:
            self.downloader.stop(crawler)  # asyncio: await _co(REPLACE)
        except Exception as e:
            log.exception("On downloader stop")
            self._exception_middlewares(  # asyncio: await
                BaseCrawlException(
                    request=None,
                    response=None,
                    exception=e,
                    exc_info=sys.exc_info(),
                ),
                crawler,
            )
        for pipe in self.pipelines:
            log.info('Stop pipe: %s', pipe)
            try:
                pipe.stop(crawler)  # asyncio: await _co(REPLACE)
            except Exception as e:
                log.exception("On pipe stop")
                self._exception_middlewares(  # asyncio: await
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
                iterator(next_requests), None,
            )

        while True:

            if self.queue_lock and self.queue_semaphore_value <= 0:
                self.queue_lock.acquire(True)

            next_requests = self.queue.get_requests(
                count=self.queue_semaphore_value
            )

            if isinstance(next_requests, StopCommand):
                break

            self.process_requests(
                iterator(next_requests), crawler,
            )

        self.finish(crawler)

    def get_queue_lock(self):
        workers_count = self.downloader.get_workers_count()
        if workers_count >= 1:
            self.workers_count = workers_count
            self.queue_semaphore_value = workers_count
            return self.LOCK_FACTORY()

    def _process_items(self, crawler, items, response=None):  # asyncio: async

        for item in items:

            if not item:
                continue

            # yield item as request
            if isinstance(item, BaseRequest):
                yield item
            else:
                # proccess item as data item by pipes
                for pipe in self.pipelines:
                    try:
                        item = pipe.process(crawler, item)  # asyncio: await _co(REPLACE)  # noqa
                    except Exception as e:
                        log.exception("On pipe process")
                        self._exception_middlewares(  # asyncio: await
                            BaseCrawlException(
                                request=response.get_request(),
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

    def _req_middlewares(self, requests, crawler):  # asyncio: async
        # pass requests to middlewares
        for request in requests:

            # decrement count of available requests to fetch
            if self.queue_lock:
                self.queue_semaphore_value -= 1

            for middleware in self.request_middlewares:
                try:
                    request = middleware.process_request(request, crawler, self.downloader)  # asyncio: await _co(REPLACE) # noqa
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
                    self._request_done(None, crawler)  # asyncio: await
                    break

            if request:
                yield request

    def _resp_middlewares(self, response, crawler):  # asyncio: async
        # pass response to middlewares
        is_error = isinstance(response, BaseCrawlException)
        func = 'process_response' if not is_error else 'process_exception'

        for middleware in self.response_middlewares:
            try:
                value = getattr(middleware, func)(response, crawler, self.downloader)  # asyncio: await _co(REPLACE) # noqa
            except Exception as e:
                log.exception(
                    'Exception on process %s by %s', response, middleware,
                )
                response = self._exception_middlewares(  # asyncio: await
                    BaseCrawlException(
                        request=response.get_request() if isinstance(response, BaseHttpResponse) else None,  # noqa
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
                self._request_done(response, crawler)  # asyncio: await
                break
            response = value

        return response

    def _exception_middlewares(self, exception, crawler):  # asyncio: async
        value = None
        for middleware in self.response_middlewares:
            try:
                value = middleware.process_exception(exception, crawler, self.downloader)  # asyncio: await _co(REPLACE)  # noqa
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

    def _put_requests(self, requests, response=None, crawler=None):  # asyncio: async  # noqa

        def _put(items):  # asyncio: async
            if not items:
                return
            for item in items:
                if not item:
                    continue
                self.in_progress += 1
                self.queue.put_requests(item)  # asyncio: await _co(REPLACE)

        if hasattr(requests, 'add_done_callback'):
            # "hold" engine and wait future/planned
            self.in_progress += 1

            def _(r):
                self.in_progress -= 1
                _put(r.result())  # asyncio: ensure_future(REPLACE)

            requests.add_done_callback(_)
        else:
            _put(requests)  # asyncio: await

    def _request_done(self, response, crawler):  # asyncio: async
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
            self.queue.put_requests(StopCommand())  # asyncio: await

        # response processing complete
        try:
            crawler.on_processing_done(response)  # asyncio: await _co(REPLACE)
        except Exception as e:
            log.exception("On done processing exception")
            self._exception_middlewares(  # asyncio: await
                BaseCrawlException(
                    request=response.get_request(),
                    response=response,
                    exception=e,
                    exc_info=sys.exc_info(),
                ),
                crawler,
            )
