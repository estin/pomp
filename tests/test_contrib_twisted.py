import json
import logging
from nose import SkipTest
from nose.tools import assert_set_equal

try:
    from nose.twistedtools import reactor, stop_reactor, deferred
    from twisted.internet import defer
except ImportError:
    raise SkipTest('twisted not installed')

from pomp.core.base import BaseCrawler, BaseDownloaderMiddleware, BasePipeline
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
        self.requested_urls = []
        self.prefix_url = prefix_url
    
    def process_request(self, url):
        self.requested_urls.append(url)
        url = '%s%s' % (self.prefix_url, url) \
            if self.prefix_url else url
        return TwistedHttpRequest(url)
    
    def process_response(self, response):
        response.body = json.loads(response.body.decode('utf-8'))
        return response


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

        req_resp_midlleware = RequestResponseMiddleware(prefix_url=self.httpd.location)
        downloader = TwistedDownloader(reactor)

        downloader.middlewares.insert(0, req_resp_midlleware)

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
                set(req_resp_midlleware.requested_urls),
                set(self.httpd.sitemap.keys())
            )

        done_defer.addCallback(check)
        return done_defer
