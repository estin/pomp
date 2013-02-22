"""
Twisted
```````

Simple downloaders and middlewares for fetching urls by Twisted.
"""


import logging
import defer as dfr

from pomp.core.base import BaseDownloader, BaseHttpRequest, \
    BaseHttpResponse
from pomp.core.utils import iterator

from twisted.internet import defer, protocol
from twisted.web.client import Agent
from twisted.web.iweb import IBodyProducer
from zope.interface import implements
from twisted.web.http_headers import Headers
import urllib


log = logging.getLogger('pomp.contrib.twisted')


class TwistedDownloader(BaseDownloader):

    def __init__(self, reactor, middlewares=None):
        super(TwistedDownloader, self).__init__(middlewares=middlewares)
        self.reactor = reactor
        self.agent = Agent(self.reactor)

    def get(self, requests):
        responses = []
        for request in iterator(requests):
            response = self._fetch(request)
            responses.append(response)
        return responses

    def _fetch(self, request):
        d = self.agent.request(
            request.method,
            request.url,
            request.headers,
            request.data
        )

        d.addCallback(self._handle_response)

        res = dfr.Deferred()

        # connect twised with pomp engine
        # TODO error_backs
        def _fire(response):
            res.callback(TwistedHttpResponse(request, response))
        d.addCallback(_fire)

        return res

    def _handle_response(self, response):
        if response.code == 204:
            d = defer.succeed('')
        else:
            d = defer.Deferred()
            response.deliverBody(SimpleReceiver(d))
        return d


class TwistedHttpRequest(BaseHttpRequest):

    def __init__(self, url, data=None, headers=None, method='GET'):
        self._url = url.encode('utf-8')
        self.data = StringProducer(urllib.urlencode(data)) if data else None
        self.headers = Headers(headers)
        self.method = method

    @property
    def url(self):
        return self._url


class TwistedHttpResponse(BaseHttpResponse):

    def __init__(self, request, response):
        self.req = request
        self.resp = response

        if not isinstance(response, Exception):
            self.body = self.resp

    @property
    def request(self):
        return self.req

    @property
    def response(self):
        return self.resp 


class SimpleReceiver(protocol.Protocol):

    def __init__(s, d):
        s.buf = ''; s.d = d

    def dataReceived(s, data):
        s.buf += data

    def connectionLost(s, reason):
        # TODO: test if reason is twisted.web.client.ResponseDone, if not, do an errback
        s.d.callback(s.buf) 


class StringProducer(object):
    implements(IBodyProducer)

    def __init__(self, body):
        self.body = body
        self.length = len(body)

    def startProducing(self, consumer):
        consumer.write(self.body)
        return defer.succeed(None)

    def pauseProducing(self):
        pass

    def stopProducing(self):
        pass
