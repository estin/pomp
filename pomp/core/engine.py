"""
Engine
"""
import logging
import itertools
from pomp.core.utils import iterator


log = logging.getLogger('pomp.engine')


class Pomp(object):

    def __init__(self, downloader, pipelines=None):

        self.downloader = downloader
        self.pipelines = pipelines or tuple()

    def response_callback(self, crawler, url, page):

        log.info('Process %s', url)
        items = crawler.process(url, page)

        if items:
            for pipe in self.pipelines:
                items = filter(None, map(pipe.process, items))

                # launch items pipelinse process
                items = list(items)

        urls = crawler.next_url(page)
        if crawler.is_depth_first:
            if urls:
                self.downloader.process(
                    iterator(urls),
                    self.response_callback,
                    crawler
                )
            return None # end of recursion
        else:
            return urls

    def pump(self, crawler):

        log.info('Start crawler: %s', crawler)

        for pipe in self.pipelines:
            log.info('Start pipe: %s', pipe)
            pipe.start()

        try:
            next_urls = self.downloader.process(
                iterator(crawler.ENTRY_URL),
                self.response_callback,
                crawler
            )

            if not crawler.is_depth_first:
                for urls in next_urls:
                    next_urls = itertools.chain(
                        next_urls,
                        self.downloader.process(
                            iterator(urls),
                            self.response_callback,
                            crawler
                        )
                    )

        finally:

            for pipe in self.pipelines:
                log.info('Stop pipe: %s', pipe)
                pipe.stop() 


        log.info('Stop crawler: %s', crawler)
