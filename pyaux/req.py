# coding: utf8
"""
Requests for humans that have to deal with lots of stuff.
"""

from __future__ import division, absolute_import, print_function, unicode_literals

import sys
import logging
import functools

import requests
import requests.adapters
import requests.exceptions
from requests.packages.urllib3.util import Retry  # pylint: disable=import-error
from pyaux.minisix import text_type, urllib_parse
from pyaux.base import (
    find_caller,
    split_dict, dict_maybe_items,
    LazyRepr, to_bytes,
)

# Singleton session for connection pooling.
# WARNING: this involves caching; do `SESSION.close()` in a `finally:` block to clean it up.
SESSION = requests.Session()


def configure_session(
        session,
        retries_total=5,
        retries_backoff_factor=0.5,
        retries_status_forcelist=(500, 502, 503, 504, 521),
        retries_method_whitelist=frozenset((
            'HEAD', 'OPTIONS', 'TRACE', 'GET',
            'POST', 'PUT', 'PATCH', 'DELETE')),
        pool_connections=30,
        pool_maxsize=30,
        **kwargs):
    """
    Configure session with significant retries.

    WARNING: by default, retries mutating requests too. Use only when
    idempotence is expected (or at-least-once delivery is generally okay).
    """
    retry_conf = Retry(
        total=retries_total,
        backoff_factor=retries_backoff_factor,
        status_forcelist=retries_status_forcelist,
        method_whitelist=retries_method_whitelist,
    )

    for prefix in ('http://', 'https://'):
        session.mount(
            prefix,
            requests.adapters.HTTPAdapter(
                max_retries=retry_conf,
                pool_connections=pool_connections,
                pool_maxsize=pool_maxsize,
            ))

    return session


SESSION_ZEALOUS = configure_session(requests.Session())


class RequesterBase(object):

    apply_environment = True
    length_cut_marker = '...'
    prepare_request_keys = frozenset((
        'method', 'url',
        'headers', 'auth', 'cookies',
        'params',
        'data', 'files', 'json',
        'hooks',
    ))
    send_request_keys = frozenset((
        'proxies', 'cert', 'verify',
        'stream', 'timeout',
        'allow_redirects',
    ))

    def __init__(self, session=True):
        if session is True:
            session = SESSION
        elif session is None:
            session = requests.Session()
        self.session = session
        self.logger = logging.getLogger('req')

    @staticmethod
    def preprepare_parameters(kwargs):
        """
        Separated out for easier overriding of `prepare_parameters` by subclasses.
        """
        headers = kwargs.get('headers')
        # For common convenience, commonize the headers:
        if headers is None:
            headers = {}
        else:
            # TODO?: OrderedDict?
            headers = {
                key.lower().replace('_', '-'): value
                for key, value in dict_maybe_items(headers)}
        kwargs['headers'] = headers

        return kwargs

    def prepare_parameters(self, kwargs):  # pylint: disable=no-self-use
        return kwargs

    def request(self, url, **kwargs):
        kwargs['url'] = url
        request, send_kwargs = self.prepare_request(kwargs)
        return self.send_request(request, **send_kwargs)

    def prepare_request(self, kwargs, run_processing=True):
        session = kwargs.pop('session', None) or self.session

        if run_processing:
            kwargs = self.preprepare_parameters(kwargs)
            kwargs = self.prepare_parameters(kwargs)

        assert kwargs.get('method')
        assert kwargs.get('url')

        prepare_keys = self.prepare_request_keys
        prepare_kwargs, send_kwargs = split_dict(
            kwargs, lambda key, value: key in prepare_keys)

        send_keys = self.send_request_keys
        send_kwargs, unknown_kwargs = split_dict(
            send_kwargs, lambda key, value: key in send_keys)

        if unknown_kwargs:
            raise ValueError("Unknown request arguments", unknown_kwargs)

        request = requests.Request(**prepare_kwargs)
        request = session.prepare_request(request)
        if self.apply_environment:
            send_kwargs_overrides = send_kwargs
            # http://docs.python-requests.org/en/master/user/advanced/#prepared-requests
            send_kwargs = session.merge_environment_settings(
                request.url, {}, None, None, None)
            send_kwargs.update(send_kwargs_overrides)
        send_kwargs['session'] = session
        return request, send_kwargs

    def send_request(self, request, **kwargs):
        session = kwargs.pop('session', None) or self.session
        return session.send(request, **kwargs)

    def __call__(self, *args, **kwargs):
        kwargs['call_extra_depth'] = (kwargs.get('call_extra_depth') or 0) + 1
        return self.request(*args, **kwargs)


