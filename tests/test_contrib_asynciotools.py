import sys
import pytest

asyncio = pytest.importorskip("asyncio")  # noqa
aiohttp = pytest.importorskip("aiohttp")  # noqa

import logging
from pomp.core.base import (
    BaseHttpRequest,
    BaseHttpResponse,
    BaseDownloader,
    BaseMiddleware,
    BasePipeline,
    BaseCrawlException,
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


class SyncPipeline(BasePipeline):

    def start(self, crawler):
        self.items = []
        self.item_count = 0

    def process(self, crawler, item):
        self.items.append(item)
        return item

    def stop(self, crawler):
        self.items_count = len(self.items)


class AsyncPipeline(BasePipeline):

    async def start(self, crawler):
        self.items = []

    async def process(self, crawler, item):
        self.items.append(item)
        return item

    async def stop(self, crawler):
        self.items_count = len(self.items)


class AiohttpRequest(BaseHttpRequest):
    def __init__(self, url):
        self.url = url

    def __str__(self):
        return '<AiohttpRequest url:{s.url}>'.format(s=self)


class AiohttpResponse(BaseHttpResponse):
    def __init__(self, request, body):
        self.request = request
        self.body = body

    def get_request(self):
        return self.request


class AiohttpAdapterMiddleware(BaseMiddleware):
    async def process_request(self, req, crawler, downloader):
        log.debug(
            "AiohttpAdapterMiddleware %s %s",
            req, isinstance(req, BaseHttpRequest),
        )
        if isinstance(req, BaseHttpRequest):
            return req
        return AiohttpRequest(req)

    async def process_response(self, response, crawler, downloader):
        return response


class AiohttpDownloader(BaseDownloader):

    async def start(self, *args, **kwargs):
        log.debug("[AiohttpDownloader] Start session")
        self.session = aiohttp.ClientSession()

    async def stop(self, *args, **kwargs):
        log.debug("[AiohttpDownloader] Close session")
        self.session.close()

    async def _fetch(self, request, future=None):
        log.debug("[AiohttpDownloader] Start fetch: %s", request.url)
        try:
            async with self.session.get(request.url) as response:
                body = await response.text()
                log.debug(
                    "[AiohttpDownloader] Done %s: %s %s",
                    request.url, len(body), body[0:20],
                )
                response = AiohttpResponse(request, body)
        except Exception as e:
            log.exception("[AiohttpDownloader] exception on %s", request)
            response = BaseCrawlException(
                request=request,
                response=None,
                exception=e,
                exc_info=sys.exc_info(),
            )

        if future:
            future.set_result(response)
        else:
            return response

    def get_workers_count(self):
        return 2

    def process(self, crawler, request):
        return ensure_future(self._fetch(request))


class AiohttpDownloaderWithPlanned(AiohttpDownloader):

    def process(self, crawler, request):
        future = asyncio.Future()
        ensure_future(self._fetch(request, future))

        planned = Planned()

        def build_response(f):
            planned.set_result(f.result())
        future.add_done_callback(build_response)

        return planned


class AiohttpDownloaderWithAsyncProcess(AiohttpDownloader):

    async def process(self, crawler, request):
        return await self._fetch(request)


class Crawler(DummyCrawler):
    ENTRY_REQUESTS = '/root'


class AioCrawler(DummyCrawler):
    ENTRY_REQUESTS = '/root'

    async def process(self, *args, **kwargs):
        for i in super(AioCrawler, self).process(*args, **kwargs):
            yield i

    async def next_requests(self, *args, **kwargs):
        for i in super(AioCrawler, self).next_requests(*args, **kwargs) or []:
            yield i

    async def on_processing_done(self, *args, **kwargs):
        super(AioCrawler, self).on_processing_done(*args, **kwargs)


class TestContribAsyncio(object):
    @classmethod
    def setup_class(cls):
        cls.httpd = HttpServer(sitemap=make_sitemap(level=2, links_on_page=2))
        cls.httpd.start()

    @classmethod
    def teardown_class(cls):
        cls.httpd.stop()

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

        assert \
            set([r.url.replace(self.httpd.location, '')
                for r in self.collect_middleware.requests]) == \
            set(self.httpd.sitemap.keys())

    def test_asyncio_engine_with_planned(self):
        pomp = AioPomp(
            downloader=AiohttpDownloaderWithPlanned(),
            middlewares=self.middlewares,
            pipelines=[],
        )

        loop = asyncio.get_event_loop()
        loop.run_until_complete(pomp.pump(Crawler()))

        assert \
            set([r.url.replace(self.httpd.location, '')
                for r in self.collect_middleware.requests]) == \
            set(self.httpd.sitemap.keys())

    def test_asyncio_engine_with_async_process(self):
        pomp = AioPomp(
            downloader=AiohttpDownloaderWithAsyncProcess(),
            middlewares=self.middlewares,
            pipelines=[],
        )

        loop = asyncio.get_event_loop()
        loop.run_until_complete(pomp.pump(Crawler()))

        assert \
            set([r.url.replace(self.httpd.location, '')
                for r in self.collect_middleware.requests]) == \
            set(self.httpd.sitemap.keys())

    def test_asyncio_engine_with_aio_crawler(self):
        pomp = AioPomp(
            downloader=self.downloader,
            middlewares=self.middlewares,
            pipelines=[],
        )

        loop = asyncio.get_event_loop()
        loop.run_until_complete(pomp.pump(AioCrawler()))

        assert \
            set([r.url.replace(self.httpd.location, '')
                for r in self.collect_middleware.requests]) == \
            set(self.httpd.sitemap.keys())

    def test_asyncio_concurrent_crawler(self):
        pomp = AioPomp(
            downloader=self.downloader,
            middlewares=self.middlewares,
            pipelines=[],
        )

        loop = asyncio.get_event_loop()
        loop.run_until_complete(pomp.pump(
            AioConcurrentCrawler(
                worker_class=Crawler,
                pool_size=2,
            )
        ))

        assert \
            set([r.url.replace(self.httpd.location, '')
                for r in self.collect_middleware.requests]) == \
            set(self.httpd.sitemap.keys())

    def test_asyncio_pipelines(self):
        sync_pipeline = SyncPipeline()
        async_pipeline = AsyncPipeline()

        pomp = AioPomp(
            downloader=self.downloader,
            middlewares=self.middlewares,
            pipelines=[
                sync_pipeline,
                async_pipeline,
            ],
        )

        loop = asyncio.get_event_loop()
        loop.run_until_complete(pomp.pump(Crawler()))

        assert sync_pipeline.items_count
        assert async_pipeline.items_count
        assert sync_pipeline.items_count == async_pipeline.items_count
