"""
Standart downloaders
"""
try:
    from urllib.request import urlopen, Request
except ImportError:
    from urllib2 import urlopen, Request


from multiprocessing.pool import ThreadPool
from pomp.core.base import BaseDownloader, BaseHttpRequest, \
    BaseHttpResponse, BaseDownloaderMiddleware
from pomp.core.utils import iterator


class SimpleDownloader(BaseDownloader):

    TIMEOUT = 5

    def __init__(self, *args, **kwargs):
        super(SimpleDownloader, self).__init__(*args, **kwargs)
        # insert urllib adpter middleware by default
        self.middlewares.insert(0, UrllibAdapterMiddleware())

    def get(self, requests):
        responses = []
        for request in iterator(requests):
            response = self._fetch(request)
            responses.append(response)
        return responses

    def _fetch(self, request, timeout=TIMEOUT):
        res = urlopen(request.url, timeout=timeout)
        return UrllibHttpResponse(request, res)  


class ThreadedDownloader(SimpleDownloader):

    def __init__(self, pool_size=5, *args, **kwargs):
        self.workers_pool = ThreadPool(processes=pool_size)
        super(ThreadedDownloader, self).__init__(*args, **kwargs)
    
    def get(self, requests):
        return self.workers_pool.map(self._fetch, requests)


class UrllibHttpRequest(BaseHttpRequest):

    def __init__(self, url):
        self.request = url if isinstance(url, Request) else Request(url)

    @property
    def url(self):
        return self.request.get_full_url()


class UrllibHttpResponse(BaseHttpResponse):

    def __init__(self, request, urlopen_res):
        self.urlopen_res = urlopen_res
        self.req = request
        self.body = self.urlopen_res.read()

    @property
    def request(self):
        return self.req


class UrllibAdapterMiddleware(BaseDownloaderMiddleware):

    def process_request(self, req):
        if isinstance(req, BaseHttpRequest):
            return req
        return UrllibHttpRequest(url=req)

    def process_response(self, response):
        return response