class RequesterSessionWrap(RequesterBase):

    def __getattr__(self, key):
        return getattr(self.session, key)


class RequesterVerbMethods(RequesterBase):

    def get(self, *args, **kwargs):
        kwargs['method'] = 'get'
        return self.request(*args, **kwargs)

    def options(self, *args, **kwargs):
        kwargs['method'] = 'options'
        return self.request(*args, **kwargs)

    def head(self, *args, **kwargs):
        kwargs['method'] = 'head'
        return self.request(*args, **kwargs)

    def post(self, *args, **kwargs):
        kwargs['method'] = 'post'
        return self.request(*args, **kwargs)

    def put(self, *args, **kwargs):
        kwargs['method'] = 'put'
        return self.request(*args, **kwargs)

    def patch(self, *args, **kwargs):
        kwargs['method'] = 'patch'
        return self.request(*args, **kwargs)

    def delete(self, *args, **kwargs):
        kwargs['method'] = 'delete'
        return self.request(*args, **kwargs)


class RequesterDefaults(RequesterBase):

    def __init__(self, default_timeout=5.0, default_write_method='post', default_allow_redirects='auto', **kwargs):
        self.default_timeout = default_timeout
        self.default_write_method = default_write_method
        self.default_allow_redirects = default_allow_redirects
        super(RequesterDefaults, self).__init__(**kwargs)

    def prepare_parameters(self, kwargs):
        # NOTE: will leave explicit `timeout=None` as-is.
        kwargs.setdefault('timeout', self.default_timeout)

        # Determine the method by the presence of `data` / `files`.
        if kwargs.get('method') is None:
            if kwargs.get('data') is not None or kwargs.get('files') is not None:
                kwargs['method'] = self.default_write_method
            else:
                kwargs['method'] = 'get'

        if 'allow_redirects' not in kwargs:
            if self.default_allow_redirects == 'auto':
                # From `requests.get` logic.
                kwargs['allow_redirects'] = kwargs['method'] in ('get', 'options')
            else:
                kwargs['allow_redirects'] = self.default_allow_redirects

        return super(RequesterDefaults, self).prepare_parameters(kwargs)


class RequesterBaseUrl(RequesterBase):
    """ Common relative URL support for RequesterBase """

    def __init__(self, base_url=None, **kwargs):
        self.base_url = base_url
        super(RequesterBaseUrl, self).__init__(**kwargs)

    def prepare_parameters(self, kwargs):
        if self.base_url:
            kwargs['url'] = urllib_parse.urljoin(
                self.base_url,
                kwargs['url'])  # required parameter
        return super(RequesterBaseUrl, self).prepare_parameters(kwargs)


