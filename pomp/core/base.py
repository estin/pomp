"""
Base classes
"""
CRAWL_DEPTH_FIRST_METHOD = 'depth'
CRAWL_WIDTH_FIRST_METHOD = 'width'

class BaseCrawler(object):
    ENTRY_URL = None
    CRAWL_METHOD = CRAWL_DEPTH_FIRST_METHOD

    def next_url(self, page):
        raise NotImplementedError()

    def process(self, response):
        return self.extract_items(response)

    def extract_items(self, url, page):
        raise NotImplementedError()

    @property
    def is_depth_first(self):
        return self.CRAWL_METHOD == CRAWL_DEPTH_FIRST_METHOD


class BaseDownloader(object):

    def __init__(self, middlewares=None):
        self.middlewares = middlewares or ()

    def process(self, urls, callback, crawler):
        # start downloading and processing
        return list(self._lazy_process(urls, callback, crawler))

    def _lazy_process(self, urls, callback, crawler):

        if not urls:
            return

        requests = []
        for request in urls:

            for middleware in self.middlewares:
                request = middleware.process_request(request)
                if not request:
                    break

            if not request:
                continue

            requests.append(request)

        if not requests:
            return

        for response in self.get(requests):

            for middleware in self.middlewares:
                response = middleware.process_response(response)
                if not response:
                    break

            if response:
                yield callback(crawler, response)

    def get(self, url):
        raise NotImplementedError()


class BasePipeline(object):

    def start(self):
        pass

    def process(self, item):
        raise NotImplementedError()

    def stop(self):
        pass


class BaseDownloaderMiddleware(object):

    def porcess_request(self, request):
        raise NotImplementedError()
 
    def porcess_response(self, response):
        raise NotImplementedError() 


class BaseHttpRequest(object):

    def __init__(self, *args, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class BaseHttpResponse(object):
 
    def __init__(self, *args, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
