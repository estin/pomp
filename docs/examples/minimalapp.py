import re
from pomp.core.base import BaseCrawler
from pomp.contrib.urllibtools import UrllibHttpRequest


python_sentence_re = re.compile('[\w\s]{0,}python[\s\w]{0,}', re.I | re.M)


class MyCrawler(BaseCrawler):
    """Extract all sentences with `python` word"""
    ENTRY_REQUESTS = UrllibHttpRequest('http://python.org/news')  # entry point

    def extract_items(self, response):
        for i in python_sentence_re.findall(response.body.decode('utf-8')):
            sentence = i.strip()
            print("Sentence: {}".format(sentence))
            yield sentence


if __name__ == '__main__':
    from pomp.core.engine import Pomp
    from pomp.contrib.urllibtools import UrllibDownloader

    pomp = Pomp(
        downloader=UrllibDownloader(),
    )

    pomp.pump(MyCrawler())
