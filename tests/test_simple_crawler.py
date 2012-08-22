from pomp.core.base import BaseCrawler, BaseDownloader, BasePipeline
from pomp.core.engine import Pomp
from pomp.core.item import Item, Field


class TestSimplerCrawler(object):

    def test_crawler(self):

        class DummyItem(Item):
            value = Field()
            url = Field()

            def __repr__(self):
                return '<DummyItem(%s, %s)>' % (self.url, self.value)

        class DummyCrawler(BaseCrawler):
            ENTRY_URL = (
                "http://python.org/1",
                "http://python.org/2"
            )

            def __init__(self):
                super(DummyCrawler, self).__init__()
                self.crawled_urls = []

            def next_url(self, page):
                url = 'http://python.org/1/trash'
                return url if url not in self.crawled_urls else None

            def extract_items(self, url, page):
                self.crawled_urls.append(url)
                item = DummyItem()
                item.value = 1
                item.url = url
                return [item]

        class DummyDownloader(BaseDownloader):

            def get(slef, url):
                return '<html><head></head><body></body></html>'


        class IncPipeline(BasePipeline):

            def process(self, item):
                item.value += 1
                return item

        class FilterPipeline(BasePipeline):

            def process(self, item):
                if 'trash' in item.url:
                    return None
                return item

        pomp = Pomp(
            downloader=DummyDownloader(),
            pipelines=[IncPipeline(), FilterPipeline()],
        )

        result = pomp.pump(DummyCrawler())

        assert len(result) == 2
