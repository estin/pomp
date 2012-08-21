"""
Base classes
"""

class BaseCrawler(object):
    ENTRY_URL = None

    def next_url(self, page):
        raise NotImplementedError()

    def process(self, page):
        self.extract_items(page)

    def extract_items(self, page):
        raise NotImplementedError()


class BaseDownloader(object):

    def get(self, url):
        raise NotImplementedError()
