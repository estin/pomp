"""
Base classes
"""


class BaseCrawler(object):
    ENTRY_URL = None

    def next_url(self, page):
        raise NotImplementedError()

    def process(self, url, page):
        return self.extract_items(url, page)

    def extract_items(self, url, page):
        raise NotImplementedError()


class BaseDownloader(object):

    def process(self, urls, callback, crawler):
        map(lambda url: callback(crawler, url, self.get(url)), urls)

    def get(self, url):
        raise NotImplementedError()


class BasePipeline(object):

    def start(self):
        pass

    def process(self, item):
        raise NotImplementedError()

    def stop(self):
        pass
