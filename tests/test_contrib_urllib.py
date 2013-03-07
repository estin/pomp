import logging
from nose.tools import assert_set_equal, assert_equal
from pomp.core.base import BaseCrawler, BaseDownloaderMiddleware
from pomp.core.engine import Pomp
from pomp.contrib import SimpleDownloader, ThreadedDownloader

from mockserver import HttpServer, make_sitemap
from tools import DummyCrawler
from tools import RequestResponseMiddleware, CollectRequestResponseMiddleware


logging.basicConfig(level=logging.DEBUG)


class TestContribUrllib(object):

    @classmethod
    def setupClass(cls):
        cls.httpd = HttpServer(sitemap=make_sitemap(level=2, links_on_page=2))
        cls.httpd.start()

    @classmethod
    def teardownClass(cls):
        cls.httpd.stop()

    def test_thread_pooled_downloader(self):
        req_resp_midlleware = RequestResponseMiddleware(
            prefix_url=self.httpd.location,
            request_factory=lambda x: x,
        )

        collect_middleware = CollectRequestResponseMiddleware()

        downloader = ThreadedDownloader(
            middlewares=[collect_middleware]
        )

        downloader.middlewares.insert(0, req_resp_midlleware)

        pomp = Pomp(
            downloader=downloader,
            pipelines=[],
        )

        DummyCrawler.ENTRY_URL = '/root'
        pomp.pump(DummyCrawler())

        assert_set_equal(
            set([r.url.replace(self.httpd.location, '') \
                for r in collect_middleware.requests]),
            set(self.httpd.sitemap.keys())
        )


    def test_exception_handling(self):

        class CatchException(BaseDownloaderMiddleware):

            def __init__(self):
                self.exceptions = []

            def process_exception(self, exception):
                self.exceptions.append(exception)
                return exception

        class MockCrawler(BaseCrawler):
            def next_url(self, response):
                return

            def extract_items(self, response):
                return

        catch_exception_middleware = CatchException()
        pomp = Pomp(
            downloader=SimpleDownloader(middlewares=[catch_exception_middleware]),
            pipelines=[],
        )

        MockCrawler.ENTRY_URL = [
            'https://123.456.789.01:8081/fake_url',
            '%s/root' % self.httpd.location,
        ]

        pomp.pump(MockCrawler())

        assert_equal(len(catch_exception_middleware.exceptions), 1)
