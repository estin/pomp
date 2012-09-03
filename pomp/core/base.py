"""
Base classes
"""
CRAWL_DEPTH_FIRST_METHOD = 'depth'
CRAWL_WIDTH_FIRST_METHOD = 'width'


class BaseCrawler(object):
    ENTRY_URL = None
    CRAWL_METHOD = CRAWL_DEPTH_FIRST_METHOD

    def next_url(self, page):
        raise NotImplementedError()

    def process(self, url, page):
        return self.extract_items(url, page)

    def extract_items(self, url, page):
        raise NotImplementedError()

    @property
    def is_depth_first(self):
        return self.CRAWL_METHOD == CRAWL_DEPTH_FIRST_METHOD


class BaseDownloader(object):

    def process(self, urls, callback, crawler):
        return filter(
            None,
            map(lambda url: callback(crawler, url, self.get(url)), urls)
        )

    def get(self, url):
        raise NotImplementedError()


class BasePipeline(object):

    def start(self):
        pass

    def process(self, item):
        raise NotImplementedError()

    def stop(self):
        pass
