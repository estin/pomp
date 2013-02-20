"""
Engine
"""
import logging
import itertools
from pomp.core.utils import iterator


log = logging.getLogger('pomp.engine')


class Pomp(object):
    """Configuration object

    Main goal of class is to glue together all parts of application:

    - Downloader implementation with middlewares
    - Item pipelines
    - Crawler
    
    :param downloader: :class:`pomp.core.base.BaseDownloader`
    :param pipelines: list of item pipelines :class:`pomp.core.base.BasePipeline`
    """

    def __init__(self, downloader, pipelines=None):

        self.downloader = downloader
        self.pipelines = pipelines or tuple()

    def response_callback(self, crawler, response):

        log.info('Process %s', response)
        items = crawler.process(response)


        if items:
            for pipe in self.pipelines:
                items = filter(None, list(
                    map(lambda i: pipe.process(crawler, i), items)
                ))

        urls = crawler.next_url(response)
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
        """Start crawling
        
        :param crawler: crawler to execute :class:`pomp.core.base.BaseCrawler`
        """

        log.info('Prepare downloader: %s', self.downloader)
        self.downloader.prepare()

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
                while True:
                    if not next_urls:
                        break
                    _urls = ()
                    for urls in next_urls:
                        if not urls:
                            continue
                        _urls = itertools.chain(
                            _urls,
                            self.downloader.process(
                                iterator(urls),
                                self.response_callback,
                                crawler
                            )
                        )
                    next_urls = _urls

        finally:

            for pipe in self.pipelines:
                log.info('Stop pipe: %s', pipe)
                pipe.stop() 


        log.info('Stop crawler: %s', crawler)
