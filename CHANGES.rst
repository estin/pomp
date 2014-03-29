pomp changelog
==============

Here you can see the full list of changes between pomp releases.


Version 0.1.2
-------------

Not released yet

- twistedtools on request timeout can raise ResponseNeverReceived or
  others (see _newcleint twisted api)...
- utils.DeferredList works with deferred and not-deferred objects


Version 0.1.1
-------------

Released on December 12nd 2013

- urllib and twidted downloader on get method yield result
- bugfix `depth first` method
- concurrenttools change try/finally to generator behavior
- processing requests through queue
- better generator usage


Version 0.1.0
-------------

Released on June 14nd 2013

- rename SimpleDownloader to UrllibDownloader
- urllib code now in contrib/urllibtools.py
- ENTRY_URL renamed to ENTRY_REQUESTS
- next_url renamed to next_requests
- async support
- Twisted support
- concurrent future support
- pipelines accept crawler on start/stop/process calls
- downloader middleware also process exception


Version 0.0.2
-------------

First public preview release.
