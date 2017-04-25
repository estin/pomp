import sys
import types  # noqa
import logging
import asyncio
import inspect
from functools import partial


try:
    from asyncio import ensure_future
except ImportError:  # pragma: no cover
    from asyncio import async as ensure_future  # noqa


from pomp.core.base import (  # noqa
    BaseQueue,
    BaseRequest,
    BaseResponse,
    BaseHttpResponse,
    BaseCrawlException,
)
from pomp.core.utils import iterator, switch_to_asyncio  # noqa
from pomp.core.engine import StopCommand
from pomp.core.engine import Pomp as SyncPomp

from pomp.contrib.concurrenttools import (
    _run_crawler_worker, ConcurrentCrawler,
)


async def _co(value):
    if inspect.iscoroutine(value):
        return await value
    return value


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
        await self.prepare(crawler)

        # add ENTRY_REQUESTS to the queue
        next_requests = getattr(crawler, 'ENTRY_REQUESTS', None)
        if next_requests:
            await self._put_requests(iterator(next_requests))

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

        await self.finish(crawler)

    # some kind of python magic
    # read SyncPomp.* sources, add async/await/adapters by `# asyncio: `
    # directive and inject to this class as native methods
    exec('\n'.join(switch_to_asyncio(SyncPomp.prepare)))
    exec('\n'.join(switch_to_asyncio(SyncPomp.process_requests)))
    exec('\n'.join(switch_to_asyncio(SyncPomp.response_callback)))
    exec('\n'.join(switch_to_asyncio(SyncPomp.on_response)))
    exec('\n'.join(switch_to_asyncio(SyncPomp.on_parse_result)))
    exec('\n'.join(switch_to_asyncio(SyncPomp._request_done)))
    exec('\n'.join(switch_to_asyncio(SyncPomp._process_items)))
    exec('\n'.join(switch_to_asyncio(SyncPomp._put_requests)))
    exec('\n'.join(switch_to_asyncio(SyncPomp._req_middlewares)))
    exec('\n'.join(switch_to_asyncio(SyncPomp._resp_middlewares)))
    exec('\n'.join(switch_to_asyncio(SyncPomp._exception_middlewares)))
    exec('\n'.join(switch_to_asyncio(SyncPomp.finish)))


class AioConcurrentCrawler(ConcurrentCrawler):

    async def process(self, response):
        try:
            return await asyncio.get_event_loop().run_in_executor(
                self.executor,
                _run_crawler_worker,
                self.worker_params,
                response,
            )
        except Exception as e:
            log.exception('Exception on %s', response)
            return BaseCrawlException(
                response=response,
                exception=e,
                exc_info=sys.exc_info(),
            )
