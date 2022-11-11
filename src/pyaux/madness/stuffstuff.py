""" madstuff: other stuff stuff """
from __future__ import annotations

import re
import urllib.parse

from pyaux.base import repr_cut as _cut
from pyaux.dicts import MVOD, DotDict

__all__ = (
    "Url",
    "_url_re",
    "_cut",
    "displaydf",
    "_re_largest_matching_start",
)


# See also: https://pypi.org/project/yarl/
class Url(DotDict):
    """urlparse.ParseResult and parse_qs[l] in a dict-like non-lazy form"""

    _components = (
        "scheme",
        "netloc",
        "path",
        "params",
        "query",
        "fragment",
        # from ResultMixin
        "username",
        "password",
        "hostname",
        "port",
    )  # <scheme>://<netloc>/<path>;<params>?<query>#<fragment>
    _base_components = (
        "scheme",
        "netloc",
        "path",
        "params",
        "query",
        "fragment",
    )

    # TODO: urlunescaped parts

    def __init__(self, url, **kwa):
        self.url = url
        urldata = urllib.parse.urlparse(url, **kwa)
        for key in self._components:
            val = getattr(urldata, key)
            setattr(self, key, val)

        self.query_str = urldata.query
        self.queryl = urllib.parse.parse_qs(urldata.query)
        self.query = MVOD(urllib.parse.parse_qsl(urldata.query))
        # TODO?: self.query = pyaux.dicts.MVOD(urldata.query)

    def to_string(self):
        query_str = urllib.parse.urlencode(list(self.query.items()))
        return urllib.parse.urlunparse(
            self[key] if key != "query" else query_str for key in self._base_components
        )


_url_re = (
    r"""(?i)\b((?:[a-z][\w-]+:(?:/{1,3}|[a-z0-9%])|www\d{0,3}[.]|[a-z0-9.\-]+"""
    r"""[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+"""
    r"""(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'".,<>?«»“”‘’]))"""
)


def displaydf(df, *ar, **kwa):
    """A helper to display a pandas DataFrame in the IPython notebook.

    Recommended things to do:

        pd.options.display.max_colwidth = 2000

    :param head: (default 200) runs df = df.head(head); has default to
        avoid accidentally outputing too much; use an explicit
        `head=None` to disable.

    :param cutlinks: automatically converts all URLs in the resulting HTML
    to shortened values leading to the same addresses.
    """
    from IPython.display import HTML, display

    kwa.setdefault("float_format", lambda v: f"{v:.6f}")
    columns = kwa.pop("columns", None)
    include = kwa.pop("include", None)
    exclude = kwa.pop("exclude", None)
    head = kwa.pop("head", 200)
    cutlinks = kwa.pop("cutlinks", True)
    do_display = kwa.pop("display", True)

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
            result = f'<a href="{link}">{_cut(link, cutlinks)}</a>'
            return result

        html = re.sub(_url_re, lambda match: cutlink(match.group(0)), html)

    # TODO?: option to insert copious '<wb/>'s in all cells

    result = HTML(html)
    if do_display:
        display(result)
    return result


def _re_largest_matching_start(regex, value, return_regexp=False):
    """Find a largest match (from the start of the string) in a value
    for the regex.

    WARN: computationally complex (d'uh).

    >>> _re_largest_matching_start(r'^[az]+zxcvb', 'aazx')
    'aazx'
    >>> _re_largest_matching_start(r'^[az]+zxcvb', 'aazx', return_regexp=1)
    ('^[az]+zx', 'aazx')
    """
    # Yet Another Insane Horror

    all_regexes = [regex[:idx] for idx in range(len(regex) + 1)]

    def _try_match(rex, st):
        try:
            return re.match(rex, st)
        except Exception:
            return

    # all_match_tries = [_try_match(subreg, s) for subreg in all_regexes]

    # Even more horrible:
    all_substrings = [value[:idx] for idx in range(len(value) + 1)]
    all_match_tries = (
        (subreg, _try_match(subreg, substr)) for subreg in all_regexes for substr in all_substrings
    )
    all_matchstrings = [(subreg, val.group(0)) for subreg, val in all_match_tries if val]
    if not all_matchstrings:
        return ""
    lrex, lval = max(all_matchstrings, key=lambda val: len(val[1]))  # longest match
    if return_regexp:
        return lrex, lval
    return lval
