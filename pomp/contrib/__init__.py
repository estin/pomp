"""
Standart downloaders
"""
try:
    from urllib.request import urlopen
except ImportError:
    from urllib2 import urlopen

from multiprocessing.pool import ThreadPool
from pomp.core.base import BaseDownloader


class SimpleDownloader(BaseDownloader):

    TIMEOUT = 5

    def get(self, url):
        response = urlopen(url, timeout=self.TIMEOUT)
        return url, response.read()


class ThreadedDownloader(SimpleDownloader):

    def __init__(self, pool_size=5):
        self.workers_pool = ThreadPool(processes=pool_size)
    
    def process(self, urls, callback, crawler):
        pages = self.workers_pool.map(self.get, urls)
        return filter(
            None,
            list(map(lambda res: callback(crawler, *res), pages))
        )
