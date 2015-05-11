Pomp
====

Pomp is a screen scraping and web crawling framework. Like `Scrapy`_, but more simple.

Inspired by `Scrapy`_ but simpler implementation and without hard `Twisted`_ dependency.

Features:

* one file applications
* networking by choice

 - `urllib`_
 - `Twisted`_ by package only for py2.x
 - `concurrent.futures`_ standard for py3.2+ or by backport package
 - yours own method

* content parsing by yours own method


Roadmap:

* `gevent`_ support
* `Tornado`_ support
* `GAE`_ support

`Pomp examples`_

`Pomp docs`_

Continuous integration status by drone.io:

.. image:: https://drone.io/bitbucket.org/estin/pomp/status.png
    :target: https://drone.io/bitbucket.org/estin/pomp/latest
    :alt: Latest CI test

.. image:: https://landscape.io/github/estin/pomp/master/landscape.svg?style=flat
    :target: https://landscape.io/github/estin/pomp/master
    :alt: Code Health

.. image:: https://coveralls.io/repos/estin/pomp/badge.svg
    :target: https://coveralls.io/r/estin/pomp
    :alt: Coverage

PyPI status:

.. image:: https://pypip.in/v/pomp/badge.png
    :target: https://crate.io/packages/pomp/
    :alt: Latest PyPI version

.. image:: https://pypip.in/d/pomp/badge.png
    :target: https://crate.io/packages/pomp/
    :alt: Number of PyPI downloads

.. image:: https://pypip.in/wheel/pomp/badge.svg
    :target: https://pypi.python.org/pypi/pomp/
    :alt: Have wheel

.. image:: https://pypip.in/license/pomp/badge.svg
    :target: https://pypi.python.org/pypi/pomp/
    :alt: License

Docs status:

.. image:: https://readthedocs.org/projects/pomp/badge/?version=latest
    :target: https://readthedocs.org/projects/pomp/?badge=latest
    :alt: Documentation Status

Pomp is written and maintained by Evgeniy Tatarkin and is licensed under BSD license.

.. _urllib: http://docs.python.org/3.3/library/urllib.html
.. _Scrapy: http://scrapy.org/
.. _Twisted: http://twistedmatrix.com/
.. _gevent: http://www.gevent.org/
.. _Tornado: http://www.tornadoweb.org/
.. _concurrent.futures: http://pythonhosted.org/futures/
.. _GAE: https://developers.google.com/appengine/
.. _Pomp examples:
   https://bitbucket.org/estin/pomp/src/tip/examples?at=default
.. _Pomp docs: http://pomp.readthedocs.org
