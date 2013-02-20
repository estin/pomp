"""
Base class

 .. note::

    All this class must be overridden
"""
CRAWL_DEPTH_FIRST_METHOD = 'depth'
CRAWL_WIDTH_FIRST_METHOD = 'width'


class BaseCrawler(object):
    """Crawler interface

    Crawler must resolve two main tasks:

    - Extract data from response
    - Extract next urls for following processing from response

    Each crawler must have starting point - entry url.
    To set entry url declare them as class attribute ``ENTRY_URL`` like that::

        class MyGoogleCrawler(BaseCrawler):
            ENTRY_URL = 'http://google.com/'
            ...

    ``ENTRY_URL`` may be list of urls or list of requests
    (instances of :class:`BaseHttpRequest`).

    Crawler may choose which method for crawling to use by setting class 
    attribute ``CRAWL_METHOD`` with values:

    - ``depth first`` is pomp.core.base.CRAWL_DEPTH_FIRST_METHOD (default)
    - ``width first`` is pomp.core.base.CRAWL_WIDTH_FIRST_METHOD
    """
    ENTRY_URL = None
    CRAWL_METHOD = CRAWL_DEPTH_FIRST_METHOD

    def next_url(self, page):
        """Getting next urls for processing.
 
        :param page: the instance of :class:`BaseHttpResponse`
        :rtype: ``None`` or one url or list of urls. If ``None`` returned
                this mean that page have not any urls to following
                processing
        """
        raise NotImplementedError()

    def process(self, response):
        return self.extract_items(response)

    def extract_items(self, url, page):
        """Extract items - parse page.

        :param url: the url of downloaded page
        :param page: the instance of :class:`BaseHttpResponse`
        :rtype: one data item or list of items
        """    
        raise NotImplementedError()

    @property
    def is_depth_first(self):
        return self.CRAWL_METHOD == CRAWL_DEPTH_FIRST_METHOD


class BaseDownloader(object):
    """Downloader interface
     
    Downloader must resolve one main task - execute request 
    and fetch response.

    :param middlewares: list of middlewares, instances
                        of :class:`BaseDownloaderMiddleware`
    """

    def __init__(self, middlewares=None):
        self.middlewares = middlewares or []

    def prepare(self):
        """Prepare downloader before start processing"""
        self.request_middlewares = self.middlewares
        self.response_middlewares = self.middlewares[:]
        self.response_middlewares.reverse()

    def process(self, urls, callback, crawler):
        # start downloading and processing
        return list(self._lazy_process(urls, callback, crawler))

    def _lazy_process(self, urls, callback, crawler):

        if not urls:
            return

        requests = []
        for request in urls:

            for middleware in self.request_middlewares:
                request = middleware.process_request(request)
                if not request:
                    break

            if not request:
                continue

            requests.append(request)

        if not requests:
            return

        for response in self.get(requests):

            for middleware in self.response_middlewares:
                response = middleware.process_response(response)
                if not response:
                    break

            if response:
                yield callback(crawler, response)

    def get(self, requests):
        """Execute requests

        :param requests: urls or instances of :class:`BaseHttpRequest`
        :rtype: instances of :class:`BaseHttpResponse` or 
                :class:`BaseDownloadException`
        """
        raise NotImplementedError()


class BasePipeline(object):
    """Pipeline interface

    The main goals of pipe is:

    - filter items
    - change items
    - store items
    """ 

    def start(self):
        """Initialize pipe

        Open files and database connections etc.
        
        """
        pass

    def process(self, crawler, item):
        """Process extracted item

        :param crawler: crawler who extract items
        :param item: extracted item
        :rtype: item or ``None`` if this item must be skipped
        """
        raise NotImplementedError()

    def stop(self):
        """Finalize pipe
        
        Close files and database connections etc.
        """
        pass


class BaseDownloaderMiddleware(object):
    """Downloader middleware interface"""

    def porcess_request(self, request):
        """Change request before it will be executed by downloader

        :param request: instance of :class:`BaseHttpRequest`
        :rtype: changed request or ``None`` to skip
                execution of this request
        """
        raise NotImplementedError()
 
    def porcess_response(self, response):
        """Change response before it will be sent to crawler for exctracting
        items

        :param response: instance of :class:`BaseHttpResponse`
                         or :class:`BaseDownloadException`
        :rtype: changed response or ``None`` to skip
                processing of this response
        """ 
        raise NotImplementedError() 


class BaseHttpRequest(object):
    """Request interface"""

    @property
    def url(self):
        """Requested URL"""
        raise NotImplementedError()


class BaseHttpResponse(object):
    """Response interface"""

    @property
    def request(self):
        """Request :class:`BaseHttpRequest`"""
        raise NotImplementedError()

    @property
    def response(self):
        """Response :class:`BaseHttpResponse`"""
        raise NotImplementedError()


class BaseDownloadException(Exception):
    """Download exception interface
    
    :param request: request raises this exception
    :param exception: original exception
    """

    def __init__(self, request, exception):
        self.request = request
        self.execption = exception

    def __str__(self):
        return 'Exception on %s - %s' % (self.request, self.execption)
