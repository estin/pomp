Pomp
====

Pomp is a screen scraping and web crawling framework. Like `Scrapy`_, but more simple.

Inspired by `Scrapy`_ but simpler implementation and without hard `Twisted`_ dependency.

Features:

* one file applications
* networking by choice

 - `urllib`_
 - `Twisted`_ by package only for py2.x
 - `futures`_ standard for py3.2+ or by backport package
 - yours own method

* content parsing by yours own method


Roadmap:

* `gevent`_ support
* `Tornado`_ support

`Pomp examples`_

Pomp is written and maintained by Evgeniy Tatarkin and is licensed under BSD license.

.. _urllib: http://docs.python.org/3.3/library/urllib.html
.. _Scrapy: http://scrapy.org/
.. _Twisted: http://twistedmatrix.com/
.. _gevent: http://www.gevent.org/
.. _Tornado: http://www.tornadoweb.org/
.. _futures: http://pythonhosted.org/futures/
.. _Pomp examples:
   https://bitbucket.org/estin/pomp/src/tip/examples?at=default
