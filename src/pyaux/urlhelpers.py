"""Various functions for easier working with URLs"""

from __future__ import annotations

import urllib.parse

from .base import mangle_dict, to_bytes

__all__ = (
    "mangle_url",
    "mangle_url_l",
    "mangle_url_m",
    "url_replace",
    "url_to_querydict",
)


def dict_to_bytes(d):
    """
    Encode the strings in keys and values of a dict 'd' into
    bytestrings; useful for e.g. urlencoding the result
    """
    return {to_bytes(k): to_bytes(v) for k, v in d.items()}


def url_to_querydict(url):
    """A shorthand for getting an url's query as a dict"""
    url = to_bytes(url)
    return dict(urllib.parse.parse_qsl(urllib.parse.urlparse(url).query))


def url_replace(url, **params):
    """Replace some named parts in an url; See `urllib.parse.ParseResult` for the names"""
    url_fields = urllib.parse.ParseResult._fields
    name_to_num = {field: idx for idx, field in enumerate(url_fields)}
    url_parts = list(urllib.parse.urlparse(url))  # Need a copy anyway
    for key, val_raw in params.items():
        val = val_raw
        # Allow supplying various stuff as a query
        if key == "query" and not isinstance(val, (bytes, str)):
            if isinstance(val, dict):
                val = val.items()
            val = [(to_bytes(query_key), to_bytes(query_val)) for query_key, query_val in val]
            val = urllib.parse.urlencode(val)

        num = name_to_num[key]  # Will except here if supplied an unknown url param
        url_parts[num] = val
    return urllib.parse.urlunparse(url_parts)


def mangle_url(url, include=None, exclude=None, add=None):
    """'mangle_dict' for url's query parameters"""
    query = url_to_querydict(url)
    query_new = mangle_dict(query, include=include, exclude=exclude, add=add)
    return url_replace(url, query=query_new)


def mangle_url_m(url, include=None, exclude=None, add=None):
    """
    Multivalue-version of the `mangle_url`; works with dict of lists only
    (`param -> [value1, …]`); sorts the resulting query
    """
    url = to_bytes(url)
    url_parts = urllib.parse.urlparse(url)
    # NOTE: the order of the fields is still lost.
    query = urllib.parse.parse_qs(url_parts.query, keep_blank_values=True)
    query_new = mangle_dict(query, include=include, exclude=exclude, add=add)
    query_new = [(k, v) for k, vl in query_new.items() for v in vl]
    query_new = [(to_bytes(k), to_bytes(v)) for k, v in query_new]
    query_new = sorted(query_new)  # make the order stable since it's lost anyway
    return url_replace(url, query=query_new)


def mangle_url_l(url, include=None, exclude=None, add=None, **kwargs):
    """
    mangle_url with preserving as much as possible (order, multiple values, empty values).

    Additional keyword parameters are passed to url_replace.

    >>> from pyaux.dicts import MVOD
    >>> query = r"a=&a=1&a=true&b=null&b=undefined&b=&b=5"
    >>> urllib.parse.urlencode(MVOD(urllib.parse.parse_qsl(query, keep_blank_values=1))) == query
    True
    """
    from pyaux.dicts import MVOD

    url_parts = urllib.parse.urlparse(to_bytes(url))
    query = MVOD(urllib.parse.parse_qsl(url_parts.query, keep_blank_values=True))
    query_new = mangle_dict(query, include=include, exclude=exclude, add=add, _return_list=True)
    return url_replace(url, query=query_new, **kwargs)
