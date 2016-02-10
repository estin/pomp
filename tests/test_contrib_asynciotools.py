from nose.plugins.skip import SkipTest

try:
    import asyncio
    import aiohttp
except ImportError:
    raise SkipTest('asyncio or aiohttp not available')

import logging
from nose.tools import assert_set_equal
from pomp.core.base import (
    BaseHttpRequest, BaseHttpResponse, BaseDownloader, BaseMiddleware,
)
from pomp.contrib.asynciotools import (
    ensure_future, AioPomp, AioConcurrentCrawler,
)
from pomp.core.utils import Planned


from mockserver import HttpServer, make_sitemap
from tools import DummyCrawler
from tools import RequestResponseMiddleware, CollectRequestResponseMiddleware


logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


class AiohttpRequest(BaseHttpRequest):
    def __init__(self, url):
        self.url = url

    def __str__(self):
        return '<AiohttpRequest url:{s.url}>'.format(s=self)


class AiohttpResponse(BaseHttpResponse):
    def __init__(self, request, body):
        self.req = request
        self.body = body

    @property
    def request(self):
        return self.req


class AiohttpAdapterMiddleware(BaseMiddleware):
    def process_request(self, req, crawler, downloader):
        log.debug(
            "AiohttpAdapterMiddleware %s %s",
            req, isinstance(req, BaseHttpRequest),
        )
        if isinstance(req, BaseHttpRequest):
            return req
        return AiohttpRequest(req)

    def process_response(self, response, crawler, downloader):
        return response


class AiohttpDownloader(BaseDownloader):
    @asyncio.coroutine
    def _fetch(self, request, future):
        log.debug("[AiohttpDownloader] Start fetch: %s", request.url)
        r = yield from aiohttp.get(request.url)
        body = yield from r.text()
        log.debug(
            "[AiohttpDownloader] Done %s: %s %s",
            request.url, len(body), body[0:20],
        )
        future.set_result(AiohttpResponse(request, body))

    def get_workers_count(self):
        return 2

    def get(self, requests):
        for request in requests:

            future = asyncio.Future()
            ensure_future(self._fetch(request, future))

            planned = Planned()

            def build_response(f):
                planned.set_result(f.result())
            future.add_done_callback(build_response)

            yield planned


class Crawler(DummyCrawler):
    ENTRY_REQUESTS = '/root'


class TestContribAsyncio(object):
    @classmethod
    def setupClass(cls):
        cls.httpd = HttpServer(sitemap=make_sitemap(level=2, links_on_page=2))
        cls.httpd.start()

    @classmethod
    def teardownClass(cls):
        cls.httpd.stop()
        asyncio.get_event_loop().close()

    def setup(self):
        self.req_resp_midlleware = RequestResponseMiddleware(
            prefix_url=self.httpd.location,
            request_factory=lambda x: x,
        )

        self.collect_middleware = CollectRequestResponseMiddleware()

        self.downloader = AiohttpDownloader()

        self.middlewares = (
            self.req_resp_midlleware,
            AiohttpAdapterMiddleware(),
            self.collect_middleware,
        )

    def test_asyncio_engine(self):
        pomp = AioPomp(
            downloader=self.downloader,
            middlewares=self.middlewares,
            pipelines=[],
        )

        loop = asyncio.get_event_loop()
        loop.run_until_complete(pomp.pump(Crawler()))

        assert_set_equal(
            set([r.url.replace(self.httpd.location, '')
                for r in self.collect_middleware.requests]),
            set(self.httpd.sitemap.keys())
        )

    def test_asyncio_concurrent_crawler(self):
        pomp = AioPomp(
            downloader=self.downloader,
            middlewares=self.middlewares,
            pipelines=[],
        )

        loop = asyncio.get_event_loop()
        loop.run_until_complete(pomp.pump(Crawler()))

        loop.run_until_complete(pomp.pump(
            AioConcurrentCrawler(
                worker_class=Crawler,
                pool_size=2,
            )
        ))

        assert_set_equal(
            set([r.url.replace(self.httpd.location, '')
                for r in self.collect_middleware.requests]),
            set(self.httpd.sitemap.keys())
        )
