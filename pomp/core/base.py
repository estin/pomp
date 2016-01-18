"""
Base classes

 .. note::

    All classes in this package must be subclassed.
"""
import sys
import logging

from pomp.core.utils import Planned


log = logging.getLogger('pomp.contrib.core')


class BaseCommand(object):  # pragma: no cover
    pass


class BaseCrawler(object):  # pragma: no cover
    """Crawler interface

    The crawler must implement two tasks:

    - Extract data from response
    - Extract urls from response for follow-up processing

    Each crawler must have one or more url starting points.
    To set the entry urls, declare them as class attribute ``ENTRY_REQUESTS``::

        class MyGoogleCrawler(BaseCrawler):
            ENTRY_REQUESTS = 'http://google.com/'
            ...

    ``ENTRY_REQUESTS`` may be a list of urls or list of requests
    (instances of :class:`BaseHttpRequest`).
    """
    ENTRY_REQUESTS = None

    def next_requests(self, response):  # pragma: no cover
        """Returns follow-up requests for processing.

        Called after the `extract_items` method.

        :note:
            Subclass may not implement this method.
            Next requests may be returened with items in `extrat_items` method.

        :param response: the instance of :class:`BaseHttpResponse`
        :rtype: ``None`` or request or requests (instance of
            :class:`BaseHttpRequest` or str). ``None`` response indicates that
            that this page does not any urls for follow-up processing.
        """
        pass

    def process(self, response):
        return self.extract_items(response)

    def extract_items(self, response):
        """Parse page and extract items.

        :param response: the instance of :class:`BaseHttpResponse`
        :rtype: item/items of any type
            or type of :class:`pomp.contrib.item.Item`
            or request/requests type of :class:`BaseHttpRequest`
            or string/strings for following processing as requests
        """
        raise NotImplementedError()


class BaseQueue(object):  # pragma: no cover
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


class BaseDownloadWorker(object):  # pragma: no cover
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

    The downloader must implement one task:

    - make http request and fetch response.

    :param middlewares: list of middlewares, instances
                        of :class:`BaseDownloaderMiddleware`
    """

    def __init__(self, middlewares=None):
        self.middlewares = middlewares or []

        if isinstance(self.middlewares, tuple):
            self.middlewares = list(self.middlewares)

    def prepare(self):
        """Prepare downloader before processing starts."""
        self.request_middlewares = self.middlewares
        self.response_middlewares = self.middlewares[:]
        self.response_middlewares.reverse()

    def process(self, to_process, crawler):
        if not to_process:  # pragma: no cover
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

    def get(self, requests):  # pragma: no cover
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

    def stop(self):
        pass

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
            if not value:  # stop processing exception  # pragma: no cover
                break
        return value


class BasePipeline(object):  # pragma: no cover
    """Pipeline interface

    The function of pipes are to:

    - filter items
    - change items
    - store items
    """

    def start(self, crawler):
        """Initialize pipe

        Open files and database connections, etc.

        :param crawler: crawler that extracts items
        """
        pass

    def process(self, crawler, item):
        """Process extracted item

        :param crawler: crawler that extracts items
        :param item: extracted item
        :rtype: item or ``None`` if this item is to be skipped
        """
        raise NotImplementedError()

    def stop(self, crawler):
        """Finalize pipe

        Close files and database connections, etc.

        :param crawler: crawler that extracts items
        """
        pass


class BaseDownloaderMiddleware(object):
    """Downloader middleware interface"""

    def process_request(self, request):
        """Change request before it will be executed by downloader

        :param request: instance of :class:`BaseHttpRequest`
        :rtype: changed request or ``None`` to skip execution of this request
        """
        return request

    def process_response(self, response):
        """Modify response before content is extracted by the crawler.

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


class BaseRequest(object):  # pragma: no cover
    """Request interface"""
    pass


class BaseResponse(object):  # pragma: no cover
    """Response interface"""
    pass


class BaseHttpRequest(BaseRequest):  # pragma: no cover
    """HTTP request interface"""
    pass


class BaseHttpResponse(BaseResponse):  # pragma: no cover
    """HTTP response interface"""

    @property
    def request(self):
        """Request :class:`BaseHttpRequest`"""
        raise NotImplementedError()


class BaseDownloadException(Exception):  # pragma: no cover
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


class BaseEngine(object):  # pragma: no cover

    def pump(self, crawler):
        raise NotImplementedError()
