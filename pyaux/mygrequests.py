# coding: utf8
""" Attempt at gevent-compatible requests without any monkeypatching
(using geventhttpclient).


== Usage example ==

    # ### Basic imports / inits
    # # The wrapper that uses the session (or just use `get_session().request(…)`)
    from pyaux.base import request
    import gevent
    # # Pool (concurrency limiting)
    from gevent.pool import Pool
    pool = Pool(10)
    results = {}


=== Usage example: callback ===

    # # Need an extra wrapper that would make the globals of the
    # # callback itself (as the loop's globals change)
    def mk_callback(url):
        def callback(resp):
            results[url] = resp

        return callback

    # # Generalised way:
    def mk_callback_(__func, **env):
        def callback(*ar, **kwa):
            env.update(kwa)
            return __func(*ar, **env)

    for url in urls:
        pool.apply_async(
            request,
            args=(url,),
            kwds=dict(_return_unjson=True),
            callback=mk_callback(url),
            # # Generalised way:
            # callback = mk_callback_(
            #     (lambda resp, url: extras.__setitem__(url, resp)),
            #     url=url)
        )

    gevent.sleep()  # Uncertain
    pool.join(timeout=10)

    return results


=== Usage example: promises (greenlets) ===

    for url in urls:
        resp = pool.apply_async(
            request,
            args=(url,),
            kwds=dict(_return_unjson=True),
            callback=mk_callback(url)
        )
        results[url] = resp

    pool.join(timeout=10)

    results = {key: value.get() for key, value in results.items()}
    return results

"""

import geventhttpclient
from geventhttpclient import httplib as gehttplib
from geventhttpclient.useragent import CompatResponse

import httplib as _httplib

import requests
from requests import adapters
from requests.packages.urllib3.poolmanager import PoolManager as _PoolManager
from requests.packages.urllib3.poolmanager import SSL_KEYWORDS
# from requests.packages.urllib3.response import HTTPResponse
# from requests.packages.urllib3.exceptions import ...

from requests.packages.urllib3.connectionpool import HTTPConnectionPool, HTTPSConnectionPool
from requests.packages.urllib3.connection import HTTPConnection as _HTTPConnection
from requests.packages.urllib3.connection import HTTPSConnection as _HTTPSConnection

from .base import memoize


class GHTTPAdapter(adapters.HTTPAdapter):
    """ HTTP Adapter with overrides to use geventhttpclient """

    def init_poolmanager(self, connections, maxsize, block=adapters.DEFAULT_POOLBLOCK):
        super(GHTTPAdapter, self).init_poolmanager(connections, maxsize, block=block)
        self.poolmanager = PoolManager(
            num_pools=connections, maxsize=maxsize, block=block)


class PoolManager(_PoolManager):

    # XXX: copypasted (for the different globals)
    # TODO?: just hack the globals... somehow.
    def _new_pool(self, scheme, host, port):
        pool_cls = pool_classes_by_scheme[scheme]
        kwargs = self.connection_pool_kw
        if scheme == 'http':
            kwargs = self.connection_pool_kw.copy()
            for kw in SSL_KEYWORDS:
                kwargs.pop(kw, None)

        return pool_cls(host, port, **kwargs)


class HTTPResponseProxy(object):

    def __init__(self, resp):
        self.__resp = resp
        # NOTE: Making this class a second layer of compatibility (out
        # of 4 total, generally)
        self.__respc = CompatResponse(resp)
        self.msg = HTTPMessageAlike(resp.headers)
        self.status = int(resp.status)
        # self.__content_consumed = False

    # @property
    # def fp(self):
    #     """ A hack for
    #     `requests.packages.urllib3.util.response.is_fp_closed`
    #     which is used in
    #     `requests.packages.urllib3.response.HTTPResponse.stream`
    #     """
    #     # if self.__content_consumed:
    #     #     return None
    #     if self._body_buffer:
    #         # Not everything from the geventhttpclient's buffer was read
    #         return self
    #     return None  # 'virtually closed'
    # def read(self, *ar, **kwa):
    #     res = self.__respc.read(*ar, **kwa)
    #     if not res:
    #         self.__content_consumed = True
    #     return res

    # @property
    # def closed(self):
    #     return self.__resp.isclosed()

    @property
    def closed(self):
        return not self._body_buffer

    def __getattr__(self, name):
        try:
            return getattr(self.__respc, name)
        except AttributeError:
            try:
                return getattr(self.__resp, name)
            except AttributeError:
                if name == 'length':
                    return None
                raise


class HTTPMessageAlike(_httplib.HTTPMessage, object):
    def __init__(self, data):
        self.dict = dict(data)
        self.headers = ['%s: %s\r\n' % (k, v) for k, v in self.dict.items()]


fix_gehttplib_httpresponse = HTTPResponseProxy


def _getresponse(self, *ar, **kwa):
    """ Override-method for Connection that wraps the response for
    compatibility """
    # res = super(HTTPConnection, self).getresponse(*ar, **kwa)
    # res = gehttplib.HTTPConnection.getresponse(self, *ar, **kwa)
    res = self._upcls.getresponse(self, *ar, **kwa)
    res = fix_gehttplib_httpresponse(res)
    return res


def _urlopen(self, *ar, **kwa):
    """ HAX: force decode_content=True to make gzip work with the
    resulting session. Not sure what should be the correct way to do
    this.

    Applied to ConnectionPool classes.
    """
    kwa['decode_content'] = True
    return self._upcls.urlopen(self, *ar, **kwa)


class HTTPConnection(gehttplib.HTTPConnection):
    # Compat, needed for requests >= 2.2
    is_verified = False
    # Working around the old-style classes DRYishly:
    _upcls = gehttplib.HTTPConnection
    getresponse = _getresponse


class HTTPSConnection(gehttplib.HTTPSConnection):
    """ ... """
    is_verified = False
    _upcls = gehttplib.HTTPSConnection
    getresponse = _getresponse


#     def connect(self):
#         res = super(HTTPConnection, self).connect()
#         self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY,
#                         self.tcp_nodelay)
#         return res


class GHTTPConnectionPool(HTTPConnectionPool):
    ConnectionCls = HTTPConnection
    _upcls = HTTPConnectionPool
    urlopen = _urlopen


class GHTTPSConnectionPool(HTTPSConnectionPool):
    ConnectionCls = HTTPSConnection
    _upcls = HTTPSConnectionPool
    urlopen = _urlopen


pool_classes_by_scheme = {
    'http': GHTTPConnectionPool,
    'https': GHTTPSConnectionPool,
}


def make_session():
    session = requests.Session()
    session.mount('http://', GHTTPAdapter())
    session.mount('https://', GHTTPAdapter())
    return session


Session = make_session


@memoize
def get_cached_session(*ar, **kwa):
    return make_session(*ar, **kwa)


def get_session(new=False, **kwa):
    return make_session(**kwa) if new else get_cached_session(**kwa)
