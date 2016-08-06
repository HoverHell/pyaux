# coding: utf8
""" madstuff: other stuff stuff """

import re
from six.moves import urllib_parse as urlparse
from six.moves import xrange
from pyaux import dotdict
from pyaux.base import repr_cut as _cut


__all__ = (
    'Url',
    '_url_re',
    '_cut', 'IPNBDFDisplay',
    '_re_largest_matching_start',
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
    r'''(?i)\b((?:[a-z][\w-]+:(?:/{1,3}|[a-z0-9%])|www\d{0,3}[.]|[a-z0-9.\-]+'''
    r'''[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+'''
    r'''(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'".,<>?«»“”‘’]))''')


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
    columns = kwa.pop('columns', None)
    include = kwa.pop('include', None)
    exclude = kwa.pop('exclude', None)
    head = kwa.pop('head', 200)
    cutlinks = kwa.pop('cutlinks', True)
    do_display = kwa.pop('display', True)

    if head:
        df = df.head(head)

    if columns is not None:  # allows for reordering
        df = df.__class__(df, columns=columns)
    if include is not None:
        df = df.__class__(df, columns=[val for val in df.columns if val in include])
    if exclude is not None:
        df = df.__class__(df, columns=[val for val in df.columns if val not in exclude])

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


def _re_largest_matching_start(regex, value, return_regexp=False):
    """ Find a largest match (from the start of the string) in a value
    for the regex.

    WARN: computationally complex (d'uh).

    >>> _re_largest_matching_start(r'^[az]+zxcvb', 'aazx')
    'aazx'
    >>> _re_largest_matching_start(r'^[az]+zxcvb', 'aazx', return_regexp=1)
    ('^[az]+zx', 'aazx')
    """
    # Yet Another Insane Horror

    all_regexes = [regex[:idx] for idx in xrange(len(regex) + 1)]

    def _try_match(rex, st):
        try:
            return re.match(rex, st)
        except Exception:
            return

    # all_match_tries = [_try_match(subreg, s) for subreg in all_regexes]

    # Even more horrible:
    all_substrings = [value[:idx] for idx in xrange(len(value) + 1)]
    all_match_tries = (
        (subreg, _try_match(subreg, substr))
        for subreg in all_regexes
        for substr in all_substrings)
    all_matchstrings = [
        (subreg, val.group(0))
        for subreg, val in all_match_tries
        if val]
    if not all_matchstrings:
        return ''
    lrex, lval = max(
        all_matchstrings,
        key=lambda val: len(val[1]))  # longest match
    if return_regexp:
        return lrex, lval
    return lval
