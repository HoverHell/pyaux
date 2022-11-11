""" madstuff: oneliners and debug-useful stuff """

from __future__ import annotations

import sys
import traceback

from ..base import o_repr
from .datadiff import _dumprepr
from .reprstuff import genreprwrap

__all__ = (
    "_try",
    "_try2",
    "_iter_ar",
    "_filter",
    "_filter_n",
    "_ipdbg",
    "_ipdbt",
    "_print",
    "_uprint",
    "_yprint",
    "_mrosources",
    "p_o_repr",
)


def _try2(_function_thingie, *ar, **kwa):
    """Returns (res, None) on success or (None, exception)"""
    # The weird names are to minimise kwa collision
    _exc_clss = kwa.pop("_exc_clss", Exception)
    # TODO?: return namedtuple?
    try:
        return _function_thingie(*ar, **kwa), None
    except _exc_clss as exc:
        return None, exc


def _try(*ar, **kwa):
    """Return call result or None if an exception occurs"""
    return _try2(*ar, **kwa)[0]


def _iter_ar(*args):
    """Helper to get an iterable (mostly tuple) out of some arguments"""
    if not args:
        raise TypeError("At least one argument was required")
    if len(args) > 1:
        return args

    first_arg = args[0]
    if hasattr(first_arg, "__iter__"):
        return first_arg
    return args


@genreprwrap
def _filter(*ar):
    """Mostly the same as `filter(None, …)` but as a generator with
    conveniences."""
    it = _iter_ar(*ar)
    for i in it:
        if i:
            yield i


@genreprwrap
def _filter_n(*ar):
    """Filter out None specifically (also a generator with conveniences)"""
    it = _iter_ar(*ar)
    for i in it:
        if i is not None:
            yield i


def _print(something):
    """Simple one-argument `print` one-liner; returns the argument"""
    print(something)  # noqa: T201 (print)
    return something


def _ipdbg(_a_function_thingie, *ar, **kwa):
    """Run with ipdb post-mortem on exception"""
    import ipdb

    try:
        return _a_function_thingie(*ar, **kwa)
    except Exception as exc:
        assert exc is not None
        _, _, sys.last_traceback = sys.exc_info()
        traceback.print_exc()
        ipdb.pm()
        return None


def _ipdbt(_a_function_thingie, *ar, **kwa):
    """Run with ipdb trace and post-mortem on exception"""
    import ipdb

    ipdb.set_trace()
    try:
        return _a_function_thingie(*ar, **kwa)
    except Exception as exc:
        assert exc is not None
        _, _, sys.last_traceback = sys.exc_info()
        traceback.print_exc()
        ipdb.pm()
        return None


def _pdbg(_a_function_thingie, *ar, **kwa):
    """Run with pdb post-mortem on exception"""
    import pdb

    try:
        return _a_function_thingie(*ar, **kwa)
    except Exception as exc:
        assert exc is not None
        _, _, sys.last_traceback = sys.exc_info()
        traceback.print_exc()
        pdb.pm()
        return None


def _pdbt(_a_function_thingie, *ar, **kwa):
    """Run with pdb trace and post-mortem on exception"""
    import pdb

    pdb.set_trace()
    try:
        return _a_function_thingie(*ar, **kwa)
    except Exception as exc:
        assert exc is not None
        _, _, sys.last_traceback = sys.exc_info()
        traceback.print_exc()
        pdb.pm()
        return None


def _uprint(obj, ret=False):
    try:
        from IPython.lib.pretty import pretty
    except Exception:
        from pprint import pformat as pretty
    obj_repr = pretty(obj)
    if isinstance(obj_repr, bytes):  # py2
        obj_repr = obj_repr.decode("unicode-escape")
    print(obj_repr)  # noqa: T201 (print)
    if ret:
        return obj
    return None


def _yprint(obj, ret=False, **kwa):
    kwa.setdefault("colorize", True)
    kwa.setdefault("no_anchors", False)
    kwa.setdefault("default_flow_style", None)
    kwa.setdefault("allow_unsorted_dicts", True)
    res_text = _dumprepr(obj, **kwa)
    print(res_text)  # noqa: T201 (print)
    if ret:
        return obj
    return None


def _mrosources(cls, attname, raw=False, colorize=False):
    """Return a (prettified) source code of a class method in its
    MRO. For figuring out where does the super() actually go."""
    import inspect

    from pyaux import dotdict

    meths = [dotdict(cls=mrocls, meth=getattr(mrocls, attname, None)) for mrocls in cls.__mro__]
    meths = [val for val in meths if val.meth]

    def getsrc(val):
        try:
            return inspect.getsource(val)
        except Exception:
            return "<???>"

    meths = [dotdict(val, src=getsrc(val.meth)) for val in meths]

    if colorize:
        from pyaux.base import colorize as colorfunc

        colorfunc_kwa = dict(fmt="py")
        if isinstance(colorize, dict):
            colorfunc_kwa.update(colorize)
        meths = [dotdict(val, src=colorfunc(val.src, **colorfunc_kwa)) for val in meths]
    if raw:
        return meths
    res = "\n\n".join(f" ======= {val.cls.__name__} =======\n{val.src}" for val in meths)
    return res


def p_o_repr(o, **kwa):
    kwa = dict(dict(_colors=True, _colors256=True), **kwa)
    print(o_repr(o, **kwa))  # noqa: T201 (print)
