# coding: utf8
# pylint: disable=invalid-name,unused-import,import-error
"""
Some pieces of `six`-like code relevant to this package.
"""

from __future__ import division, absolute_import, print_function, unicode_literals

import sys


PY_3 = sys.version_info >= (3,)
PY3 = PY_3


if PY_3:
    import urllib.parse as urllib_parse

    izip = zip
    unicode = str
    text_type = str
    xrange = range

    def reraise(exc_type, exc_value, exc_traceback):  # pylint: disable=unused-argument
        try:
            raise exc_value.with_traceback(exc_traceback)
        finally:
            exc_value = None
            exc_traceback = None

else:

    import urlparse as urllib_parse

    from itertools import izip  # pylint: disable=no-name-in-module

    unicode = unicode
    text_type = unicode
    xrange = xrange

    # Would be a syntax error in py3, have to exec-wrap it.
    exec((  # pylint: disable=exec-used
        "def reraise(exc_type, exc_value, exc_traceback):\n"
        "    try:\n"
        "        raise exc_type, exc_value, exc_traceback\n"
        "    finally:\n"
        "        exc_traceback = None\n"
    ))
