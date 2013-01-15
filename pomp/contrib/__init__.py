"""
Standart downloaders
"""
try:
    from urllib.request import urlopen
except ImportError:
    from urllib2 import urlopen

from multiprocessing.pool import ThreadPool
from pomp.core.base import BaseDownloader, BaseHttpRequest, \
    BaseHttpResponse, BaseDownloaderMiddleware
from pomp.core.utils import iterator


class SimpleDownloader(BaseDownloader):

    TIMEOUT = 5

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
    pass


class UrllibHttpResponse(BaseHttpResponse):

    def __init__(self, request, urlopen_res):
        self.urlopen_res = urlopen_res
        self.request = request
        self.body = self.urlopen_res.read()


class UrllibAdapterMiddleware(BaseDownloaderMiddleware):

    def process_request(self, req):
        if isinstance(req, BaseHttpRequest):
            return req
        return UrllibHttpRequest(url=req)

    def process_response(self, response):
        return response
