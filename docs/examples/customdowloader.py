import requests as requestslib
from pomp.core.base import BaseDownloader, BaseCrawlException
from pomp.core.base import BaseHttpRequest, BaseHttpResponse


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

    def process(self, crawler, request):
        try:
            return ReqResponse(request, requestslib.get(request.url))
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
