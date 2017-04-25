import json
import logging

from pomp.core.base import BaseCrawler, BaseMiddleware, BasePipeline
from pomp.core.base import BaseHttpRequest, BaseHttpResponse
from pomp.core.base import BaseDownloader
from pomp.contrib.item import Item, Field


log = logging.getLogger()


class DummyItem(Item):
    value = Field()
    url = Field()

    def __repr__(self):
        return '<DummyItem(%s, %s)>' % (self.url, self.value)


class DummyCrawler(BaseCrawler):
    ENTRY_REQUESTS = None

    def next_requests(self, response):
        for item in response.body.get('links', []):
            yield DummyRequest(item)

    def extract_items(self, response):
        item = DummyItem()
        item.value = 1
        item.url = response.get_request().url
        yield item

    def on_processing_done(self, response):
        pass


class DummyDownloader(BaseDownloader):

    def get(self, requests):
        for request in requests:
            response = DummyResponse(request, 'some html code')
            yield response


class RequestResponseMiddleware(BaseMiddleware):

    def __init__(self, request_factory, prefix_url=None, bodyjson=True):
        self.bodyjson = bodyjson
        self.prefix_url = prefix_url
        self.request_factory = request_factory

    def process_request(self, request, crawler, downloader):
        url = request.url if isinstance(request, BaseHttpRequest) else request
        url = '%s%s' % (self.prefix_url, url) \
            if self.prefix_url else url
        return self.request_factory(url)

    def process_response(self, response, crawler, downloader):
        if self.bodyjson:
            if isinstance(response.body, str):
                response.body = json.loads(response.body)
            else:
                response.body = json.loads(response.body.decode('utf-8'))
        return response


class CollectRequestResponseMiddleware(BaseMiddleware):

    def __init__(self, prefix_url=None):
        self.requests = []
        self.responses = []
        self.exceptions = []

    def process_request(self, request, crawler, downloader):
        self.requests.append(request)
        return request

    def process_response(self, response, crawler, downloader):
        self.responses.append(response)
        return response

    def process_exception(self, exception, crawler, downloader):
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

    def get_request(self):
        return self.req

    def __repr__(self):
        return '<DummyResponse on={s.req}>'.format(s=self)
