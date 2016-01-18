# -*- coding: utf-8 -*-
import csv
import codecs
import logging
from nose.tools import assert_equal
from pomp.contrib.item import Item, Field
from pomp.contrib.pipelines import CsvPipeline


logging.basicConfig(level=logging.DEBUG)


class DummyItem(Item):
    field1 = Field()
    field2 = Field()
    field3 = Field()
    field4 = Field()


class TestContribPipelines(object):

    def test_csv_pipeline(self):

        def _process(csvfile):
            pipe = CsvPipeline(
                csvfile,
                delimiter=';',
                quotechar='"',
                quoting=csv.QUOTE_MINIMAL
            )

            # prepare pipe
            pipe.start(None)

            item = DummyItem(field4='f4')
            item.field1 = 'f1'
            item.field2 = 'f2'

            # pipeline item
            pipe.process(None, item)

            # close files
            pipe.stop(None)

        # open file and init pipe
        with codecs.open('test_pipe.csv', 'w', encoding='utf-8') as csvfile:

            _process(csvfile)

            # check content
            csvfile.flush()
            with open(csvfile.name, 'r') as csvres:
                res = csvres.read()
                assert_equal(res.strip(), 'f1;f2;;f4')

        # init pipe by filepath
        _process('test_pipe2.csv')
        with open('test_pipe2.csv', 'r') as csvres:
            res = csvres.read()
            assert_equal(res.strip(), 'f1;f2;;f4')
