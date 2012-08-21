from pomp.core.base import BaseCrawler, BaseDownloader
from pomp.core.engine import Pomp


class TestSimplerCrawler(object):

    def test_crawler(self):

        class PythonOrgCrawler(BaseCrawler):
            ENTRY_URL = "http://python.org/"

            def next_url(self, current_page):
                return None

            def extract_items(self, page):
                return ['1', '2', '3', '4', '5']

        class DummyDownloader(BaseDownloader):

            def get(slef, url):
                return '<html><head></head><body></body></html>'

        pomp = Pomp(downloader=DummyDownloader())

        pomp.pump(PythonOrgCrawler())
