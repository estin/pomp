# -*- coding: utf-8 -*-
"""
    Crawler queue
"""
import os
import sys
import time
import logging

try:
    import Queue as queue
except ImportError:
    import queue

from pomp.core.base import BaseQueue, BaseCrawler
from pomp.core.engine import Pomp
from pomp.core.item import Item, Field
from pomp.contrib.urllibtools import UrllibDownloader as dnl


logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
log = logging.getLogger(__name__)


class ParsedItem(Item):
    worker = Field()
    response = Field()

    def __str__(self):
        return '<ParsedItem by {s.worker} from {s.response.request}>'.format(
            s=self
        )


class WrappedQueue(BaseQueue):

    def __init__(self, source_queue, stop_event):
        self.pid = os.getpid()
        self.source_queue = source_queue
        self.stop_event = stop_event
        log.debug('Queue INITED <%s> on worker: %s', self, self.pid)

    def get_requests(self):
        while True:
            try:
                res = self.source_queue.get(block=False)
            except queue.Empty:
                if self.stop_event.is_set():
                    return None
                time.sleep(0.5)
            else:
                log.debug('Queue GET <%s> on worker: %s', res, self.pid)
                return res

    def put_requests(self, request):
        log.debug('Queue PUT <%s> on worker: %s', request, self.pid)
        self.source_queue.put(request)


class Crawler(BaseCrawler):

    def extract_items(self, response):
        item = ParsedItem(worker=os.getpid(), response=response)
        log.debug('ITEM - %s', item)
        yield item


def crawler_worker(crawler_class, source_queue, stop_event):
    pid = os.getpid()
    log.debug('Start crawler worker: %s', pid)
    pomp = Pomp(
        downloader=dnl(timeout=3),
        pipelines=[],
        queue=WrappedQueue(source_queue, stop_event),
    )
    pomp.pump(crawler_class())
    log.debug('Stop crawler worker: %s', pid)
    return True


def populate_worker(source_queue, stop_event):
    pid = os.getpid()
    log.debug('Start populate worker: %s', pid)
    que = WrappedQueue(source_queue, stop_event)

    for url in ['http://ya.ru/', 'http://google.com/', ]:
        log.debug('wait')
        time.sleep(3)
        que.put_requests(url)

    # stop crawler workers
    stop_event.set()

    log.debug('Stop populate worker: %s', pid)
    return True


if __name__ == '__main__':
    import multiprocessing

    manager = multiprocessing.Manager()
    pool = multiprocessing.Pool(processes=3)
    que = manager.Queue()
    stop_event = manager.Event()

    # start crawlers
    for i in range(2):
        w = pool.apply_async(crawler_worker, (Crawler, que, stop_event))

    # start queue populate worker
    pool.apply_async(populate_worker, (que, stop_event))

    pool.close()
    pool.join()
