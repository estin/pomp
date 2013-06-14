.. _quickstart:

Quickstart
==========

.. currentmodule:: pomp.core

Pomp is fun to use, incredibly easy for basic applications.

A Minimal Application
---------------------

For a minimal application all you need is to define you crawler 
by inherit :class:`base.BaseCrawler`


.. literalinclude:: examples/minimalapp.py



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

For example downloader fetching data by requests_ package.


.. literalinclude:: examples/customdowloader.py


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
