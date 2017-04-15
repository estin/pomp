import sys
import pickle
import logging

from pomp.core.base import BaseMiddleware, BaseCrawlException
from pomp.core.engine import Pomp

from tools import (
    DummyDownloader, DummyCrawler, DummyRequest, RequestResponseMiddleware,
)


logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


class Crawler(DummyCrawler):
    ENTRY_REQUESTS = '/'

    def next_requests(self, response):
        pass


class RaiseOnRequestMiddleware(BaseMiddleware):
    def process_request(self, request, crawler, downloader):
        raise Exception('Some exception on Request')


class RaiseOnResponseMiddleware(BaseMiddleware):
    def process_response(self, response, crawler, downloader):
        raise Exception('Some exception on Response')


class RaiseOnExceptionMiddleware(BaseMiddleware):
    def process_exception(self, exception, crawler, downloader):
        raise Exception('Some exception on Exception processing')


class RaiseOnProcessingDoneCralwer(Crawler):

    def on_processing_done(self, response):
        log.debug("call on_processing_done")
        raise Exception('Some exception on processing done callback')


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


def test_exception_on_processing_request():

    collect_middleware = CollectRequestResponseMiddleware()
    pomp = Pomp(
        downloader=DummyDownloader(),
        middlewares=(
            RaiseOnRequestMiddleware(),
            collect_middleware,
        ),
    )

    pomp.pump(Crawler())

    assert len(collect_middleware.exceptions) == 1
    assert len(collect_middleware.requests) == 0
    assert len(collect_middleware.responses) == 0


def test_exception_on_processing_response():

    collect_middleware = CollectRequestResponseMiddleware()
    pomp = Pomp(
        downloader=DummyDownloader(),
        middlewares=(
            RaiseOnResponseMiddleware(),
            collect_middleware,
        ),
    )

    pomp.pump(Crawler())

    assert len(collect_middleware.exceptions) == 1
    assert len(collect_middleware.requests) == 1
    assert len(collect_middleware.responses) == 1


def test_exception_on_processing_response_callback():

    class CrawlerWithException(Crawler):
        def extract_items(self, *args, **kwargs):
            raise Exception("some exception on extract items")

    collect_middleware = CollectRequestResponseMiddleware()
    pomp = Pomp(
        downloader=DummyDownloader(),
        middlewares=(
            collect_middleware,
        )
    )

    pomp.pump(CrawlerWithException())

    assert len(collect_middleware.exceptions) == 1
    assert len(collect_middleware.requests) == 1
    assert len(collect_middleware.responses) == 1


def test_exception_on_processing_exception():

    collect_middleware = CollectRequestResponseMiddleware()
    pomp = Pomp(
        downloader=DummyDownloader(),
        middlewares=(
            RaiseOnRequestMiddleware(),
            RaiseOnExceptionMiddleware(),
            collect_middleware,
        ),
    )

    pomp.pump(Crawler())

    # one exception on request middleware plus one on exception processing
    assert len(collect_middleware.exceptions) == 1 + 1
    assert len(collect_middleware.requests) == 0
    assert len(collect_middleware.responses) == 0


def test_exception_pickling():
    try:
        raise RuntimeError('some exception')
    except Exception as e:
        exception = BaseCrawlException(
            request=None,
            response=None,
            exception=e,
            exc_info=sys.exc_info(),
        )
        exception = pickle.loads(pickle.dumps(exception))
        assert not exception.exc_info


def test_exception_on_processing_done():

    collect_middleware = CollectRequestResponseMiddleware()
    pomp = Pomp(
        downloader=DummyDownloader(),
        middlewares=(
            RequestResponseMiddleware(
                request_factory=DummyRequest,
                bodyjson=False
            ),
            collect_middleware,
        ),
    )

    pomp.pump(RaiseOnProcessingDoneCralwer())

    # one exception on request middleware plus one on exception processing
    assert len(collect_middleware.exceptions) == 1
    assert len(collect_middleware.requests) == 1
    assert len(collect_middleware.responses) == 1
