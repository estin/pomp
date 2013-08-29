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
    :param stop_on_empty_queue: stop processing if queue is empty
    """

    def __init__(
            self, downloader, pipelines=None,
            queue=None, stop_on_empty_queue=True):

        self.downloader = downloader
        self.pipelines = pipelines or tuple()
        self.queue = queue
        self.stop_on_empty_queue = stop_on_empty_queue

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

        if self.queue:  # return request for queue get/put loop
            return next_requests
        else:  # execute requests by `witdh first` or `depth first` methods
            if crawler.is_depth_first():
                if next_requests:
                    self.downloader.process(
                        iterator(next_requests),
                        self.response_callback,
                        crawler
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
            # if ENTRY_REQUESTS produce new requests
            # put them to queue
            if next_requests:
                filtered = list(filter_requests(next_requests))  # fire
                if filtered:
                    self.queue.put_requests(filtered)

            # queue processing loop
            while True:

                # wait requests from queue
                try:
                    requests = self.queue.get_requests()
                except Exception:
                    log.exception('On get requests from %s', self.queue)
                    raise

                if self.stop_on_empty_queue and not requests:
                    log.info('Queue empty - STOP')
                    break

                # process request from queue
                next_requests = self.downloader.process(
                    iterator(requests),
                    self.response_callback,
                    crawler
                )

                # put new requests to queue
                filtered = list(filter_requests(next_requests))  # fire
                if filtered:
                    self.queue.put_requests(filtered)

        else:  # recursive process
            if not crawler.is_depth_first():
                self._call_next_requests(next_requests, crawler)
            else:
                # is width first method
                # execute generator
                if isinstance(next_requests, types.GeneratorType):
                    list(next_requests)  # fire generator
        return self.stop_deferred

    def _call_next_requests(self, next_requests, crawler):
        # separate deferred and regular requests
        # fire generator
        deferreds = []
        other = []
        for r in filter(None, next_requests):
            if isinstance(r, defer.Deferred):
                deferreds.append(r)
            else:
                other.append(r)

        if deferreds:  # async behavior
            d = DeferredList(deferreds)
            d.add_callback(self._on_next_requests, crawler)

        if other:  # sync behavior
            self._on_next_requests(other, crawler)

    def _on_next_requests(self, next_requests, crawler):
        # execute request by downloader
        for requests in filter(None, next_requests):
            _requests = self.downloader.process(
                iterator(requests),
                self.response_callback,
                crawler
            )

            self._call_next_requests(_requests, crawler)

        if not self.stoped and not crawler.in_process():
            self._stop(crawler)

    def _stop(self, crawler):
        self.stoped = True
        for pipe in self.pipelines:
            log.info('Stop pipe: %s', pipe)
            pipe.stop(crawler)

        log.info('Stop crawler: %s', crawler)
        self.stop_deferred.callback(None)
