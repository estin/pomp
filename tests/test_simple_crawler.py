import logging
from nose.tools import assert_equal
from pomp.core.base import BasePipeline, BaseQueue
from pomp.core.base import CRAWL_WIDTH_FIRST_METHOD
from pomp.core.engine import Pomp


from tools import DummyCrawler, DummyDownloader, DummyRequest
from tools import RequestResponseMiddleware


logging.basicConfig(level=logging.DEBUG)


url_to_request_middl = RequestResponseMiddleware(
    request_factory=DummyRequest,
    bodyjson=False
)


class Crawler(DummyCrawler):
    ENTRY_REQUESTS = (
        "http://python.org/1",
        "http://python.org/2"
    )

    def __init__(self):
        super(Crawler, self).__init__()
        self.crawled_urls = []

    def next_requests(self, response):
        url = 'http://python.org/1/trash'
        result = url if url not in self.crawled_urls else None
        self.crawled_urls.append(url)
        return result


class RoadPipeline(BasePipeline):

    def __init__(self):
        self.collection = []

    def process(self, crawler, item):
        self.collection.append(item)
        return item

    def reset(self):
        self.collection = []


class TestSimplerCrawler(object):

    def test_crawler_dive_methods(self):
        road = RoadPipeline()

        pomp = Pomp(
            downloader=DummyDownloader(middlewares=[url_to_request_middl]),
            pipelines=[
                road,
            ],
        )

        # Depth first method
        pomp.pump(Crawler())

        assert_equal(set([item.url for item in road.collection]), set([
            'http://python.org/1',
            'http://python.org/1/trash',
            'http://python.org/2',
        ]))

        # Width first method
        road.reset()

        class DummyWidthCrawler(Crawler):
            CRAWL_METHOD = CRAWL_WIDTH_FIRST_METHOD

        pomp.pump(DummyWidthCrawler())

        assert_equal(set([item.url for item in road.collection]), set([
            'http://python.org/1',
            'http://python.org/2',
            'http://python.org/1/trash',
        ]))

    def test_pipeline(self):

        class IncPipeline(BasePipeline):

            def process(self, crawler, item):
                item.value += 1
                return item

        class FilterPipeline(BasePipeline):

            def process(self, crawler, item):
                if 'trash' in item.url:
                    return None
                return item

        class SavePipeline(BasePipeline):

            def __init__(self, collection):
                self.collection = collection

            def process(self, crawler, item):
                self.collection.append(item)
                return item

        result = []

        pomp = Pomp(
            downloader=DummyDownloader(middlewares=[url_to_request_middl]),
            pipelines=[
                IncPipeline(),
                FilterPipeline(),
                SavePipeline(result),
            ],
        )

        pomp.pump(Crawler())

        assert_equal([(item.url, item.value) for item in result], [
            ('http://python.org/1', 2),
            ('http://python.org/2', 2),
        ])

    def test_queue_crawler(self):
        road = RoadPipeline()

        class SimpleQueue(BaseQueue):

            def __init__(self):
                self.requests = []

            def get_requests(self):
                try:
                    return self.requests.pop()
                except IndexError:
                    return  # empty queue

            def put_requests(self, request):
                self.requests.append(request)

        queue = SimpleQueue()

        pomp = Pomp(
            downloader=DummyDownloader(middlewares=[url_to_request_middl]),
            pipelines=[
                road,
            ],
            queue=queue,
            stop_on_empty_queue=True,
        )

        class DummyWidthCrawler(Crawler):
            CRAWL_METHOD = CRAWL_WIDTH_FIRST_METHOD

        pomp.pump(DummyWidthCrawler())

        assert_equal(set([item.url for item in road.collection]), set([
            'http://python.org/1',
            'http://python.org/1/trash',
            'http://python.org/2',
        ]))
