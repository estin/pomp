"""
Engine
"""
from pomp.core.base import iterator


class Pomp(object):

    def __init__(self, downloader):

        self.downloader = downloader

    def response_callback(self, crawler, url, page):

        crawler.process(url, page)

        urls = crawler.next_url(page)

        if urls:
            self.downloader.process(
                iterator(urls),
                self.response_callback,
                crawler
            )

    def pump(self, crawler):

        self.downloader.process(
            iterator(crawler.ENTRY_URL),
            self.response_callback,
            crawler
        )
