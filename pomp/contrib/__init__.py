"""
Standart downloaders
"""
try:
    from urllib.request import urlopen
except ImportError:
    from urllib2 import urlopen

from multiprocessing.pool import ThreadPool
from pomp.core.base import BaseDownloader
from pomp.core.utils import iterator


def fetch(url, timeout):
    return urlopen(url, timeout=timeout).read()


class SimpleDownloader(BaseDownloader):

    TIMEOUT = 5

    def get(self, urls):
        responses = []
        for url in iterator(urls):
            response = fetch(url, timeout=self.TIMEOUT)
            responses.append((url, response))
        return responses


class ThreadedDownloader(BaseDownloader):

    TIMEOUT = 5

    def __init__(self, pool_size=5, *args, **kwargs):
        self.workers_pool = ThreadPool(processes=pool_size)
        super(ThreadedDownloader, self).__init__(*args, **kwargs)

    def fetch(self, url):
        return fetch(url, timeout=self.TIMEOUT)
    
    def get(self, urls):
        return zip(urls, self.workers_pool.map(self.fetch, urls))
