import time
import json
import logging
import multiprocessing
from wsgiref.util import setup_testing_defaults
from wsgiref.simple_server import make_server


logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger('mockserver')


# TODO silent server
def simple_app(environ, start_response):
    setup_testing_defaults(environ)

    status = '200 OK'
    headers = [('Content-type', 'text/plain')]

    start_response(status, headers)

    ret = ["%s: %s\n" % (key, value)
           for key, value in environ.iteritems()]
    return ret


def sitemap_app(environ, start_response):
    #setup_testing_defaults(environ)

    status = '200 OK'
    headers = [('Content-type', 'text/plain')]

    start_response(status, headers)

    requested_url = environ['PATH_INFO']
    if requested_url == '/sleep':
        time.sleep(2)
        response = 'Done'
    else:
        response = sitemap_app.sitemap.get(requested_url)
    log.debug('Requested url: %s, response: %s', requested_url, response)
    ret = [response.encode('utf-8')]
    return ret 


def make_reponse_body(items, links):
    return json.dumps({
        'items': items,
        'links': links,
    })


def make_sitemap(level=3, links_on_page=3, sitemap=None, entry='/root'):
    sitemap = sitemap if sitemap else {}
    if level == 0:
        return sitemap

    def make_entry(url, sitemap, links_on_page):
        sitemap.update({
            url: make_reponse_body(
                ['a', 'b'],
                ['%s/%s' % (url, i) for i in range(0, links_on_page)],
            )
        })

    for lev in range(0, level):
        make_entry(entry, sitemap, links_on_page)
        for child in range(0, links_on_page):
            child_url = '%s/%s' % (entry, child)
            make_entry(child_url, sitemap, links_on_page if level > 1 else 0)
            make_sitemap(level=level - 1, sitemap=sitemap, entry=child_url)
            
    return sitemap


class HttpServer(object):

    def __init__(self, host='localhost', port=8001, app=None, sitemap=None):
        app = app or sitemap_app
        self.sitemap = sitemap or {}

        # inject sitemap to app
        app.sitemap = self.sitemap

        self.host, self.port = host, port
        self.location = 'http://%s:%s' % (self.host, self.port)

        self.httpd = make_server(host, port, app)
        self.process = multiprocessing \
            .Process(target=self.httpd.serve_forever)

    def start(self):
        log.debug('Start http server: %s', self)
        self.process.start()
    
    def stop(self):
        log.debug('Stop http server: %s', self)
        self.process.terminate()
        self.process.join()
        self.httpd.server_close()
