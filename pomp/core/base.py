"""
Base classes

 .. note::

    All classes in this package must be subclassed.
"""


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

    def on_processing_done(self, response):
        """Called when request/response was fully processed by middlewares,
        this crawler and and pipelines.

        :param response: the instance of :class:`BaseHttpResponse`
        """
        pass


class BaseQueue(object):  # pragma: no cover
    """Blocking queue interface"""

    def get_requests(self, count=None):
        """Get from queue

        .. note::

            must block execution until item is available

        :param count: count of requests to be processed by downloader
                      in concurrent mode, None - downloader have not
                      concurrency (workers). This param can be ignored.
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
                :class:`BaseCrawlException` or :class:`.Planned`
                for async behavior
        """
        raise NotImplementedError()


class BaseDownloader(object):
    """Downloader interface

    The downloader must implement one task:

    - make http request and fetch response.
    """

    def prepare(self):
        """Prepare downloader before processing starts."""
        pass

    def process(self, requests, crawler):
        # requests list can consists of BaseCrawlException instances
        # we must yield it without passing to downloader
        requests_as_exceptions = []

        def _filter(requests):
            for item in requests:
                if isinstance(item, BaseCrawlException):
                    requests_as_exceptions.append(item)
                else:
                    yield item

        # execute requests by downloader
        for response in self.get(_filter(requests or [])):
            yield response

        # when we yield exeption as request we do not break request-response
        # processing logic
        for exception in requests_as_exceptions:
            yield exception

    def get(self, requests):  # pragma: no cover
        """Execute requests

        :param requests: list of instances of :class:`BaseHttpRequest`
        :rtype: list of instances of :class:`BaseHttpResponse` or
                :class:`BaseCrawlException` or :class:`.Planned`
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


class BaseMiddleware(object):
    """Middleware interface"""

    def process_request(self, request, crawler, downloader):
        """Change request before it will be executed by downloader

        :param request: instance of :class:`BaseHttpRequest`
        :param crawler: instance of :class:`BaseCrawler`
        :param downloader: instance of :class:`BaseDownloader`
        :rtype: changed request or ``None`` to skip execution of this request
        """
        return request

    def process_response(self, response, crawler, downloader):
        """Modify response before content is extracted by the crawler.

        :param response: instance of :class:`BaseHttpResponse`
        :param crawler: instance of :class:`BaseCrawler`
        :param downloader: instance of :class:`BaseDownloader`
        :rtype: changed response or ``None`` to skip
                processing of this response
        """
        return response

    def process_exception(self, exception, crawler, downloader):
        """Handle exception

        :param exception: instance of :class:`BaseCrawlException`
        :param crawler: instance of :class:`BaseCrawler`
        :param downloader: instance of :class:`BaseDownloader`
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


class BaseCrawlException(Exception):  # pragma: no cover
    """Download exception interface

    :param request: request raises this exception
    :param response: response raises this exception
    :param exception: original exception
    :param exc_info: result of `sys.exc_info` call
    """

    def __init__(
            self, request=None, response=None, exception=None, exc_info=None):
        self.request = request
        self.response = response
        self.exception = exception
        self.exc_info = exc_info

    def __reduce__(self):
        return (
            BaseCrawlException,
            (),
            {
                'request': self.request,
                'response': self.response,
                'exception': self.exception,
                'exc_info': None,  # do not serialize traceback
            },
        )

    def __str__(self):
        return 'Exception on response: %s request: %s - %s' % (
            self.response, self.request, self.exception
        )


class BaseEngine(object):  # pragma: no cover

    def pump(self, crawler):
        raise NotImplementedError()