class RequesterContentType(RequesterBase):
    """
    `requests` itself allows a `json=...` parameter to the methods.

    However, that is a bad design decision.

    This mixin adds a support for 'content_type' paremeter which defines how
    the body should be serialized.

    WARNING: it also sets the default content type to `'json'`.
    """

    def __init__(self, default_content_type='json', **kwargs):
        self.default_content_type = default_content_type
        super(RequesterContentType, self).__init__(**kwargs)

    def prepare_parameters(self, kwargs):
        content_type = kwargs.pop('content_type', self.default_content_type)
        data = kwargs.get('data')
        json_data = kwargs.pop('json', None)
        if json_data is not None:
            raise Exception((
                "Please don't use `json=...` keyword here."
                " Use `content_type='json'`, which might already be the default."))
        if data is not None and content_type is not None:
            # # Maybe:
            # if content_type == 'multipart':
            #     kwargs.pop('data', None)
            #     kwargs['files'] = data
            content_type_header, data = self.serialize_data(
                data, content_type=content_type, context=kwargs)
            if data is not None:
                kwargs['data'] = data
                if content_type_header is not None:
                    kwargs['headers']['content-type'] = content_type_header
        return super(RequesterContentType, self).prepare_parameters(kwargs)

    json_content_type = 'application/json; charset=utf-8'

    def serialize_data(self, data, content_type, context=None):
        """
        ...

        NOTE: `content_type=None` has a special meaning 'pass the data as-is'.
        """
        if content_type is None:
            return None, data
        # # Maybe:
        # if content_type == 'urlencode':
        #     return None, data
        if content_type == 'json':
            return self.serialize_data_json(data, context=context)
        if content_type == 'ujson':  # Special case for dangerous performance.
            return self.serialize_data_ujson(data, context=context)
        raise Exception("Unknown data serialization content_type", content_type)

    def serialize_data_json(self, data, context=None):  # pylint: disable=unused-argument
        """ Overridable point for json-serialization customization. """
        from .anyjson import json_dumps
        data = to_bytes(json_dumps(data))
        return self.json_content_type, data

    def serialize_data_ujson(self, data, context=None):  # pylint: disable=unused-argument
        import ujson
        # pylint: disable=c-extension-no-member
        data = to_bytes(ujson.dumps(data, ensure_ascii=False))
        return self.json_content_type, data


class RequesterMeta(RequesterBase):

    def __init__(self, collect_call_info=True, call_info_in_ua=True, **kwargs):
        self.collect_call_info = collect_call_info
        self.call_info_in_ua = call_info_in_ua
        super(RequesterMeta, self).__init__(**kwargs)

    def prepare_parameters(self, kwargs):
        call_info = kwargs.pop('call_info', None)
        if call_info and self.call_info_in_ua:
            # `call_info`: `(cfile, cline, cfunc)`.
            kwargs['headers']['user-agent'] = '{}, {}:{}: {}'.format(
                kwargs['headers'].get('user-agent') or '',
                *call_info)
        return super(RequesterMeta, self).prepare_parameters(kwargs)

    def request(self, url, **kwargs):
        """
        ...

        WARNING: should either be the entry-point method or be wrapped with

            kwargs['call_extra_depth'] = (kwargs.get('call_extra_depth') or 0) + 1
        """
        call_extra_depth = kwargs.pop('call_extra_depth', 0)
        if self.collect_call_info and kwargs.get('call_info') is None:
            # Could actually filter out the current module, but that's costly and palliative.
            kwargs['call_info'] = find_caller(extra_depth=call_extra_depth + 1)
        return super(RequesterMeta, self).request(url, **kwargs)


class RequesterAutoRaiseForStatus(RequesterBase):

    raise_with_content = True
    raise_content_cap = 1800

    def send_request(self, request, **kwargs):
        require = kwargs.pop('require', True)
        response = super(RequesterAutoRaiseForStatus, self).send_request(request, **kwargs)
        if require:
            self.raise_for_status(response)
        return response

    def raise_for_status(self, response):
        if not self.raise_with_content:
            response.raise_for_status()
            return
        if response.ok:
            return
        self.raise_for_status_forced(response)

    def raise_for_status_forced(self, response):
        try:
            # TODO?: support streaming?
            content = response.content
            cap = self.raise_content_cap
            if cap:
                content = '{}{}'.format(content[:cap], self.length_cut_marker)
        except Exception:
            raise requests.exceptions.HTTPError(
                "Status Error: {} {}".format(
                    response.status_code, response.reason),
                response=response)
        raise requests.exceptions.HTTPError(
            "Status Error: {} {}: {}".format(
                response.status_code, response.reason, content),
            response=response)


