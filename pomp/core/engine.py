"""
Engine
"""
from pomp.core.base import iterator


class Pomp(object):

    def __init__(self, downloader, pipelines=None):

        self.downloader = downloader
        self.pipelines = pipelines or tuple()
        self.collector = []

    def collect(self, items):
        self.collector += items

    def response_callback(self, crawler, url, page):

        items = crawler.process(url, page)

        if items:
            for pipe in self.pipelines:
                items = filter(None, map(pipe.process, items))

        self.collect(items)

        urls = crawler.next_url(page)

        if urls:
            self.downloader.process(
                iterator(urls),
                self.response_callback,
                crawler
            )

    def pump(self, crawler):

        map(lambda pipe: pipe.start(), self.pipelines)

        try:
            self.downloader.process(
                iterator(crawler.ENTRY_URL),
                self.response_callback,
                crawler
            )

            return self.collector
        finally:
            map(lambda pipe: pipe.stop(), self.pipelines)
