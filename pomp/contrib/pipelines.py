# coding: utf-8
"""
Simple pipelines
"""
import csv
import codecs

try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO

from pomp.core.base import BasePipeline
from pomp.core.utils import PY3, isstring


# https://docs.python.org/2/library/csv.html#examples
class UnicodeCsvWriter:
    """
    A CSV writer that writes rows to CSV file `f` with the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        # self.writer.writerow([s.encode("utf-8") for s in row])
        self.writer.writerow([self._encode_item(s) for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):  # pragma: no cover
        for row in rows:
            self.writerow(row)

    def _encode_item(self, data):
        if isstring(data):
            return data.encode('utf-8')
        return data


class CsvPipeline(BasePipeline):
    """Save items to CSV format

    Params `*args` and `**kwargs` passed to ``csv.writer`` constuctor.

    :param output_file: Filename of file-like object or a file object. If
                        `output_file` is a file-like object, then the file will
                        remain open after the pipe is stopped.
    """

    def __init__(self, output_file, *args, **kwargs):
        self.output_file = output_file
        self._csv_args = args
        self._csv_kwargs = kwargs

        # do not close file if it not opened by this instance
        self._need_close = False

    def start(self, crawler):
        if isstring(self.output_file):
            if PY3:
                self.csvfile = codecs.open(
                    self.output_file, 'w', encoding='utf-8'
                )
            else:
                self.csvfile = open(self.output_file, 'w')
            self._need_close = True
        else:
            self.csvfile = self.output_file

        if PY3:
            self.writer = csv.writer(
                self.csvfile, *self._csv_args, **self._csv_kwargs
            )
        else:
            self.writer = UnicodeCsvWriter(
                self.csvfile, *self._csv_args, **self._csv_kwargs
            )

    def process(self, crawler, item):
        self.writer.writerow(item.values())
        return item

    def stop(self, crawler):
        if self._need_close:
            self.csvfile.close()
