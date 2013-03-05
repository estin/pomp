"""
Twisted
```````

Simple downloaders and middlewares for fetching urls by Twisted.
"""
import urllib
import logging
import defer as dfr

from twisted.internet import defer, protocol
from twisted.web.client import Agent
from twisted.web.iweb import IBodyProducer
from zope.interface import implements
from twisted.web.http_headers import Headers 

from pomp.core.base import BaseDownloader, BaseHttpRequest, BaseHttpResponse, \
    BaseDownloadException 
from pomp.core.utils import iterator


log = logging.getLogger('pomp.contrib.twisted')


class TwistedDownloader(BaseDownloader):

    def __init__(self, reactor, timeout=5, middlewares=None):
        super(TwistedDownloader, self).__init__(middlewares=middlewares)
        self.reactor = reactor
        self.agent = Agent(self.reactor)
        self.timeout = timeout

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

        # Set timeout to request
        # on timeout will be errorBack with CancelledError
        watchdog = self.reactor.callLater(self.timeout, d.cancel)
        def _reset_timeout(res):
            if watchdog.active():
                watchdog.cancel()
            return res
        d.addBoth(_reset_timeout)

        d.addCallback(self._handle_response)

        # deferred result of tiwsted request processing
        res = dfr.Deferred()

        # connect twised with pomp engine
        def _fire(response):
            res.callback(TwistedHttpResponse(request, response))
        d.addCallback(_fire)

        # errors
        def _fire_error(failure):
            try:
                failure.raiseException()
            except Exception as e:
                log.exception('Exception on %s', request)
                res.callback(BaseDownloadException(request, exception=e))
        d.addErrback(_fire_error)

        return res

    def _handle_response(self, response):
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

    def __str__(self):
        return 'Request({0}): {1}'.format(self.method, self.url)


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
