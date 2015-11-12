"""
Simple downloaders and middlewares for fetching data by standard
`urlopen` function from `urllib` package for python3.x
or `urllib2` for python2.7+
"""
import sys
try:
    from urllib.request import urlopen, Request
except ImportError:  # pragma: no cover
    from urllib2 import urlopen, Request

import logging

from pomp.core.base import (
    BaseDownloadWorker, BaseDownloader,
    BaseHttpRequest, BaseHttpResponse, BaseDownloaderMiddleware,
    BaseDownloadException,
)
from pomp.core.utils import iterator


log = logging.getLogger('pomp.contrib.urllib')


class UrllibDownloadWorker(BaseDownloadWorker):

    def __init__(self, timeout=5):
        self.timeout = timeout

    def get_one(self, request):
        try:
            log.info("Fetch %s %s %s", type(request), request, request.url)
            res = urlopen(request.url, timeout=self.timeout)
            return UrllibHttpResponse(request, res)
        except Exception as e:
            log.exception('Exception on %s', request)
            return BaseDownloadException(
                request,
                exception=e,
                exc_info=sys.exc_info(),
            )


class UrllibDownloader(BaseDownloader):
    """Simplest downloader

    :param timeout: request timeout in seconds
    """
    WORKER_CLASS = UrllibDownloadWorker

    def __init__(self, middlewares=None, timeout=5):
        super(UrllibDownloader, self).__init__(middlewares=middlewares)
        self.worker = UrllibDownloadWorker(timeout=timeout)

    def get(self, requests):
        for request in iterator(requests):
            yield self.worker.get_one(request)


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
        self.req = request
        # self.resp = response

        if not isinstance(response, Exception):
            self.body = response.read()

    @property
    def request(self):
        return self.req

    # @property
    # def response(self):
    #     return self.resp

    def __str__(self):
        return '<UrllibHttpResponse on {s.request}>'.format(s=self)


class UrllibAdapterMiddleware(BaseDownloaderMiddleware):
    """Middlerware for adapting urllib.Request
    to :class:`pomp.core.base.BaseHttpRequest`
    """

    def process_request(self, req):
        return req if isinstance(req, BaseHttpRequest) \
            else UrllibHttpRequest(req)

    def process_response(self, response):
        return response
