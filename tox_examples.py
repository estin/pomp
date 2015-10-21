#!/usr/bin/env python
# coding: utf-8
import os
import sys
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO


FOR_TESTING = (
    './docs/examples/minimalapp.py',
    './docs/examples/customdowloader.py',
    './examples/e01_pythonnews.py',
    './examples/e02_dmoz.py',
    './examples/e03_queue.py',
)


if sys.version_info >= (3, 3):
    sys.path.append(
        os.path.join(os.path.dirname(__file__), 'examples')
    )
    FOR_TESTING += (
        './examples/e04_aiohttp.py',
    )


class Capturing(list):
    # http://stackoverflow.com/a/16571630/258194

    def __enter__(self):
        self._stdout = sys.stdout
        sys.stdout = self._stringio = StringIO()
        return self

    def __exit__(self, *args):
        self.extend(self._stringio.getvalue().splitlines())
        sys.stdout = self._stdout


for f in FOR_TESTING:
    print(f)
    with Capturing() as output:
        with open(f) as code:
            exec(code.read())
