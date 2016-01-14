import json
import logging

from pomp.core.base import BaseCrawler, BaseDownloaderMiddleware, BasePipeline
from pomp.core.base import BaseHttpRequest, BaseHttpResponse
from pomp.core.base import BaseDownloader
from pomp.core.item import Item, Field


log = logging.getLogger()


class DummyItem(Item):
    value = Field()
    url = Field()

    def __repr__(self):
        return '<DummyItem(%s, %s)>' % (self.url, self.value)


class DummyCrawler(BaseCrawler):
    ENTRY_REQUESTS = None

    def next_requests(self, response):
        res = response.body.get('links', [])
        return res

    def extract_items(self, response):
        item = DummyItem()
        item.value = 1
        item.url = response.request.url
        yield item


class DummyDownloader(BaseDownloader):

    def get(self, requests):
        for request in requests:
            response = DummyResponse(request, 'some html code')
            yield response


class RequestResponseMiddleware(BaseDownloaderMiddleware):

    def __init__(self, request_factory, prefix_url=None, bodyjson=True):
        self.bodyjson = bodyjson
        self.prefix_url = prefix_url
        self.request_factory = request_factory

    def process_request(self, request):
        url = request.url if isinstance(request, BaseHttpRequest) else request
        url = '%s%s' % (self.prefix_url, url) \
            if self.prefix_url else url
        return self.request_factory(url)

    def process_response(self, response):
        if self.bodyjson:
            if isinstance(response.body, str):
                response.body = json.loads(response.body)
            else:
                response.body = json.loads(response.body.decode('utf-8'))
        return response


class CollectRequestResponseMiddleware(BaseDownloaderMiddleware):

    def __init__(self, prefix_url=None):
        self.requests = []
        self.responses = []
        self.exceptions = []

    def process_request(self, request):
        self.requests.append(request)
        return request

    def process_response(self, response):
        self.responses.append(response)
        return response

    def process_exception(self, exception):
        self.exceptions.append(exception)
        return exception


class PrintPipeline(BasePipeline):

    def process(self, crawler, item):
        print('Pipeline:', item)


class DummyRequest(BaseHttpRequest):

    def __init__(self, url):
        self.url = url

    def __repr__(self):
        return '<DummyRequest url={s.url}>'.format(s=self)


class DummyResponse(BaseHttpResponse):

    def __init__(self, request, response):
        self.req = request
        self.resp = response

    @property
    def request(self):
        return self.req

    def __repr__(self):
        return '<DummyResponse on={s.req}>'.format(s=self)
