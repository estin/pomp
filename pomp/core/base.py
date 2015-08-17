"""
Base classes

 .. note::

    All this class must be subclassed
"""
import sys
import logging
import defer


CRAWL_DEPTH_FIRST_METHOD = 'depth'
CRAWL_WIDTH_FIRST_METHOD = 'width'


log = logging.getLogger('pomp.contrib.core')


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

    Crawler may choose which method for crawling to use by setting class
    attribute ``CRAWL_METHOD`` with values:

    - ``depth first`` is pomp.core.base.CRAWL_DEPTH_FIRST_METHOD (default)
    - ``width first`` is pomp.core.base.CRAWL_WIDTH_FIRST_METHOD

    :note:
        If engine used queue for requests processing
        the ```CRAWL_METHOD``` is ignored. And ```ENTRY_REQUESTS```
        not required
    """
    ENTRY_REQUESTS = None
    CRAWL_METHOD = CRAWL_DEPTH_FIRST_METHOD

    def __init__(self):
        self._in_process = 0

    def next_requests(self, response):
        """Getting next requests for processing.

        Called after `extract_items` method.

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

    def is_depth_first(self):
        return self.CRAWL_METHOD == CRAWL_DEPTH_FIRST_METHOD

    def dive(self, value=1):
        # this method called in one thread - MainThread
        # dowloader fetch request sync or async
        self._in_process += value

    def _reset_state(self):
        self._in_process = 0

    def in_process(self):
        return self._in_process != 0


class BaseQueue(object):
    """Queue interface

    request is the task
    """

    def get_requests(self):
        """Get from queue

        :rtype: instance of :class:`BaseRequest` or `defer.Deferred`
                or list of them
        """
        raise NotImplementedError()

    def put_requests(self, requests):
        """Put to queue

        :param requests: instance of :class:`BaseRequest` or list of them
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

    def process(self, to_process, callback, crawler):
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
                    request = None  # stop processing request by middlewares
                    self._process_exception(
                        BaseDownloadException(
                            request,
                            exception=e,
                            exc_info=sys.exc_info(),
                        )
                    )
                if not request:
                    break

            if not request:
                continue

            requests.append(request)

        if not requests:
            return

        def _process_resp(response):
            is_error = isinstance(response, BaseDownloadException)
            func = 'process_response' if not is_error else 'process_exception'
            for middleware in self.response_middlewares:
                try:
                    response = getattr(middleware, func)(response)
                except Exception as e:
                    log.exception(
                        'Exception on process %s by %s', response, middleware)
                    response = None  # stop processing response by middlewares
                    self._process_exception(
                        BaseDownloadException(
                            response,
                            exception=e,
                            exc_info=sys.exc_info(),
                        )
                    )
                if not response:
                    break

            if response and not is_error:
                try:
                    return callback(crawler, response)
                except Exception as e:
                    log.exception(
                        'Exception on response %s callback', response)
                    self._process_exception(
                        BaseDownloadException(
                            response,
                            exception=e,
                            exc_info=sys.exc_info(),
                        )
                    )

        crawler.dive(len(requests))  # dive in
        for response in self.get(requests):
            if isinstance(response, defer.Deferred):  # async behavior
                def _(res):
                    crawler.dive(-1)  # dive out
                    return res
                response.add_callback(_)
                response.add_callback(_process_resp)
                yield response
            else:  # sync behavior
                crawler.dive(-1)  # dive out
                yield _process_resp(response)

    def _process_exception(self, exception):
        for middleware in self.response_middlewares:
            try:
                value = middleware.process_exception(exception)
            except Exception:
                log.exception(
                    'Exception on prcess %s by %s', exception, middleware)
            if not value:  # stop processing exception
                break

    def get(self, requests):
        """Execute requests

        :param requests: urls or instances of :class:`BaseHttpRequest`
        :rtype: instances of :class:`BaseHttpResponse` or
                :class:`BaseDownloadException` or deferred for async behavior
        """
        raise NotImplementedError()


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

    def __init__(self, request, exception, exc_info=None):
        self.request = request
        self.exception = exception
        self.exc_info = exc_info

    def __str__(self):
        return 'Exception on %s - %s' % (self.request, self.exception)
