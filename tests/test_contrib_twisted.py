import logging
from nose import SkipTest
from nose.tools import assert_set_equal

try:
    from nose.twistedtools import reactor, stop_reactor, deferred
    from twisted.internet import defer
except ImportError:
    raise SkipTest('twisted not installed')

import defer as dfr

from pomp.core.base import BaseDownloadException, BaseQueue
from pomp.core.engine import Pomp
from pomp.contrib.twistedtools import TwistedDownloader, TwistedHttpRequest

from tools import DummyCrawler, RequestResponseMiddleware, \
    CollectRequestResponseMiddleware, PrintPipeline
from mockserver import HttpServer, make_sitemap


logging.basicConfig(level=logging.DEBUG)

log = logging.getLogger(__name__)


class TestContribTiwsted(object):

    @classmethod
    def setupClass(cls):
        cls.httpd = HttpServer(sitemap=make_sitemap(level=2, links_on_page=2))
        cls.httpd.start()

    @classmethod
    def teardownClass(cls):
        stop_reactor()
        cls.httpd.stop()

    def do_simple_test(self, queue=None):
        req_resp_middleware = RequestResponseMiddleware(
            prefix_url=self.httpd.location,
            request_factory=TwistedHttpRequest,
        )
        collect_middleware = CollectRequestResponseMiddleware()
        downloader = TwistedDownloader(
            reactor, middlewares=[collect_middleware])

        downloader.middlewares.insert(0, req_resp_middleware)

        pomp = Pomp(
            downloader=downloader,
            pipelines=[PrintPipeline()],
            queue=queue,
        )

        class Crawler(DummyCrawler):
            ENTRY_REQUESTS = '/root'

        done_defer = defer.Deferred()
        d = pomp.pump(Crawler())

        d.add_callback(done_defer.callback)

        def check(x):
            assert_set_equal(
                set([r.url.replace(self.httpd.location, '')
                    for r in collect_middleware.requests]),
                set(self.httpd.sitemap.keys())
            )

        done_defer.addCallback(check)
        return done_defer

    @deferred(timeout=1.0)
    def test_downloader(self):
        return self.do_simple_test()

    @deferred(timeout=1.0)
    def test_exceptions(self):

        req_resp_middleware = RequestResponseMiddleware(
            prefix_url='invalid url',
            request_factory=TwistedHttpRequest,
        )
        collect_middleware = CollectRequestResponseMiddleware()

        downloader = TwistedDownloader(
            reactor, middlewares=[collect_middleware])

        downloader.middlewares.insert(0, req_resp_middleware)

        pomp = Pomp(
            downloader=downloader,
            pipelines=[PrintPipeline()],
        )

        class Crawler(DummyCrawler):
            ENTRY_REQUESTS = '/root'

        done_defer = defer.Deferred()
        d = pomp.pump(Crawler())

        d.add_callback(done_defer.callback)

        def check(x):
            assert len(collect_middleware.exceptions) == 1
            assert isinstance(
                collect_middleware.exceptions[0], BaseDownloadException)

        done_defer.addCallback(check)
        return done_defer

    @deferred(timeout=1.0)
    def test_timeout(self):

        req_resp_midlleware = RequestResponseMiddleware(
            prefix_url=self.httpd.location,
            request_factory=TwistedHttpRequest,
        )
        collect_middleware = CollectRequestResponseMiddleware()

        downloader = TwistedDownloader(
            reactor,
            timeout=0.5,
            middlewares=[collect_middleware]
        )

        downloader.middlewares.insert(0, req_resp_midlleware)

        pomp = Pomp(
            downloader=downloader,
            pipelines=[PrintPipeline()],
        )

        class Crawler(DummyCrawler):
            ENTRY_REQUESTS = '/sleep'

        done_defer = defer.Deferred()
        d = pomp.pump(Crawler())

        d.add_callback(done_defer.callback)

        def check(x):
            assert len(collect_middleware.exceptions) == 1
            e = collect_middleware.exceptions[0]
            assert isinstance(e, BaseDownloadException)

            # twisted _newcleint can raise ResponseNeverReceived
            # next assert works only for `oldclient`
            # assert isinstance(e.exception, defer.CancelledError)

        done_defer.addCallback(check)
        return done_defer

    @deferred(timeout=1.0)
    def test_deferred_queue(self):

        class DeferredQueue(BaseQueue):

            def __init__(self):
                self.requests = []

            def get_requests(self):
                d = dfr.Deferred()

                def fire(f):
                    log.debug(
                        "Fire on queue:%s len: %s",
                        f,
                        len(self.requests),
                    )
                    try:
                        f.callback(self.requests.pop())
                    except IndexError:
                        log.debug("Queue empty")
                        f.callback(None)  # empty queue

                reactor.callLater(0.01, fire, d)
                return d

            def put_requests(self, request):
                log.debug("Put to queue:%s", request)
                self.requests.append(request)

        return self.do_simple_test(queue=DeferredQueue())
