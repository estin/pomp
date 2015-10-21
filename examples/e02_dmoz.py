# coding: utf-8
"""
    Stolen from https://github.com/scrapy/dirbot

    requires: lxml

    store csv data to /<os tmpdir>/dmoz.csv
"""
import os
import re
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
from pomp.core.base import BasePipeline, BaseDownloaderMiddleware
from pomp.core.item import Item, Field
from pomp.contrib.urllibtools import UrllibHttpRequest


logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)


class StatisticMiddleware(BaseDownloaderMiddleware):
    def __init__(self):
        self.requests = self.responses = self.exceptions = 0

    def process_request(self, request):
        self.requests += 1
        return request

    def process_response(self, response):
        self.responses += 1
        return response

    def process_exception(self, exception):
        self.exceptions += 1
        return exception

    def __str__(self):
        return 'requests/responses/exceptions ' \
            '= {s.requests}/{s.responses}/{s.exceptions}' \
            .format(s=self)


class LXMLDownloaderMiddleware(BaseDownloaderMiddleware):

    def __init__(self, encoding=None):
        self.encoding = encoding

    def process_request(self, request):
        return request

    def process_response(self, response):
        if self.encoding:
            response.tree = html.fromstring(
                response.body.decode(self.encoding)
            )
        else:
            response.tree = html.fromstring(response.body)
        return response


class WebsiteItem(Item):

    name = Field()
    url = Field()
    description = Field()

    def __str__(self):
        return u'{s.name}\nurl: {s.url}\ndesc: {s.description}'.format(s=self)


class PrintPipeline(BasePipeline):

    def process(self, crawler, item):
        print('-' * 75)
        print(u'%s' % item)
        return item


class DmozSpider(BaseCrawler):
    BASE_URL = 'http://www.dmoz.org/'

    ENTRY_REQUESTS = UrllibHttpRequest(urljoin(
        BASE_URL, '/Computers/Programming/Languages/Python/Books/'
    ))

    DESCRIPTION_CLEANUP_RE = re.compile('-\s([^\n]*?)\\n')

    SITES_XPATH = '//ul[@class="directory-url"]/li'
    NEXT_URLS_XPATH = '//ul[@class="language"]/li/a'

    def __init__(self):
        super(DmozSpider, self).__init__()
        self._parsed_urls = [self.ENTRY_REQUESTS]

    def extract_items(self, response):

        # extract data
        for site in response.tree.xpath(self.SITES_XPATH):
            item = WebsiteItem()

            item.name = ''.join(site.xpath('a/text()'))
            item.url = ''.join(site.xpath('a/@href'))
            item.description = ''.join(self.DESCRIPTION_CLEANUP_RE.findall(
                ''.join(site.xpath('text()'))
            ))

            yield item

        # extract next urls
        for link in response.tree.xpath(self.NEXT_URLS_XPATH):
            url = urljoin(self.BASE_URL, link.get('href'))
            if url not in self._parsed_urls:
                self._parsed_urls.append(url)
                yield UrllibHttpRequest(url)


if __name__ == '__main__':
    from pomp.core.engine import Pomp
    from pomp.contrib.concurrenttools import ConcurrentUrllibDownloader

    statistics = StatisticMiddleware()
    middlewares = (
        statistics,
        LXMLDownloaderMiddleware(encoding='utf-8'),
    )

    filepath = os.path.join(tempfile.gettempdir(), 'dmoz.csv')
    pomp = Pomp(
        downloader=ConcurrentUrllibDownloader(
            pool_size=3,
            middlewares=middlewares,
        ),
        pipelines=[
            PrintPipeline(),
            CsvPipeline(filepath, delimiter=';', quotechar='"'),
        ],
    )

    pomp.pump(DmozSpider())
    print("Statistics:\n %s" % statistics)
