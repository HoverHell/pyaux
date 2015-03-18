# coding: utf8
""" madstuff: other stuff stuff """

import re
import urlparse
from pyaux import dotdict


__all__ = (
    'Url',
    '_url_re',
    '_cut', 'IPNBDFDisplay',
)


class Url(dotdict):
    """ urlparse.ParseResult and parse_qs[l] in a dict-like non-lazy form """
    _components = (
        'scheme', 'netloc', 'path', 'params', 'query', 'fragment',
        # from ResultMixin
        'username', 'password', 'hostname', 'port',
    )  # <scheme>://<netloc>/<path>;<params>?<query>#<fragment>

    # TODO: urlunescaped parts

    def __init__(self, url, **kwa):
        self.url = url
        urldata = urlparse.urlparse(url, **kwa)
        for key in self._components:
            val = getattr(urldata, key)
            setattr(self, key, val)

        self.query_str = urldata.query
        self.queryl = urlparse.parse_qs(urldata.query)
        self.query = dict(urlparse.parse_qsl(urldata.query))
        # TODO?: self.query = pyaux.dicts.MVOD(urldata.query)


_url_re = (
    ur'''(?i)\b((?:[a-z][\w-]+:(?:/{1,3}|[a-z0-9%])|www\d{0,3}[.]|[a-z0-9.\-]+'''
    ur'''[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+'''
    ur'''(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'".,<>?«»“”‘’]))''')


def _cut(s, l):
    if len(s) <= l:
        return s
    return s[:l] + u'…'


def IPNBDFDisplay(df, *ar, **kwa):
    """ A helper to display a pandas DataFrame in the IPython notebook.

    Recommended things to do:
    pandas.options.display.max_colwidth = 2000
    H = IPNBDFDisplay

    :param head: (default 200) runs df = df.head(head); has default to
        avoid accidentally outputing too much; needs explicit
        `head=None` to disable.
    """
    from IPython.display import display, HTML
    kwa.setdefault('float_format', lambda v: '%.6f' % (v,))
    head = kwa.pop('head', 200)
    cutlinks = kwa.pop('cutlinks', True)
    do_display = kwa.pop('display', True)

    if head:
        df = df.head(head)

    html = df.to_html(*ar, **kwa)

    if cutlinks:
        cutlinks = 80 if cutlinks is True else cutlinks

        def cutlink(link):
            return '<a href="%s">%s</a>' % (link, _cut(link, cutlinks))
        html = re.sub(
            _url_re,
            lambda match: cutlink(match.group(0)),
            html)

    # TODO?: option to insert copious '<wb/>'s in all cells

    if do_display:
        display(HTML(html))
    else:
        return HTML(html)
