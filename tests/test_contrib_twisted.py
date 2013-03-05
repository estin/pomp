import json
import logging
from nose import SkipTest
from nose.tools import assert_set_equal

try:
    from nose.twistedtools import reactor, stop_reactor, deferred
    from twisted.internet import defer
except ImportError:
    raise SkipTest('twisted not installed')

from pomp.core.base import BaseCrawler, BaseDownloaderMiddleware, \
    BasePipeline, BaseDownloadException
from pomp.core.engine import Pomp
from pomp.contrib.twistedtools import TwistedDownloader, TwistedHttpRequest
from pomp.core.base import CRAWL_WIDTH_FIRST_METHOD
from pomp.core.item import Item, Field

from mockserver import HttpServer, make_sitemap

logging.basicConfig(level=logging.DEBUG)


class DummyItem(Item):
    value = Field()
    url = Field()

    def __repr__(self):
        return '<DummyItem(%s, %s)>' % (self.url, self.value)


class DummyCrawler(BaseCrawler):
    ENTRY_URL = None
    CRAWL_METHOD = CRAWL_WIDTH_FIRST_METHOD

    def __init__(self):
        super(DummyCrawler, self).__init__()

    def next_url(self, response):
        res = response.body.get('links', [])
        return res

    def extract_items(self, response):
        item = DummyItem()
        item.value = 1
        item.url = response.request.url
        yield item 


class RequestResponseMiddleware(BaseDownloaderMiddleware):

    def __init__(self, prefix_url=None):
        self.prefix_url = prefix_url
    
    def process_request(self, url):
        url = '%s%s' % (self.prefix_url, url) \
            if self.prefix_url else url
        return TwistedHttpRequest(url)
    
    def process_response(self, response):
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


class TestContribTiwsted(object):

    @classmethod
    def setupClass(cls):
        cls.httpd = HttpServer(sitemap=make_sitemap(level=2, links_on_page=2))
        cls.httpd.start()

    @classmethod
    def teardownClass(cls):
        stop_reactor()
        cls.httpd.stop()

    @deferred(timeout=1.0)
    def test_downloader(self):

        req_resp_middleware = RequestResponseMiddleware(prefix_url=self.httpd.location)
        collect_middleware = CollectRequestResponseMiddleware()
        downloader = TwistedDownloader(reactor, middlewares=[collect_middleware])

        downloader.middlewares.insert(0, req_resp_middleware)

        pomp = Pomp(
            downloader=downloader,
            pipelines=[PrintPipeline()],
        )

        DummyCrawler.ENTRY_URL = '/root'

        done_defer = defer.Deferred()
        d = pomp.pump(DummyCrawler())

        d.add_callback(done_defer.callback)

        def check(x):
            assert_set_equal(
                set([r.url.replace(self.httpd.location, '') \
                    for r in  collect_middleware.requests]),
                set(self.httpd.sitemap.keys())
            )

        done_defer.addCallback(check)
        return done_defer

    @deferred(timeout=1.0)
    def test_exceptions(self):

        req_resp_midlleware = RequestResponseMiddleware(prefix_url='ivalid url')
        collect_middleware = CollectRequestResponseMiddleware()

        downloader = TwistedDownloader(reactor, middlewares=[collect_middleware])

        downloader.middlewares.insert(0, req_resp_midlleware)

        pomp = Pomp(
            downloader=downloader,
            pipelines=[PrintPipeline()],
        )

        DummyCrawler.ENTRY_URL = '/root'

        done_defer = defer.Deferred()
        d = pomp.pump(DummyCrawler())

        d.add_callback(done_defer.callback)
        #d.add_callback(done_defer.callback)

        def check(x):
            assert len(collect_middleware.exceptions) == 1
            assert isinstance(collect_middleware.exceptions[0], 
                BaseDownloadException)

        done_defer.addCallback(check)
        return done_defer 


    @deferred(timeout=1.0)
    def test_timeout(self):

        req_resp_midlleware = RequestResponseMiddleware(prefix_url=self.httpd.location)
        collect_middleware = CollectRequestResponseMiddleware()

        downloader = TwistedDownloader(reactor,
            timeout=0.5,
            middlewares=[collect_middleware]
        )

        downloader.middlewares.insert(0, req_resp_midlleware)

        pomp = Pomp(
            downloader=downloader,
            pipelines=[PrintPipeline()],
        )

        DummyCrawler.ENTRY_URL = '/sleep'

        done_defer = defer.Deferred()
        d = pomp.pump(DummyCrawler())

        d.add_callback(done_defer.callback)

        def check(x):
            assert len(collect_middleware.exceptions) == 1
            e = collect_middleware.exceptions[0]
            assert isinstance(e, BaseDownloadException)
            assert isinstance(e.exception, defer.CancelledError)

        done_defer.addCallback(check)
        return done_defer
