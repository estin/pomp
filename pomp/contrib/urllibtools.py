"""
Downloader and middleware implementations.

- Downloaders: Fetches data by standard `urllib.urlopen` (Python 3.x) or
  `urllib2.urlopen` (Python 2.7+)
"""
import sys
try:
    from urllib.request import urlopen, Request
except ImportError:  # pragma: no cover
    from urllib2 import urlopen, Request

import logging

from pomp.core.base import (
    BaseDownloadWorker, BaseDownloader,
    BaseHttpRequest, BaseHttpResponse, BaseMiddleware,
    BaseCrawlException,
)


log = logging.getLogger('pomp.contrib.urllib')


class UrllibDownloadWorker(BaseDownloadWorker):

    def __init__(self, timeout=None):
        self.timeout = None

    def process(self, request):
        try:
            log.info("Fetch %s %s %s", type(request), request, request.url)
            res = urlopen(request.url, timeout=self.timeout)
            return UrllibHttpResponse(request, res)
        except Exception as e:
            log.exception('Exception on %s', request)
            return BaseCrawlException(
                request,
                exception=e,
                exc_info=sys.exc_info(),
            )


class UrllibDownloader(BaseDownloader):
    """Simplest downloader

    :param timeout: request timeout in seconds
    """
    WORKER_CLASS = UrllibDownloadWorker

    def __init__(self, timeout=None):
        super(UrllibDownloader, self).__init__()
        self.worker = UrllibDownloadWorker(timeout=timeout)

    def process(self, crawler, request):
        return self.worker.process(request)


class UrllibHttpRequest(Request, BaseHttpRequest):
    """Adapter for urllib request to :class:`pomp.core.base.BaseHttpRequest`"""

    @property
    def url(self):
        return self.get_full_url()

    def __str__(self):
        return '<UrllibHttpRequest {s.url}>'.format(s=self)


class UrllibHttpResponse(BaseHttpResponse):
    """Adapter for urllib response to
    :class:`pomp.core.base.BaseHttpResponse`"""

    def __init__(self, request, response):
        self.request = request

        if not isinstance(response, Exception):
            self.body = response.read()

    def get_request(self):
        return self.request

    def __str__(self):
        return '<UrllibHttpResponse on {s.request}>'.format(s=self)


class UrllibAdapterMiddleware(BaseMiddleware):
    """Middlerware for adapting urllib.Request
    to :class:`pomp.core.base.BaseHttpRequest`
    """

    def process_request(self, req, crawler, downloader):
        return req if isinstance(req, BaseHttpRequest) \
            else UrllibHttpRequest(req)

    def process_response(self, response, crawler, downloader):
        return response
