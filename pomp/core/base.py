"""
Base classes
"""
import types


def iterator(var):
    if isinstance(var, types.StringTypes):
        return iter((var,))
    return iter(var)


class BaseCrawler(object):
    ENTRY_URL = None

    def next_url(self, page):
        raise NotImplementedError()

    def process(self, url, page):
        self.extract_items(url, page)

    def extract_items(self, url, page):
        raise NotImplementedError()


class BaseDownloader(object):

    def process(self, urls, callback, crawler):
        map(lambda url: callback(crawler, url, self.get(url)), urls)

    def get(self, url):
        raise NotImplementedError()
