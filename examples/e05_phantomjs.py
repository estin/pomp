"""
Integration with phantomjs
requires: selenium, lxml
"""
import os
import sys
import time
import signal
import logging
import collections


try:
    from urlparse import urljoin
except ImportError:
    from urllib.parse import urljoin

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

from pomp.core.base import (
    BaseHttpRequest, BaseHttpResponse, BaseDownloadWorker,
    BaseCrawler,
)
from pomp.contrib.concurrenttools import ConcurrentDownloader
from pomp.core.item import Item, Field


logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
log = logging.getLogger(__name__)


class PhantomRequest(BaseHttpRequest):
    def __init__(self, url, level=None):
        self._url = url
        self.level = level or 0

    @property
    def url(self):
        return self._url

    def __str__(self):
        return '<{s.__class__.__name__} level:{s.level} url:{s.url} ' \
            'wdriver: {s.driver_url}>'.format(s=self)


class PhantomResponse(BaseHttpResponse):
    def __init__(self, request, body):
        self.req = request
        self.body = body

    @property
    def request(self):
        return self.req

    @property
    def response(self):
        raise self.body


class PhantomDownloadWorker(BaseDownloadWorker):
    def __init__(self):
        self.pid = os.getpid()

    def get_one(self, request):
        # attach webdriver to already started phanomjs node
        driver = webdriver.Remote(
            command_executor=request.driver_url,
            desired_capabilities=DesiredCapabilities.PHANTOMJS,
        )
        log.debug("[PhantomWorker:%s] Start %s", self.pid, request)

        # start
        driver.get(request.url)

        # allow phantomjs evaluate javascript and render `also likes`
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    '//div[@class="RelatedUsers-users"]//a[contains(@class, "js-user-profile-link")]'  # noqa
                )
            )
        )

        # scroll down 3 times to load older tweets
        for i in range(0, 3):
            driver.execute_script(
                "window.document.body.scrollTop = document.body.scrollHeight;"
            )
            # wait and allow new content to load
            time.sleep(1)

        # finish - get current document body
        body = driver.execute_script("return document.documentElement.outerHTML;")  # noqa
        log.debug("[PhantomWorker:%s] Finish %s", self.pid, request)
        driver.close()
        return PhantomResponse(request, body)


class PhantomDownloader(ConcurrentDownloader):

    def prepare(self, *args, **kwargs):
        super(PhantomDownloader, self).prepare(*args, **kwargs)

        # start phanomjs nodes
        self.drivers = collections.deque([
            webdriver.PhantomJS() for i in range(self.pool_size)
        ])

    def get(self, requests):
        # associate each request with phantomjs node
        for request in requests:
            request.driver_url = self.drivers[0].command_executor._url
            log.debug("Associated request %s", request)
            self.drivers.rotate(1)

        return super(PhantomDownloader, self).get(requests)

    def stop(self):
        super(PhantomDownloader, self).stop()
        log.debug("close all phantomjs nodes")
        for driver in self.drivers:
            pid = driver.service.process.pid
            # driver.close()
            # driver.quit()
            # HACK - phantomjs does not exited after close and quit
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass


class Tw(Item):

    author = Field()
    body = Field()
    likes = Field()

    def __str__(self):
        return u'{s.author} likes: {s.likes}\nbody: {s.body}'.format(s=self)


class TwitterSpider(BaseCrawler):
    BASE_URL = 'https://twitter.com/'

    ENTRY_REQUESTS = PhantomRequest(urljoin(
        BASE_URL, 'gvanrossum'
    ))

    TWEETS_XPATH = '//ol[@id="stream-items-id"]/li'
    AUTHOR_XPATH = './/strong[contains(@class, "fullname")]/text()'
    BODY_XPATH = './/p[contains(@class, "tweet-text")]'
    LIKES_XPATH = './/span[@class="ProfileTweet-actionCountForPresentation"]/text()'  # noqa

    ALSO_LIKES_LINKS_XPATH = '//div[@class="RelatedUsers-users"]' \
        '//a[contains(@class, "js-user-profile-link")]/@href'

    def __init__(self):
        self._parsed_also_likes = []

    def extract_items(self, response):
        # extract items
        for i in response.tree.xpath(self.TWEETS_XPATH):
            tw = Tw()
            try:
                tw.author = i.xpath(self.AUTHOR_XPATH)[0]
                tw.body = i.xpath(self.BODY_XPATH)[0].text_content()
                tw.likes = i.xpath(self.LIKES_XPATH)[0]
            except IndexError:
                log.exception("Something wrong in xpath processing")
                continue
            yield tw

        # go to also likes users
        self._parsed_also_likes.append(response.request.url)
        level = getattr(response.request, 'level', 0)
        # do not go deeper then 3 level
        if level < 3:
            # follow to the first two persons from `also likes`
            for href in response.tree.xpath(self.ALSO_LIKES_LINKS_XPATH)[:2]:
                # do not repeat requests
                url = urljoin(self.BASE_URL, href)
                if url not in self._parsed_also_likes:
                    yield PhantomRequest(url, level=level + 1)


if __name__ == '__main__':
    from pomp.core.engine import Pomp
    from e02_dmoz import (
        PrintPipeline, LXMLDownloaderMiddleware, StatisticMiddleware,
    )

    statistics = StatisticMiddleware()
    pomp = Pomp(
        downloader=PhantomDownloader(
            pool_size=2,
            worker_class=PhantomDownloadWorker,
            middlewares=(
                statistics,
                LXMLDownloaderMiddleware(),
            ),
        ),
        pipelines=[PrintPipeline()],
    )
    pomp.pump(TwitterSpider())
    print("Statistics:\n %s" % statistics)
