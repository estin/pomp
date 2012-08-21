"""
Engine
"""


class Pomp(object):

    def __init__(self, downloader):

        self.downloader = downloader

    def pump(self, crawler):

        # fetch entry url
        page = self.downloader.get(crawler.ENTRY_URL)

        # process page
        crawler.process(page)

        # get next url
        crawler.next_url(page)
