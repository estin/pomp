Pomp
====

Pomp is a screen scraping and web crawling framework. Like `Scrapy`_, but more simple.

Inspired by `Scrapy`_ but simpler implementation and without hard `Twisted`_ dependency.

Features:

* pure python
* one dependency only for python2.x - `concurrent.futures`_ (backport
  package for python2.x)
* one file applications, without project layouts and others restrictions
* meta framework like `Paste`_ (a framework for scrapping frameworks)
* extendible networking, may be used any sync or async methods
* without parsing libraries in the core, use you favorites
* can be distributed, designed to use an external queue

Do not care about:

* redirects
* proxies
* caching
* database integration
* cookies
* authentication
* etc.

If you want some proxies, redirects or others stuff implement it by our
self or use great library - `requests`_ as Pomp downloader.

`Pomp examples`_

`Pomp docs`_

Continuous integration status by drone.io:

.. image:: https://drone.io/bitbucket.org/estin/pomp/status.png
    :target: https://drone.io/bitbucket.org/estin/pomp/latest
    :alt: Latest CI test

.. image:: https://landscape.io/github/estin/pomp/master/landscape.svg?style=flat
    :target: https://landscape.io/github/estin/pomp/master
    :alt: Code Health


PyPI status:

.. image:: https://img.shields.io/pypi/v/pomp.png
    :target: https://pypi.python.org/pypi/pomp/
    :alt: Latest PyPI version

.. image:: https://img.shields.io/pypi/dm/pomp.png
    :target: https://pypi.python.org/pypi/pomp/
    :alt: Number of PyPI downloads

.. image:: https://img.shields.io/pypi/wheel/pomp.png
    :target: https://pypi.python.org/pypi/pomp/
    :alt: Have wheel

.. image:: https://img.shields.io/pypi/l/pomp.png
    :target: https://pypi.python.org/pypi/pomp/
    :alt: License

Docs status:

.. image:: https://readthedocs.org/projects/pomp/badge/?version=latest
    :target: https://readthedocs.org/projects/pomp/?badge=latest
    :alt: Documentation Status

Pomp is written and maintained by Evgeniy Tatarkin and is licensed under BSD license.

.. _Scrapy: http://scrapy.org/
.. _Twisted: http://twistedmatrix.com/
.. _concurrent.futures: http://pythonhosted.org/futures/
.. _Pomp examples:
   https://bitbucket.org/estin/pomp/src/tip/examples?at=default
.. _Pomp docs: http://pomp.readthedocs.org
.. _Paste: http://pythonpaste.org/
.. _requests: http://www.python-requests.org/en/latest/
