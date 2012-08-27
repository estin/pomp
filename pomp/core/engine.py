"""
Engine
"""
from pomp.core.utils import iterator


class Pomp(object):

    def __init__(self, downloader, pipelines=None):

        self.downloader = downloader
        self.pipelines = pipelines or tuple()

    def response_callback(self, crawler, url, page):

        items = crawler.process(url, page)

        if items:
            for pipe in self.pipelines:
                items = filter(None, map(pipe.process, items))

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
        finally:
            map(lambda pipe: pipe.stop(), self.pipelines)
