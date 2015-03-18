# coding: utf8
""" madstuff: oneliners and debug-useful stuff """

import sys
import traceback
from .madness_reprstuff import GenReprWrapWrap


__all__ = (
    '_try', '_try2', '_iter_ar', '_filter',
    '_filter_n', '_print', '_ipdbg', '_uprint',
)


def _try2(_function_thingie, *ar, **kwa):
    """ Returns (res, None) on success or (None, exception) """
    # The weird names are to minimise kwa collision
    _exc_clss = kwa.pop('_exc_clss', Exception)
    # TODO?: return namedtuple?
    try:
        return (_function_thingie(*ar, **kwa), None)
    except _exc_clss as e:
        return (None, e)


def _try(*ar, **kwa):
    """ Return call result or None if an exception occurs """
    return _try2(*ar, **kwa)[0]


def _iter_ar(*ar):
    """ Helper to get an iterable (mostly tuple) out of some arguments """
    if len(ar) == 0:
        raise TypeError("At least one argument was required")
    elif len(ar) > 1:
        return ar
    else:
        ar0 = ar[0]
        if hasattr(ar0, '__iter__'):
            return ar0
        return (ar0,)


@GenReprWrapWrap
def _filter(*ar):
    """ Mostly the same as `filter(None, …)` but as a generator with
    conveniences. """
    it = _iter_ar(*ar)
    for i in it:
        if i:
            yield i


@GenReprWrapWrap
def _filter_n(*ar):
    """ Filter out None specifically (also a generator with conveniences) """
    it = _iter_ar(*ar)
    for i in it:
        if i is not None:
            yield i


def _print(s):
    """ Simple one-argument `print` one-liner; returns the argument """
    print s
    return s


def _ipdbg(_a_function_thingie, *ar, **kwa):
    """ Run with ipdb post-mortem on exception """
    import ipdb
    try:
        return _a_function_thingie(*ar, **kwa)
    except Exception as exc:
        _, _, sys.last_traceback = sys.exc_info()
        traceback.print_exc()
        ipdb.pm()
        return None


def _uprint(o):
    try:
        from IPython.lib.pretty import pretty
    except Exception:
        from pprint import pformat as pretty
    print pretty(o).decode('unicode-escape')
    return o
