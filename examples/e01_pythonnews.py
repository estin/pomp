"""
Extract python news from python.org
"""
import sys
import re
import logging
from pomp.core.base import BaseCrawler, BasePipeline
from pomp.contrib.item import Item, Field
from pomp.contrib.urllibtools import (
    UrllibDownloader, UrllibHttpRequest,
)


logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
news_re = re.compile(
    r'<h2 class="news">(.*?)</h2>([\s\S]*?)<div class="pubdate">(.*?)</div>')


class PythonNewsItem(Item):
    title = Field()
    published = Field()

    def __str__(self):
        return '%s\n\t%s\n' % (
            self.title,
            self.published,
        )


class PythonNewsCrawler(BaseCrawler):
    ENTRY_REQUESTS = UrllibHttpRequest('http://python.org/news/')

    def extract_items(self, response):
        for i in news_re.findall(response.body.decode('utf-8')):
            item = PythonNewsItem()
            item.title, item.published = i[0], i[2]
            yield item

    def next_requests(self, response):
        return None  # one page crawler


class PrintPipeline(BasePipeline):

    def process(self, crawler, item):
        print(item)
        return item


if __name__ == '__main__':
    from pomp.core.engine import Pomp

    pomp = Pomp(
        downloader=UrllibDownloader(),
        pipelines=[PrintPipeline()],
    )

    pomp.pump(PythonNewsCrawler())
