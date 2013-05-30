# -*- coding: utf-8 -*-
"""
    LiveJournal friends of http://grrm.livejournal.com/ user

    requires: lxml

    store csv data to /tmp/friends.csv
    print result dict

"""
import sys
import logging
import pprint
from collections import defaultdict

from lxml import html

from pomp.core.base import BaseCrawler
from pomp.contrib.pipelines import CsvPipeline
from pomp.core.base import BasePipeline, BaseDownloaderMiddleware
from pomp.contrib import UrllibHttpRequest
from pomp.core.item import Item, Field


logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)


class LXMLDownloaderMiddleware(BaseDownloaderMiddleware):

    def __init__(self, encoding=None):
        self.encoding = encoding

    def process_request(self, request):
        return request

    def process_response(self, response):
        if self.encoding:
            response.tree = html.fromstring(
                response.body.decode(self.encoding))
        else:
            response.tree = html.fromstring(response.body)
        return response


class DictCollectPipeline(BasePipeline):

    def start(self, crawler):
        self.result = defaultdict(lambda: {'friends': []})

    def process(self, crawler, item):
        self.result[item.friend_to]['friends'].append(item.username)
        return item


class FriendItem(Item):
    username = Field()
    friend_to = Field()

    def __repr__(self):
        return 'username: %s friend to:%s' % (
            self.username,
            self.friend_to,
        )


class FriendLevelRequest(UrllibHttpRequest):
    def __init__(self, *args, **kwargs):
        self.level = kwargs.get('level', 0)
        self.username = kwargs['username']
        # cleanup kwargs for passing to urllib
        if 'level' in kwargs:
            del kwargs['level']
        if 'username' in kwargs:
            del kwargs['username']
        super(FriendLevelRequest, self).__init__(*args, **kwargs)


class LJFriendSpider(BaseCrawler):
    QS = '?socconns=pfriends&mode_full_socconns=1'
    BASE_URL = 'http://{0}.livejournal.com/profile/friendlist' + QS

    ENTRY_REQUESTS = (
        FriendLevelRequest(
            BASE_URL.format('grrm'),
            username='grrm'
        ),
    )

    FRIENDS_XPATH = '//dl[contains(@data-widget-options, "socconns")]' \
                    '/dd[@class="b-profile-group-body"]' \
                    '/div[@class="b-tabs-content"]/a'

    def __init__(self, max_level=2, friends_limit=2):
        """LiveJournal spider

            :param max_level: max level dive-in
            :param friends_limit: count of first friends to follow
        """
        self.max_level = max_level
        self.friend_limit = friends_limit
        self._next_requests = []
        super(LJFriendSpider, self).__init__()

    def extract_items(self, response):
        items = []
        k = 0
        # find item section
        for i in response.tree.xpath(self.FRIENDS_XPATH):
            item = FriendItem()
            item.username = i.text

            # associate parsed user with hist friend from parent request
            item.friend_to = response.request.username
            items.append(item)

            # follow to item.username
            if response.request.level < self.max_level \
                    and k < self.friend_limit:
                # generate new url to follow
                url = i.get('href') + self.QS
                self._next_requests.append(FriendLevelRequest(
                    url,
                    username=item.username,
                    level=response.request.level + 1
                ))
                k += 1
        return items

    def next_requests(self, response):
        # when users parsed pomp call next_url method
        # for getting next targets
        def _urls():
            if self._next_requests:
                yield self._next_requests.pop()
        return list(_urls())


if __name__ == '__main__':
    from pomp.core.engine import Pomp

    try:
        from pomp.contrib.concurrenttools import ConcurrentUrllibDownloader \
            as dnl
    except ImportError:
        from pomp.contrib import ThreadedDownloader as dnl

    middlewares = [LXMLDownloaderMiddleware(encoding='utf-8')]

    dict_pipe = DictCollectPipeline()
    pomp = Pomp(
        downloader=dnl(middlewares=middlewares, timeout=10),
        pipelines=[
            dict_pipe,
            CsvPipeline('/tmp/friends.csv'),
        ],
    )

    pomp.pump(LJFriendSpider())

    print('Result:')
    pprint.pprint(dict(dict_pipe.result))