class RequesterLog(RequesterBase):

    log_response_headers = True
    logging_url_cap = 1800

    def send_request(self, request, **kwargs):
        self.log_before(request, **kwargs)
        try:
            response = super(RequesterLog, self).send_request(request, **kwargs)
        except Exception as exc:
            exc_info = sys.exc_info()
            self.log_exc(request, exc, exc_info=exc_info, **kwargs)
            raise
        self.log_after(request, response, **kwargs)
        return response

    def request_for_logging(self, request):

        url = request.url
        url_cap = self.logging_url_cap
        if url_cap and len(url) > url_cap:
            url = '{}{}'.format(url[:url_cap], self.length_cut_marker)

        data_info = ''
        if request.body:
            data_info = "  data_len={}".format(len(request.body))

        return "{method} {url}{data_info}".format(
            method=request.method.upper(), url=url, data_info=data_info)

    def request_for_logging_lazy(self, request):
        return LazyRepr(functools.partial(self.request_for_logging, request))

    def response_for_logging(self, response):
        pieces = [
            response.status_code,
            response.request.method,
            response.url,
            '    {}b'.format(len(response.content or '')),
        ]
        try:
            elapsed = "in {:.3f}s".format(response.elapsed.total_seconds())
        except Exception:  # pylint: disable=broad-except
            elapsed = "in ???s"
        pieces.append(elapsed)
        if self.log_response_headers:
            pieces.append('    response.headers={!r}'.format(response.headers))
        return ' '.join(
            text_type(piece) if not isinstance(piece, text_type) else piece
            for piece in pieces)

    def log_before(self, request, level=logging.DEBUG, **kwargs):
        if not self.logger.isEnabledFor(level):
            return
        self.logger.debug(
            "Sending request: %s",
            self.request_for_logging_lazy(request))

    def log_after(self, request, response, level=logging.INFO, **kwargs):
        if not self.logger.isEnabledFor(level):
            return
        self.logger.log(
            level,
            "Response: %s    -> %s",
            self.request_for_logging_lazy(request),
            self.response_for_logging(response))

    def log_exc(self, request, exc, exc_info=None, level=logging.ERROR, **kwargs):
        if not self.logger.isEnabledFor(level):
            return

        response_str = ''
        response = getattr(exc, 'response', None)
        if response is not None:
            response_str = ' ({})'.format(
                self.response_for_logging(response))

        self.logger.log(
            level,
            "Request exception: %s -> %r%s",
            self.request_for_logging_lazy(request),
            exc,
            response_str,
            exc_info=exc_info or True)


class Requester(
        RequesterLog, RequesterAutoRaiseForStatus, RequesterMeta,
        RequesterContentType, RequesterBaseUrl, RequesterDefaults,
        RequesterVerbMethods, RequesterSessionWrap, RequesterBase):
    """ Batteries-included combined class """

    # # TODO: for accessible signatures:
    # def __init__(self, ...):
    #     """ ... """
    #     super(...)
    # def request(self, url, ...):
    #     """ ... """
    #     callinfo = ...
    #     return super(...)



class APIRequester(Requester):

    def __init__(self, **kwargs):
        kwargs.setdefault('session', SESSION_ZEALOUS)
        kwargs.setdefault('default_timeout', 120)
        kwargs.setdefault('default_allow_redirects', False)
        super(APIRequester, self).__init__(**kwargs)

    def raise_for_status(self, response):
        if response.status not in (200, 201):
            self.raise_for_status_forced(response)


def test():
    from pyaux.runlib import init_logging
    init_logging(level=1)
    reqr = Requester()
    resp = reqr.get('https://example.com?param1=a', params=dict(param2='b'))
    print(resp)
    assert resp.ok
    resp = reqr(
        'https://example.com?param2=a',
        params=dict(param1='b'),
        headers={'Content-Type': 'nope, delete this'},
        data=dict(param3=['c', 1]))
    print(resp)


if __name__ == '__main__':
    test()
