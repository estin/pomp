import json
import logging
from nose.tools import assert_set_equal
from pomp.core.base import BaseCrawler, BaseDownloaderMiddleware
from pomp.core.engine import Pomp
from pomp.contrib import ThreadedDownloader, UrllibHttpRequest
from pomp.core.base import CRAWL_WIDTH_FIRST_METHOD

from mockserver import HttpServer, make_sitemap

logging.basicConfig(level=logging.DEBUG)


class DummyCrawler(BaseCrawler):
    ENTRY_URL = None
    CRAWL_METHOD = CRAWL_WIDTH_FIRST_METHOD

    def __init__(self):
        super(DummyCrawler, self).__init__()

    def next_url(self, response):
        return response.body.get('links', [])

    def extract_items(self, response):
        return


class RequestResponseMiddleware(BaseDownloaderMiddleware):

    def __init__(self, prefix_url=None):
        self.requested_urls = []
        self.prefix_url = prefix_url
    
    def process_request(self, url):
        self.requested_urls.append(url)
        url = '%s%s' % (self.prefix_url, url) \
            if self.prefix_url else url
        return url
    
    def process_response(self, response):
        response.body = json.loads(response.body.decode('utf-8'))
        return response


class TestThreadedCrawler(object):

    @classmethod
    def setupClass(cls):
        cls.httpd = HttpServer(sitemap=make_sitemap(level=2, links_on_page=2))
        cls.httpd.start()

    @classmethod
    def teardownClass(cls):
        cls.httpd.stop()

    def test_thread_pooled_downloader(self):
        req_resp_midlleware = RequestResponseMiddleware(prefix_url=self.httpd.location)

        downloader = ThreadedDownloader()

        downloader.middlewares.insert(0, req_resp_midlleware)

        pomp = Pomp(
            downloader=downloader,
            pipelines=[],
        )

        DummyCrawler.ENTRY_URL = '/root'
        pomp.pump(DummyCrawler())

        assert_set_equal(
            set(req_resp_midlleware.requested_urls),
            set(self.httpd.sitemap.keys())
        )
