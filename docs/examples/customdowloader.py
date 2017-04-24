import requests as requestslib
from pomp.core.base import BaseDownloader, BaseCrawlException
from pomp.core.base import BaseHttpRequest, BaseHttpResponse

from pomp.core.utils import iterator


class ReqRequest(BaseHttpRequest):
    def __init__(self, url):
        self.url = url


class ReqResponse(BaseHttpResponse):
    def __init__(self, request, response):
        self.request = request

        if not isinstance(response, Exception):
            self.body = response.text

    def get_request(self):
        return self.request


class RequestsDownloader(BaseDownloader):

    def get(self, requests):
        for request in iterator(requests):
            yield self._fetch(request)

    def _fetch(self, request):
        try:
            response = requestslib.get(request.url)
            return ReqResponse(request, response)
        except Exception as e:
            print('Exception on %s: %s', request, e)
            return BaseCrawlException(request, exception=e)


if __name__ == '__main__':
    from pomp.core.base import BaseCrawler
    from pomp.core.engine import Pomp

    class Crawler(BaseCrawler):
        ENTRY_REQUESTS = ReqRequest('http://python.org/news/')

        def extract_items(self, response):
            print(response.body)

        def next_requests(self, response):
            return None  # one page crawler

    pomp = Pomp(
        downloader=RequestsDownloader(),
    )

    pomp.pump(Crawler())
