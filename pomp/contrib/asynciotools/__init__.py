import sys  # noqa
import logging
import asyncio
from functools import partial


try:
    from asyncio import ensure_future
except ImportError:  # pragma: no cover
    from asyncio import async as ensure_future  # noqa


from pomp.core.base import BaseQueue, BaseCrawlException  # noqa
from pomp.core.utils import iterator, switch_to_asyncio, Planned
from pomp.core.engine import StopCommand
from pomp.core.engine import Pomp as SyncPomp

from pomp.contrib.concurrenttools import (
    _run_crawler_worker, ConcurrentCrawler,
)


log = logging.getLogger(__name__)


class SimpleAsyncioQueue(BaseQueue):

    def __init__(self, use_lifo=False):
        self.q = asyncio.Queue() if use_lifo else asyncio.LifoQueue()

    async def get_requests(self, count=None):
        return await self.q.get()

    async def put_requests(self, requests):
        await self.q.put(requests)


class AioPomp(SyncPomp):
    DEFAULT_QUEUE_CLASS = SimpleAsyncioQueue
    LOCK_FACTORY = asyncio.Lock

    async def pump(self, crawler):
        """Start crawling

        :param crawler: isntance of :class:`pomp.core.base.BaseCrawler`
        """
        self.prepare(crawler)

        # add ENTRY_REQUESTS to the queue
        next_requests = getattr(crawler, 'ENTRY_REQUESTS', None)
        if next_requests:
            await self._put_requests(
                iterator(next_requests), request_done=False,
            )

        _pending_iteration_tasks = []

        def _on_iterations_task_done(task, future):
            _pending_iteration_tasks.remove(task)

        while True:

            if self.queue_lock and self.queue_semaphore_value <= 0:
                await self.queue_lock.acquire()

            next_requests = await self.queue.get_requests(
                count=self.queue_semaphore_value
            )

            if isinstance(next_requests, StopCommand):
                break

            # process requests and do not block loop
            task = asyncio.ensure_future(
                self.process_requests(
                    iterator(next_requests), crawler,
                )
            )
            _pending_iteration_tasks.append(task)
            task.add_done_callback(
                partial(_on_iterations_task_done, task)
            )

        # loop ended, but we have pending tasks - wait
        if _pending_iteration_tasks:
            log.debug(
                "Wait pending iteration tasks: %s",
                len(_pending_iteration_tasks),
            )
            await asyncio.wait(_pending_iteration_tasks)

        self.finish(crawler)

    # some kind of python magic
    # read SyncPomp.* sources, add async/await/adapters by `# asyncio: `
    # directive and inject to this class as native methods
    exec('\n'.join(switch_to_asyncio(SyncPomp.process_requests)))
    exec('\n'.join(switch_to_asyncio(SyncPomp._put_requests)))
    exec('\n'.join(switch_to_asyncio(SyncPomp._request_done)))


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
