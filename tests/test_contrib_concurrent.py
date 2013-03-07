import logging
from nose import SkipTest
from nose.tools import assert_set_equal

from pomp.core.engine import Pomp
from pomp.contrib import UrllibHttpRequest

try:
    from pomp.contrib.concurrenttools import ConcurrentUrllibDownloader
except ImportError:
    raise SkipTest('concurrent future not available') 

from tools import DummyCrawler
from tools import RequestResponseMiddleware, CollectRequestResponseMiddleware
from mockserver import HttpServer, make_sitemap

logging.basicConfig(level=logging.DEBUG)


class TestContribConcurrent(object):

    @classmethod
    def setupClass(cls):
        cls.httpd = HttpServer(sitemap=make_sitemap(level=2, links_on_page=2))
        cls.httpd.start()

    @classmethod
    def teardownClass(cls):
        cls.httpd.stop()

    def test_concurrent_urllib_downloader(self):
        req_resp_midlleware = RequestResponseMiddleware(
            prefix_url=self.httpd.location,
            request_factory=UrllibHttpRequest,
        )

        collect_middleware = CollectRequestResponseMiddleware()

        downloader = ConcurrentUrllibDownloader(
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
