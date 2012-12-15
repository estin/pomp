import logging
from nose.tools import assert_equal
from pomp.core.base import BaseCrawler, BaseDownloader, BasePipeline
from pomp.core.base import CRAWL_WIDTH_FIRST_METHOD
from pomp.core.engine import Pomp
from pomp.core.item import Item, Field


logging.basicConfig(level=logging.DEBUG)

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
        result = url if url not in self.crawled_urls else None
        self.crawled_urls.append(url)
        return result

    def extract_items(self, url, page):
        item = DummyItem()
        item.value = 1
        item.url = url
        return [item]


class DummyDownloader(BaseDownloader):

    def get(slef, url):
        return url, '<html><head></head><body></body></html>'


class TestSimplerCrawler(object):

    def test_crawler_dive_methods(self):
        class RoadPipeline(BasePipeline):

            def __init__(self):
                self.collection = []

            def process(self, item):
                self.collection.append(item)
                return item

            def reset(self):
                self.collection = []

        road = RoadPipeline()

        pomp = Pomp(
            downloader=DummyDownloader(),
            pipelines=[
                road,
            ],
        )

        # Depth first method
        pomp.pump(DummyCrawler())

        assert_equal([item.url for item in road.collection], [
            'http://python.org/1',
            'http://python.org/1/trash',
            'http://python.org/2',
        ])

        # Width first method
        road.reset()

        class DummyWidthCrawler(DummyCrawler):
            CRAWL_METHOD = CRAWL_WIDTH_FIRST_METHOD

        pomp.pump(DummyWidthCrawler())

        assert_equal([item.url for item in road.collection], [
            'http://python.org/1',
            'http://python.org/2',
            'http://python.org/1/trash',
        ])

    def test_pipeline(self):

        class IncPipeline(BasePipeline):

            def process(self, item):
                item.value += 1
                return item

        class FilterPipeline(BasePipeline):

            def process(self, item):
                if 'trash' in item.url:
                    return None
                return item

        class SavePipeline(BasePipeline):

            def __init__(self, collection):
                self.collection = collection

            def process(self, item):
                self.collection.append(item)
                return item

        result = []

        pomp = Pomp(
            downloader=DummyDownloader(),
            pipelines=[
                IncPipeline(),
                FilterPipeline(),
                SavePipeline(result),
            ],
        )

        pomp.pump(DummyCrawler())

        assert_equal([(item.url, item.value) for item in result], [
            ('http://python.org/1', 2),
            ('http://python.org/2', 2),
        ])

