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

`Pomp CI tests`_

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
.. _Pomp CI tests: https://drone.io/bitbucket.org/estin/pomp
