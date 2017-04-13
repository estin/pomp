# coding: utf-8
"""
    Stolen from https://github.com/scrapy/quotesbot

    requires: lxml

    store csv data to /<os tmpdir>/quotes.csv
"""
import os
import sys
import logging
import tempfile

try:
    from urlparse import urljoin
except ImportError:
    from urllib.parse import urljoin

from lxml import html

from pomp.core.base import BaseCrawler
from pomp.contrib.pipelines import CsvPipeline
from pomp.core.base import BasePipeline, BaseMiddleware
from pomp.contrib.item import Item, Field
from pomp.contrib.urllibtools import UrllibHttpRequest


logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)


class StatisticMiddleware(BaseMiddleware):
    def __init__(self):
        self.requests = self.responses = self.exceptions = 0

    def process_request(self, request, crawler, downloader):
        self.requests += 1
        return request

    def process_response(self, response, crawler, downloader):
        self.responses += 1
        return response

    def process_exception(self, exception, crawler, downloader):
        self.exceptions += 1
        return exception

    def __str__(self):
        return 'requests/responses/exceptions ' \
            '= {s.requests}/{s.responses}/{s.exceptions}' \
            .format(s=self)


class LXMLDownloaderMiddleware(BaseMiddleware):

    def __init__(self, encoding=None):
        self.encoding = encoding

    def process_response(self, response, crawler, downloader):
        if self.encoding:
            response.tree = html.fromstring(
                response.body.decode(self.encoding)
            )
        else:
            response.tree = html.fromstring(response.body)
        return response


class QuotesItem(Item):

    author = Field()
    text = Field()
    tags = Field()

    def __str__(self):
        return u'{s.author}:\n{s.text}\ntags: {s.tags}'.format(s=self)


class PrintPipeline(BasePipeline):

    def process(self, crawler, item):
        print('-' * 75)
        print(u'%s' % item)
        return item


class QuotesSpider(BaseCrawler):
    BASE_URL = 'http://quotes.toscrape.com/'

    ENTRY_REQUESTS = UrllibHttpRequest(urljoin(
        BASE_URL, '/tag/books/'
    ))

    QUOTES_XPATH = '//div[@class="quote"]'
    NEXT_URLS_XPATH = '//li[@class="next"]/a'

    def __init__(self):
        super(QuotesSpider, self).__init__()

    def extract_items(self, response):

        # extract data
        for quote in response.tree.xpath(self.QUOTES_XPATH):
            item = QuotesItem()

            item.author = ''.join(
                quote.xpath('.//small[@class="author"]/text()'))
            item.text = ''.join(quote.xpath('span[@class="text"]/text()'))
            item.tags = quote.xpath('.//a[@class="tag"]/text()')

            yield item

        # extract next urls
        for link in response.tree.xpath(self.NEXT_URLS_XPATH):
            yield UrllibHttpRequest(urljoin(self.BASE_URL, link.get('href')))


if __name__ == '__main__':
    from pomp.core.engine import Pomp
    from pomp.contrib.concurrenttools import ConcurrentUrllibDownloader

    statistics = StatisticMiddleware()
    middlewares = (
        statistics,
        LXMLDownloaderMiddleware(encoding='utf-8'),
    )

    filepath = os.path.join(tempfile.gettempdir(), 'quotes.csv')
    pomp = Pomp(
        downloader=ConcurrentUrllibDownloader(
            pool_size=3,
        ),
        middlewares=middlewares,
        pipelines=(
            PrintPipeline(),
            CsvPipeline(filepath, delimiter=';', quotechar='"'),
        ),
    )

    pomp.pump(QuotesSpider())
    print("Statistics:\n %s" % statistics)
