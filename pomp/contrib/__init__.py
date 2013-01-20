"""
Standart downloaders
"""
try:
    from urllib.request import urlopen, Request
except ImportError:
    from urllib2 import urlopen, Request


import logging
from multiprocessing.pool import ThreadPool
from pomp.core.base import BaseDownloader, BaseHttpRequest, \
    BaseHttpResponse, BaseDownloaderMiddleware, BaseDownloadException
from pomp.core.utils import iterator


log = logging.getLogger('pomp.contrib.urllib')


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
        try:
            res = urlopen(request.url, timeout=timeout)
            return UrllibHttpResponse(request, res)
        except Exception as e:
            log.exception('Exception on %s', request)
            return BaseDownloadException(request, exception=e)


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

    def __init__(self, request, response):
        self.req = request
        self.resp = response

        if not isinstance(response, Exception):
            self.body = self.resp.read()

    @property
    def request(self):
        return self.req

    @property
    def response(self):
        return self.response 


class UrllibAdapterMiddleware(BaseDownloaderMiddleware):

    def process_request(self, req):
        if isinstance(req, BaseHttpRequest):
            return req
        return UrllibHttpRequest(url=req)

    def process_response(self, response):
        return response
