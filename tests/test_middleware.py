import logging
from nose.tools import assert_equal
from pomp.core.base import BaseDownloaderMiddleware

from pomp.core.engine import Pomp

from tools import DummyDownloader, DummyCrawler


logging.basicConfig(level=logging.DEBUG)


class Crawler(DummyCrawler):
    ENTRY_REQUESTS = '/'


class RaiseOnRequestMiddleware(BaseDownloaderMiddleware):
    def process_request(self, request):
        raise Exception('Some exception on Request')


class RaiseOnResponseMiddleware(BaseDownloaderMiddleware):
    def process_response(self, response):
        raise Exception('Some exception on Response') 


class RaiseOnExceptionMiddleware(BaseDownloaderMiddleware):
    def process_exception(self, exception):
        raise Exception('Some exception on Exception processing')


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


def test_exception_on_processing_request():

    collect_middleware = CollectRequestResponseMiddleware()
    pomp = Pomp(
        downloader=DummyDownloader(middlewares=[
            RaiseOnRequestMiddleware(),
            collect_middleware,
        ]),
    )

    pomp.pump(Crawler())

    assert_equal(len(collect_middleware.exceptions), 1)
    assert_equal(len(collect_middleware.requests), 0)
    assert_equal(len(collect_middleware.responses), 0)


def test_exception_on_processing_response():

    collect_middleware = CollectRequestResponseMiddleware()
    pomp = Pomp(
        downloader=DummyDownloader(middlewares=[
            RaiseOnResponseMiddleware(),
            collect_middleware,
        ]),
    )

    pomp.pump(Crawler())

    assert_equal(len(collect_middleware.exceptions), 1)
    assert_equal(len(collect_middleware.requests), 1)
    assert_equal(len(collect_middleware.responses), 1) 


def test_exception_on_processing_exception():

    collect_middleware = CollectRequestResponseMiddleware()
    pomp = Pomp(
        downloader=DummyDownloader(middlewares=[
            RaiseOnRequestMiddleware(),
            RaiseOnExceptionMiddleware(),
            collect_middleware,
        ]),
    )

    pomp.pump(Crawler())

    assert_equal(len(collect_middleware.exceptions), 1)
    assert_equal(len(collect_middleware.requests), 0)
    assert_equal(len(collect_middleware.responses), 0)
