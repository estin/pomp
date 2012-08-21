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
            ENTRY_URL = "http://python.org/"

            def next_url(self, current_page):
                return None

            def extract_items(self, page):
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
