import logging
import asyncio
from functools import partial


try:
    from asyncio import ensure_future
except ImportError:  # pragma: no cover
    from asyncio import async as ensure_future


from pomp.core.base import BaseQueue
from pomp.core.utils import iterator, Planned
from pomp.core.engine import StopCommand
from pomp.core.engine import Pomp as SyncPomp

from pomp.contrib.concurrenttools import (
    _run_crawler_worker, ConcurrentCrawler,
)


log = logging.getLogger(__name__)


class SimpleAsyncioQueue(BaseQueue):

    def __init__(self, use_lifo=False):
        self.q = asyncio.Queue() if use_lifo else asyncio.LifoQueue()

    @asyncio.coroutine
    def get_requests(self):
        return (yield from self.q.get())

    @asyncio.coroutine
    def put_requests(self, requests):
        yield from self.q.put(requests)


class AioPomp(SyncPomp):
    DEFAULT_QUEUE_CLASS = SimpleAsyncioQueue

    @asyncio.coroutine
    def pump(self, crawler):
        """Start crawling

        :param crawler: isntance of :class:`pomp.core.base.BaseCrawler`
        """
        self.prepare(crawler)

        # add ENTRY_REQUESTS to the queue
        next_requests = getattr(crawler, 'ENTRY_REQUESTS', None)
        if next_requests:
            yield from self._put_requests(
                iterator(next_requests), request_done=False,
            )

        while True:

            # do not fetch from queue request more than downloader can process
            if self.queue_semaphore:
                yield from self.queue_semaphore.acquire()

            next_requests = yield from self.queue.get_requests()

            if isinstance(next_requests, StopCommand):
                self.stop = True
                break
            else:
                yield from self.process_requests(
                    iterator(next_requests), crawler,
                )
        self.finish(crawler)

    @asyncio.coroutine
    def process_requests(self, requests, crawler):
        for response in self.downloader.process(requests, crawler):
            if isinstance(response, Planned):
                future = asyncio.Future()

                def _(r):
                    ensure_future(
                        self._put_requests(
                            self.response_callback(crawler, r.result())
                        )
                    ).add_done_callback(
                        future.set_result
                    )

                response.add_done_callback(_)

                yield from future
            else:
                yield from self._put_requests(
                    self.response_callback(
                        crawler, response
                    )
                )

    @asyncio.coroutine
    def _put_requests(self, requests, request_done=True):

        @asyncio.coroutine
        def _put(items):

            if items:
                for item in items:
                    self.in_progress += 1
                    yield from self.queue.put_requests(item)

            if request_done:
                yield from self._request_done()

        if isinstance(requests, Planned):
            future = asyncio.Future()

            def _(r):
                ensure_future(
                    _put(r.result())
                ).add_done_callback(
                    future.set_result
                )

            requests.add_done_callback(_)

            yield from future
        else:
            yield from _put(requests)

    @asyncio.coroutine
    def _request_done(self):
        if self.queue_semaphore:
            self.queue_semaphore.release()

        self.in_progress -= 1
        if self.in_progress == 0:
            # work done
            yield from self.queue.put_requests(StopCommand())

    def get_queue_semaphore(self):
        workers_count = self.downloader.get_workers_count()
        if workers_count > 1:
            return asyncio.BoundedSemaphore(workers_count)


class AioConcurrentCrawler(ConcurrentCrawler):

    def process(self, response):

        # build Planned object
        done_future = Planned()

        # fire done_future when asyncio finish response processing by
        # crawler worker in executor
        asyncio.ensure_future(
            asyncio.get_event_loop().run_in_executor(
                self.executor,
                _run_crawler_worker,
                self.worker_params,
                response,
            )
        ).add_done_callback(
            partial(self._done, response, done_future)
        )

        return done_future
