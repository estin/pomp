"""
Base classes

 .. note::

    All this class must be subclassed
"""
import sys
import logging

from pomp.core.utils import Planned


log = logging.getLogger('pomp.contrib.core')


class BaseCommand(object):
    pass


class BaseCrawler(object):
    """Crawler interface

    Crawler must resolve two main tasks:

    - Extract data from response
    - Extract next urls for following processing from response

    Each crawler must have starting point - entry url.
    To set entry url declare them as class attribute ``ENTRY_REQUESTS``
    like that::

        class MyGoogleCrawler(BaseCrawler):
            ENTRY_REQUESTS = 'http://google.com/'
            ...

    ``ENTRY_REQUESTS`` may be list of urls or list of requests
    (instances of :class:`BaseHttpRequest`).
    """
    ENTRY_REQUESTS = None

    def __init__(self):
        self._in_process = 0

    def next_requests(self, response):
        """Getting next requests for processing.

        Called after `extract_items` method.

        :note:
            Subclass can not implement thid method.
            Next requests may be returened with items in `extrat_items` method.

        :param response: the instance of :class:`BaseHttpResponse`
        :rtype: ``None`` or request or requests (instnace of
            :class:`BaseHttpRequest` or str). If ``None`` returned
            this mean that page have not any urls to following
            processing
        """
        pass

    def process(self, response):
        return self.extract_items(response)

    def extract_items(self, response):
        """Extract items and next requests - parse page.

        :param response: the instance of :class:`BaseHttpResponse`
        :rtype: item or items (isntance of :class:`pomp.core.item.Item`)
            or request or requests (instance of :class:`BaseHttpRequest`)
        """
        raise NotImplementedError()


class BaseQueue(object):
    """Blocking queue interface"""

    def get_requests(self):
        """Get from queue

        .. note::

            must block execution until item is available

        :rtype: instance of :class:`BaseRequest` or :class:`.Planned`
                or list of them
        """
        raise NotImplementedError()

    def put_requests(self, requests):
        """Put to queue

        :param requests: instance of :class:`BaseRequest` or list of them
        """
        raise NotImplementedError()


class BaseDownloadWorker(object):
    """Download worker interface"""

    def get_one(self, request):
        """Execute request

        :param request: instance of :class:`BaseHttpRequest`
        :rtype: instance of :class:`BaseHttpResponse` or
                :class:`BaseDownloadException` or :class:`.Planned`
                for async behavior
        """
        raise NotImplementedError()


class BaseDownloader(object):
    """Downloader interface

    Downloader must resolve one main task - execute request
    and fetch response.

    :param middlewares: list of middlewares, instances
                        of :class:`BaseDownloaderMiddleware`
    """

    def __init__(self, middlewares=None):
        self.middlewares = middlewares or []

        if isinstance(self.middlewares, tuple):
            self.middlewares = list(self.middlewares)

    def prepare(self):
        """Prepare downloader before start processing"""
        self.request_middlewares = self.middlewares
        self.response_middlewares = self.middlewares[:]
        self.response_middlewares.reverse()

    def process(self, to_process, crawler):
        if not to_process:
            return

        requests = []
        for request in to_process:

            for middleware in self.request_middlewares:
                try:
                    request = middleware.process_request(request)
                except Exception as e:
                    log.exception(
                        'Exception on process %s by %s', request, middleware)
                    yield self._process_exception(
                        BaseDownloadException(
                            request,
                            exception=e,
                            exc_info=sys.exc_info(),
                        )
                    )
                    request = None  # stop processing request by middlewares
                if not request:
                    break

            if not request:
                continue

            requests.append(request)

        if not requests:
            return

        for response in self.get(requests):
            if isinstance(response, Planned):  # async behavior
                future = Planned()

                def _chain(res):
                    future.set_result(self._process_resp(res.result()))

                response.add_done_callback(_chain)
                yield future
            else:  # sync behavior
                yield self._process_resp(response)

    def get(self, requests):
        """Execute requests

        :param requests: list of instances of :class:`BaseHttpRequest`
        :rtype: list of instances of :class:`BaseHttpResponse` or
                :class:`BaseDownloadException` or :class:`.Planned`
                for async behavior
        """
        raise NotImplementedError()

    def get_workers_count(self):
        """
        :rtype: count of workers (pool size), by default 0
        """
        return 0

    def _process_resp(self, response):
        is_error = isinstance(response, BaseDownloadException)
        func = 'process_response' if not is_error else 'process_exception'
        for middleware in self.response_middlewares:
            try:
                value = getattr(middleware, func)(response)
            except Exception as e:
                log.exception(
                    'Exception on process %s by %s', response, middleware)
                response = self._process_exception(
                    BaseDownloadException(
                        response,
                        exception=e,
                        exc_info=sys.exc_info(),
                    )
                )
                value = None  # stop processing response by middlewares
            if not value:
                break
            response = value
        return response

    def _process_exception(self, exception):
        for middleware in self.response_middlewares:
            try:
                value = middleware.process_exception(exception)
            except Exception:
                log.exception(
                    'Exception on prcess %s by %s', exception, middleware)
            if not value:  # stop processing exception
                break
        return value


class BasePipeline(object):
    """Pipeline interface

    The main goals of pipe is:

    - filter items
    - change items
    - store items
    """

    def start(self, crawler):
        """Initialize pipe

        Open files and database connections etc.

        :param crawler: crawler who extract items
        """
        pass

    def process(self, crawler, item):
        """Process extracted item

        :param crawler: crawler who extract items
        :param item: extracted item
        :rtype: item or ``None`` if this item must be skipped
        """
        raise NotImplementedError()

    def stop(self, crawler):
        """Finalize pipe

        Close files and database connections etc.

        :param crawler: crawler who extract items
        """
        pass


class BaseDownloaderMiddleware(object):
    """Downloader middleware interface"""

    def process_request(self, request):
        """Change request before it will be executed by downloader

        :param request: instance of :class:`BaseHttpRequest`
        :rtype: changed request or ``None`` to skip
                execution of this request
        """
        return request

    def process_response(self, response):
        """Change response before it will be sent to crawler for exctracting
        items

        :param response: instance of :class:`BaseHttpResponse`
        :rtype: changed response or ``None`` to skip
                processing of this response
        """
        return response

    def process_exception(self, exception):
        """Handle exception raised in downloading process

        :param exception: instance of :class:`BaseDownloadException`
        :rtype: changed response or ``None`` to skip
                processing of this exception
        """
        return exception


class BaseRequest(object):
    """Request interface"""
    pass


class BaseResponse(object):
    """Response interface"""
    pass


class BaseHttpRequest(BaseRequest):
    """HTTP request interface"""

    @property
    def url(self):
        """Requested URL"""
        raise NotImplementedError()


class BaseHttpResponse(BaseResponse):
    """HTTP response interface"""

    @property
    def request(self):
        """Request :class:`BaseHttpRequest`"""
        raise NotImplementedError()

    @property
    def response(self):
        """Original response object fetched in :meth:`BaseDownloader.get`"""
        raise NotImplementedError()


class BaseDownloadException(Exception):
    """Download exception interface

    :param request: request raises this exception
    :param exception: original exception
    :param exc_info: result of `sys.exc_info` call
    """

    def __init__(self, request, exception=None, exc_info=None):
        self.request = request
        self.exception = exception
        self.exc_info = exc_info

    def __str__(self):
        return 'Exception on %s - %s' % (self.request, self.exception)
