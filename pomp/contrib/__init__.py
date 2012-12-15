"""
Standart downloaders
"""
try:
    from urllib.request import urlopen
except ImportError:
    from urllib2 import urlopen

from pomp.core.base import BaseDownloader


class SimpleDownloader(BaseDownloader):

    TIMEOUT = 5

    def get(self, url):
        response = urlopen(url, timeout=self.TIMEOUT)
        return response.read()
