"""
asyncio support
For python >= 3.4, requires: aiohttp, lxml

e02_quotes.py on aiohttp downloader
"""
import sys
import logging

import asyncio
import aiohttp

from pomp.core.base import (
    BaseHttpRequest,
    BaseHttpResponse,
    BaseDownloader,
    BaseCrawlException,
)


logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
log = logging.getLogger(__name__)


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


class AiohttpDownloader(BaseDownloader):

    def start(self, crawler):
        log.debug("[AiohttpDownloader] Start session")
        self.session = aiohttp.ClientSession()

    def stop(self, crawler):
        log.debug("[AiohttpDownloader] Close session")
        self.session.close()

    async def process(self, crawler, request):
        log.debug("[AiohttpDownloader] Start fetch: %s", request.url)
        try:
            async with self.session.get(request.url) as response:
                body = await response.text()
                log.debug(
                    "[AiohttpDownloader] Done %s: %s %s",
                    request.url, len(body), body[0:20],
                )
                return AiohttpResponse(request, body)
        except Exception as e:
            log.exception("[AiohttpDownloader] exception on %s", request)
            return BaseCrawlException(
                request=request,
                response=None,
                exception=e,
                exc_info=sys.exc_info(),
            )


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
