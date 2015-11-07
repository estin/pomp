import logging
import asyncio


try:
    from asyncio import ensure_future
except ImportError:
    from asyncio import async as ensure_future


from pomp.core.base import BaseQueue
from pomp.core.utils import iterator
from pomp.core.engine import StopCommand
from pomp.core.engine import Pomp as SyncPomp


log = logging.getLogger(__name__)


class SimpleAsyncioQueue(BaseQueue):

    def __init__(self, use_lifo=False):
        self.q = asyncio.Queue() if use_lifo else asyncio.LifoQueue()

    @asyncio.coroutine
    def get_requests(self):
        return (yield from self.q.get())

    def put_requests(self, requests):
        return ensure_future(self.q.put(requests))


class AioPomp(SyncPomp):
    DEFAULT_QUEUE_CLASS = SimpleAsyncioQueue

    @asyncio.coroutine
    def pump(self, crawler):
        """Start crawling

        :param crawler: isntance of :class:`pomp.core.base.BaseCrawler`
        """
        self.prepare(crawler)
        while True:

            # do not fetch from queue request more than downloader can process
            if self.queue_semaphore:
                yield from self.queue_semaphore.acquire()

            next_requests = yield from self.queue.get_requests()

            if isinstance(next_requests, StopCommand):
                self.stop = True
                break
            else:
                self.process_requests(
                    iterator(next_requests), crawler,
                )
        self.finish(crawler)

    def get_queue_semaphore(self):
        workers_count = self.downloader.get_workers_count()
        if workers_count > 1:
            return asyncio.BoundedSemaphore(workers_count)
