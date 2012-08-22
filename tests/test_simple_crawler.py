from pomp.core.base import BaseCrawler, BaseDownloader
from pomp.core.engine import Pomp
from pomp.core.item import Item, Field


class TestSimplerCrawler(object):

    def test_crawler(self):

        class DummyItem(Item):
            f1 = Field()
            f2 = Field()
            f3 = Field()

        class DummyCrawler(BaseCrawler):
            ENTRY_URL = (
                "http://python.org/1",
                "http://python.org/2"
            )

            def __init__(self):
                super(DummyCrawler, self).__init__()
                self.crawled_urls = []

            def next_url(self, page):
                url = 'http://python.org/1/1'
                return url if url not in self.crawled_urls else None

            def extract_items(self, url, page):
                self.crawled_urls.append(url)
                item = DummyItem()
                item.f1 = '1'
                item.f2 = '2'
                item.f3 = '3'
                return [item]

        class DummyDownloader(BaseDownloader):

            def get(slef, url):
                return '<html><head></head><body></body></html>'

        pomp = Pomp(downloader=DummyDownloader())

        pomp.pump(DummyCrawler())
