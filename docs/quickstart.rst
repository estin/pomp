.. _quickstart:

Quickstart
==========

.. currentmodule:: pomp.core.base

Pomp is fun to use, incredibly easy for basic applications.

A Minimal Application
---------------------

For a minimal application all you need is to define you crawler 
by inherit :class:`BaseCrawler`::

    import re
    from pomp.core.base import BaseCrawler, BasePipeline
    from pomp.contrib import SimpleDownloader


    python_sentence_re = re.compile('[\w\s]{0,}python[\s\w]{0,}', re.I | re.M)


    class MyCrawler(BaseCrawler):
        """Extract all sentences with `python` word"""
        ENTRY_URL = 'http://python.org/news' # entry point

        def extract_items(self, response):
            for i in python_sentence_re.findall(response.body.decode('utf-8')):
                yield i.strip()

        def next_url(self, response):
            return None # one page crawler, stop crawl


    class PrintPipeline(BasePipeline):
        def process(self, item):
            print('Sentence:', item)


    if __name__ == '__main__':
        from pomp.core.engine import Pomp

        pomp = Pomp(
            downloader=SimpleDownloader(),
            pipelines=(PrintPipeline(),)
        )

        pomp.pump(MyCrawler())


Item pipelines
--------------


Custom downloader
-----------------


Downloader middleware
---------------------
