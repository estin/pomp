.. _quickstart:

Quickstart
==========

.. currentmodule:: pomp.core.base

Pomp is fun to use, incredibly easy for basic applications.

A Minimal Application
---------------------

For a minimal application all you need is to define you crawler inherited 
from :class:`BaseCrawler`::

    from pomp.core.base import BaseCrawler
    from pomp.contrib import SimpleDownloader


    class MyCrawler(BaseCrawler):
        ENTRY_URL = 'http://python.org/news' # entry point

        def extract_items(self, response):
            response.body = response.body.decode('utf-8')
            return None

        def next_url(self, response):
            return None # one page crawler, stop crawl

    if __name__ == '__main__':
        from pomp.core.engine import Pomp

        pomp = Pomp(
            downloader=SimpleDownloader(),
        )

        pomp.pump(MyCrawler())
