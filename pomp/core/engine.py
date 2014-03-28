"""
Engine
"""
import types
import logging

import defer

from pomp.core.utils import iterator, DeferredList


log = logging.getLogger('pomp.engine')


def filter_requests(requests):
    return filter(
        lambda x: True if x else False,
        iterator(requests)
    )


class Pomp(object):
    """Configuration object

    Main goal of class is to glue together all parts of application:

    - Downloader implementation with middlewares
    - Item pipelines
    - Crawler

    :param downloader: :class:`pomp.core.base.BaseDownloader`
    :param pipelines: list of item pipelines
                      :class:`pomp.core.base.BasePipeline`
    :param queue: instance of :class:`pomp.core.base.BaseQueue`
    """

    def __init__(self, downloader, pipelines=None, queue=None):
        self.downloader = downloader
        self.pipelines = pipelines or tuple()
        self.queue = queue

    def response_callback(self, crawler, response):

        log.info('Process %s', response)
        items = crawler.process(response)

        # pipe items
        for pipe in self.pipelines:
            items = filter(
                None,
                [pipe.process(crawler, i) for i in items],
            )

        # get next requests
        next_requests = crawler.next_requests(response)

        if self.queue:
            return next_requests  # return requests to pass through queue
        else:  # execute requests by `witdh first` or `depth first` methods
            if crawler.is_depth_first():
                if next_requests:

                    # next recursion step
                    next_requests = self.downloader.process(
                        iterator(next_requests),
                        self.response_callback,
                        crawler
                    )

                    self._sync_or_async(
                        next_requests,
                        crawler,
                        self._on_next_requests
                    )
                else:
                    if not self.stoped and not crawler.in_process():
                        self._stop(crawler)

                return None  # end of recursion
            else:
                return next_requests

    def pump(self, crawler):
        """Start crawling

        :param crawler: crawler to execute :class:`pomp.core.base.BaseCrawler`
        """
        log.info('Prepare downloader: %s', self.downloader)
        self.downloader.prepare()

        self.stoped = False
        crawler._reset_state()

        log.info('Start crawler: %s', crawler)

        for pipe in self.pipelines:
            log.info('Start pipe: %s', pipe)
            pipe.start(crawler)

        self.stop_deferred = defer.Deferred()

        next_requests = getattr(crawler, 'ENTRY_REQUESTS', None)

        # process ENTRY_REQUESTS
        if next_requests:
            next_requests = self.downloader.process(
                iterator(crawler.ENTRY_REQUESTS),
                self.response_callback,
                crawler
            )

        if self.queue:
            if not next_requests:
                # empty request - get it from queue
                next_requests = self._queue_get_requests()

            self._sync_or_async(
                next_requests,
                crawler,
                self._on_next_requests
            )
        else:  # recursive process
            if not crawler.is_depth_first():
                self._sync_or_async(
                    next_requests,
                    crawler,
                    self._on_next_requests
                )
            else:
                # is width first method
                # execute generator
                if isinstance(next_requests, types.GeneratorType):
                    list(next_requests)  # fire generator
        return self.stop_deferred

    def _sync_or_async(self, next_requests, crawler, callback):
        d = DeferredList([r for r in filter_requests(next_requests)])
        d.add_callback(callback, crawler)
        return d

    def _do(self, requests, crawler):
        # execute request by downloader
        for req in filter_requests(requests):
            _requests = self.downloader.process(
                iterator(req),
                self.response_callback,
                crawler
            )
            self._sync_or_async(
                _requests,
                crawler,
                self._on_next_requests
            )

    def _on_next_requests(self, next_requests, crawler):
        if self.queue:
            # if queue then all request must pass through it
            # first put request to queue for others crawler nodes
            for requests in filter_requests(next_requests):
                filtered = list(filter_requests(requests))  # fire
                if filtered:
                    self.queue.put_requests(filtered)

            # others crawler nodes will get request from common queue
            # pass

            # now get from queue
            try:
                next_requests = self.queue.get_requests()
            except Exception:
                log.exception('On get requests from %s', self.queue)
                raise

            reason = 'queue is empty'
            if isinstance(next_requests, defer.Deferred):
                next_requests.add_callback(self._check_stop, crawler, reason)
            else:
                self._check_stop(next_requests, crawler, reason)
            self._sync_or_async(next_requests, crawler, self._do)
        else:
            # execute recursive
            self._do(next_requests, crawler)
            self._check_stop(None, crawler, 'recursion ended')

    def _check_stop(self, request, crawler, reason):
        if not self.stoped and not request and not crawler.in_process():
            log.info('STOP by reason: %s', reason)
            self._stop(crawler)
        return request

    def _stop(self, crawler):
        self.stoped = True
        for pipe in self.pipelines:
            log.info('Stop pipe: %s', pipe)
            pipe.stop(crawler)

        log.info('Stop crawler: %s', crawler)
        self.stop_deferred.callback(None)
