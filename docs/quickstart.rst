.. _quickstart:

Quickstart
==========

.. currentmodule:: pomp.core

Pomp is fun to use, incredibly easy for basic applications.

A Minimal Application
---------------------

For a minimal application all you need is to define you crawler 
by inherit :class:`base.BaseCrawler`::

    import re
    from pomp.core.base import BaseCrawler


    python_sentence_re = re.compile('[\w\s]{0,}python[\s\w]{0,}', re.I | re.M)


    class MyCrawler(BaseCrawler):
        """Extract all sentences with `python` word"""
        ENTRY_REQUESTS = 'http://python.org/news' # entry point

        def extract_items(self, response):
            for i in python_sentence_re.findall(response.body.decode('utf-8')):
                item = i.strip()
                print(item)
                return item

        def next_requests(self, response):
            return None # one page crawler, stop crawl


    if __name__ == '__main__':
        from pomp.core.engine import Pomp
        from pomp.contrib.urllibtools import UrllibDownloader

        pomp = Pomp(
            downloader=UrllibDownloader(),
        )

        pomp.pump(MyCrawler())


Item pipelines
--------------

For processing extracted items pomp has pipelines mechanism.
Define pipe by subclass of :class:`base.BasePipeline` and pass
it to :class:`engine.Pomp` constructor.

Pipe calls one by one 

Example pipelines for filtering items with length less the 10 symbols and
printing sentence::

    class FilterPipeline(BasePipeline):
        def process(self, item):
            # None - skip item for following processing
            return None if len(item) < 10 else item

    class PrintPipeline(BasePipeline):
        def process(self, item):
            print('Sentence:', item, ' length:', len(item))
            return item # return item for following processing

    pomp = Pomp(
        downloader=UrllibDownloader(),
        pipelines=(FilterPipeline(), PrintPipeline(),)
    )

See :ref:`contrib-pipelines`


Custom downloader
-----------------
For download data from source target application can define
downloader to implement special protocols or strategies.

Custom downloader must be subclass of :class:`base.BaseDownloader`

For example downloader fetching data by requests_ package::

    import requests as requestslib
    from pomp.core.base import BaseDownloader, BaseDownloadException
    from pomp.core.base import BaseHttpRequest, BaseHttpResponse

    from pomp.core.utils import iterator


    class ReqRequest(BaseHttpRequest):
        def __init__(self, url):
            self._url = url
        
        @property
        def url(self):
            return self._url


    class ReqResponse(BaseHttpResponse):
        def __init__(self, request, response):
            self.req = request
            self.resp = response

            if not isinstance(response, Exception):
                self.body = self.resp.text

        @property
        def request(self):
            return self.req

        @property
        def response(self):
            return self.resp 


    class RequestsDownloader(BaseDownloader):

        def get(self, requests):
            responses = []
            for request in iterator(requests):
                response = self._fetch(request)
                responses.append(response)
            return responses

        def _fetch(self, request):
            try:
                res = requestslib.get(request.url)
                return ReqResponse(request, res)
            except Exception as e:
                print('Exception on %s: %s', request, e)
                return BaseDownloadException(request, exception=e)


    if __name__ == '__main__':
        from pomp.core.base import BaseCrawler
        from pomp.core.engine import Pomp

        class Crawler(BaseCrawler):
            ENTRY_REQUESTS = ReqRequest('http://python.org/news/')

            def extract_items(self, response):
                print(response.body)

            def next_requests(self, response):
                return None # one page crawler

        pomp = Pomp(
            downloader=RequestsDownloader(),
        )

        pomp.pump(Crawler())


Downloader middleware
---------------------

For hook request before it executed by downloader or response before it
passed to crawler in pomp exists middlewares framework.

Middleware must be subclass of :class:`base.BaseDownloaderMiddleware`.


Each request will be passed to middlewares one by one in order it will passed to
downloader.
Each response/exception will be passed to middlewares one by one in
reverse order.

For example statistic middleware::

    from pomp.core.base import BaseDownloaderMiddleware

    class StatisticMiddleware(BaseDownloaderMiddleware):
        def __init__(self):
            self.requests = self.responses = self.exceptions = 0

        def process_request(self, request):
            self.requests += 1
            return request

        def process_response(self, response):
            self.responses += 1
            return response

        def process_exception(self, exception):
            self.exceptions += 1
            return exception


.. _requests: http://docs.python-requests.org/
