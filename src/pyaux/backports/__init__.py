# coding: utf8
""" Various modules for use in older python versions which don't have them natively yet """

import re

_sh_find_unsafe = re.compile(r"[^\w@%+=:,./-]").search


def sh_quote_prettier(s):
    r"""
    Quote a value for copypasteability in a posix commandline.

    A more readable version than the `shlex.quote`.

    >>> sh_quote_prettier("'one's one'")
    "\\''one'\\''s one'\\'"
    """
    if not s:
        return "''"
    if _sh_find_unsafe(s) is None:
        return s

    # A shorter version: backslash-escaped single quote.
    result = "'" + s.replace("'", "'\\''") + "'"
    # Cleanup the empty excesses at the ends
    _overedge = "''"
    if result.startswith(_overedge):
        result = result[len(_overedge) :]
    if result.endswith(_overedge):
        result = result[: -len(_overedge)]
    return result
