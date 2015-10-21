"""
EXPERIMENTAL asyncio support.
For python >= 3.3, requires: aiohttp, lxml

e02_dmoz.py on aiohttp downloader
"""
# import re
import sys
import logging
import asyncio

try:
    from asyncio import ensure_future
except ImportError:
    from asyncio import async as ensure_future

import aiohttp

from pomp.core.base import (
    BaseQueue, BaseHttpRequest, BaseHttpResponse, BaseDownloader,
)
from pomp.core.utils import Planned


logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
log = logging.getLogger(__name__)


class AiohttpRequest(BaseHttpRequest):
    def __init__(self, url):
        self._url = url

    @property
    def url(self):
        return self._url

    def __str__(self):
        return '<AiohttpRequest url:{s.url}>'.format(s=self)


class AiohttpResponse(BaseHttpResponse):
    def __init__(self, request, body):
        self.req = request
        self.body = body


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

    def get(self, requests):
        for request in requests:

            future = asyncio.Future()
            ensure_future(self._fetch(request, future))

            planned = Planned()

            def build_response(f):
                planned.set_result(f.result())
            future.add_done_callback(build_response)

            yield planned


class AiohttpQueue(BaseQueue):
    def __init__(self, loop):
        self.q = asyncio.Queue()
        self.loop = loop

    def get_requests(self):
        future = ensure_future(self.q.get())
        # block pomp loop and run asyncio loop
        self.loop.run_until_complete(future)
        return future.result()

    def put_requests(self, requests):
        ensure_future(self.q.put(requests))


if __name__ == '__main__':
    from pomp.core.engine import Pomp
    from e02_dmoz import (
        PrintPipeline, DmozSpider, LXMLDownloaderMiddleware,
        StatisticMiddleware,
    )

    loop = asyncio.get_event_loop()
    statistics = StatisticMiddleware()
    pomp = Pomp(
        downloader=AiohttpDownloader(
            middlewares=(
                statistics,
                LXMLDownloaderMiddleware(),
            ),
        ),
        pipelines=[PrintPipeline()],
        queue=AiohttpQueue(loop=loop),
    )
    pomp.pump(DmozSpider())
    print("Statistics:\n %s" % statistics)
