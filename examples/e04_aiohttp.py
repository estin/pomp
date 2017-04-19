"""
asyncio support
For python >= 3.4, requires: aiohttp, lxml

e02_quotes.py on aiohttp downloader
"""
import sys
import logging
import asyncio

try:
    from asyncio import ensure_future
except ImportError:
    from asyncio import async as ensure_future

import aiohttp

from pomp.core.base import (
    BaseHttpRequest, BaseHttpResponse, BaseDownloader,
)
from pomp.core.utils import Planned


logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
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


class AiohttpDownloader(BaseDownloader):

    def prepare(self):
        log.debug("[AiohttpDownloader] Start session")
        self.session = aiohttp.ClientSession()

    def stop(self):
        log.debug("[AiohttpDownloader] Close session")
        self.session.close()

    async def _fetch(self, request, future):
        log.debug("[AiohttpDownloader] Start fetch: %s", request.url)
        async with self.session.get(request.url) as response:
            body = await response.text()
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


if __name__ == '__main__':
    from pomp.contrib.asynciotools import AioPomp
    from e02_quotes import (
        PrintPipeline, QuotesSpider, LXMLDownloaderMiddleware,
        StatisticMiddleware,
    )

    loop = asyncio.get_event_loop()
    statistics = StatisticMiddleware()
    pomp = AioPomp(
        downloader=AiohttpDownloader(),
        middlewares=(
            statistics,
            LXMLDownloaderMiddleware(),
        ),
        pipelines=[PrintPipeline()],
    )
    loop.run_until_complete(pomp.pump(QuotesSpider()))
    loop.close()
    print("Statistics:\n %s" % statistics)
