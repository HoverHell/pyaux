"""Various functions for easier working with URLs"""

from __future__ import annotations

import shlex
import urllib.parse
from typing import TypedDict

from .base import mangle_dict, to_bytes

__all__ = (
    "curl_to_requests_kwargs",
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
    from pyaux.dicts import MVOD  # noqa: PLC0415

    url_parts = urllib.parse.urlparse(to_bytes(url))
    query = MVOD(urllib.parse.parse_qsl(url_parts.query, keep_blank_values=True))
    query_new = mangle_dict(query, include=include, exclude=exclude, add=add, _return_list=True)
    return url_replace(url, query=query_new, **kwargs)


class RequestsKwargs(TypedDict, total=False):
    method: str
    url: str
    headers: dict[str, str]
    params: dict[str, str | list[str]]
    data: str
    cookies: dict[str, str]
    auth: tuple[str, str]
    verify: bool


def _parse_header(raw: str) -> tuple[str, str]:
    name, sep, value = raw.partition(":")
    if sep == "":
        raise ValueError(f"Invalid header: {raw!r}")
    return name.strip(), value.lstrip()


def _parse_cookie_string(raw: str) -> dict[str, str]:
    cookies: dict[str, str] = {}
    for part in raw.split(";"):
        item = part.strip()
        if not item:
            continue
        name, sep, value = item.partition("=")
        if sep == "":
            continue
        cookies[name.strip()] = value.strip()
    return cookies


def _merge_params(query: str) -> dict[str, str | list[str]]:
    params: dict[str, str | list[str]] = {}
    for key, value in urllib.parse.parse_qsl(query, keep_blank_values=True):
        current = params.get(key)
        if current is None:
            params[key] = value
        elif isinstance(current, list):
            current.append(value)
        else:
            params[key] = [current, value]
    return params


def curl_to_requests_kwargs(curl_command: str) -> RequestsKwargs:
    """
    Given a `curl` command (e.g. from firefox's "copy as cURL"),
    build kwargs for `requests.request`.
    """
    tokens = shlex.split(curl_command, posix=True)
    if not tokens or tokens[0] != "curl":
        raise ValueError(f"Expected a curl command in {curl_command!r}")

    method = "GET"
    method_explicit = False
    url: str | None = None
    headers: dict[str, str] = {}
    cookies: dict[str, str] = {}
    data_parts: list[str] = []
    auth: tuple[str, str] | None = None
    verify = True

    i = 1
    while i < len(tokens):
        token = tokens[i]

        if token in {"-X", "--request"}:
            i += 1
            if i >= len(tokens):
                raise ValueError(f"Missing value after {token}")
            method = tokens[i].upper()
            method_explicit = True

        elif token in {"-H", "--header"}:
            i += 1
            if i >= len(tokens):
                raise ValueError(f"Missing value after {token}")
            name, value = _parse_header(tokens[i])
            if name.lower() == "cookie":
                cookies.update(_parse_cookie_string(value))
            else:
                headers[name] = value

        elif token in {"-b", "--cookie"}:
            i += 1
            if i >= len(tokens):
                raise ValueError(f"Missing value after {token}")
            cookies.update(_parse_cookie_string(tokens[i]))

        elif token in {"-d", "--data", "--data-binary", "--data-raw", "--data-ascii"}:
            i += 1
            if i >= len(tokens):
                raise ValueError(f"Missing value after {token}")
            data_parts.append(tokens[i])
            if not method_explicit:
                method = "POST"

        elif token in {"-u", "--user"}:
            i += 1
            if i >= len(tokens):
                raise ValueError(f"Missing value after {token}")
            user, sep, password = tokens[i].partition(":")
            if sep == "":
                raise ValueError("Expected --user value in the form username:password")
            auth = (user, password)

        elif token in {"-k", "--insecure"}:
            verify = False

        elif token == "--url":
            i += 1
            if i >= len(tokens):
                raise ValueError("Missing value after --url")
            url = tokens[i]

        elif token in {"--compressed", "--globoff", "--path-as-is", "-L", "--location"} or token.startswith("-"):
            pass

        elif url is None:
            url = token

        i += 1

    if url is None:
        raise ValueError("No URL found in curl command")

    split_url = urllib.parse.urlsplit(url)
    base_url = urllib.parse.urlunsplit((split_url.scheme, split_url.netloc, split_url.path, "", ""))

    result: RequestsKwargs = {
        "method": method,
        "url": base_url if split_url.query else url,
    }

    if split_url.query:
        result["params"] = _merge_params(split_url.query)
    if headers:
        result["headers"] = headers
    if cookies:
        result["cookies"] = cookies
    if data_parts:
        result["data"] = data_parts[0] if len(data_parts) == 1 else "&".join(data_parts)
    if auth is not None:
        result["auth"] = auth
    if not verify:
        result["verify"] = False

    return result
