"""
Standart downloaders
"""
import urllib2
from pomp.core.base import BaseDownloader


class SimpleDownloader(BaseDownloader):

    TIMEOUT = 5

    def get(self, url):
        response = urllib2.urlopen(url, timeout=self.TIMEOUT)
        return response.read()
