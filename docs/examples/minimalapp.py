import re
from pomp.core.base import BaseCrawler


python_sentence_re = re.compile('[\w\s]{0,}python[\s\w]{0,}', re.I | re.M)


class MyCrawler(BaseCrawler):
    """Extract all sentences with `python` word"""
    ENTRY_REQUESTS = 'http://python.org/news'  # entry point

    def extract_items(self, response):
        for i in python_sentence_re.findall(response.body.decode('utf-8')):
            item = i.strip()
            print(item)
            return item

    def next_requests(self, response):
        return None  # one page crawler, stop crawl


if __name__ == '__main__':
    from pomp.core.engine import Pomp
    from pomp.contrib.urllibtools import UrllibDownloader

    pomp = Pomp(
        downloader=UrllibDownloader(),
    )

    pomp.pump(MyCrawler())
