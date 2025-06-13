from __future__ import annotations

import errno
import functools
import json
import logging
import math
import os
import re
import sys
import time
import traceback
import unicodedata
import urllib.parse
from collections.abc import Callable, Hashable, Iterable, Iterator
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, TypeVar, cast

if TYPE_CHECKING:
    from decimal import Decimal
    from types import FrameType

__all__ = (
    "HashableDictST",
    "LazyRepr",
    "LazyStr",
    "Memoize",
    "OReprMixin",
    "ReprObj",
    "ThrottledCall",
    "_sqrt",
    "chunks",
    "colorize",
    "colorize_diff",
    "colorize_yaml",
    "configurable_wrapper",
    "current_frame",
    "debug_plug",
    "dict_maybe_items",
    "exclogwrap",
    "find_caller",
    "find_files",
    "get_env_flag",
    "groupby",
    "human_sort_key",
    "import_func",
    "import_module",
    "mangle_dict",
    "mangle_items",
    "memoize_method",
    "memoized_property",
    "mk_logging_property",
    "mkdir_p",
    "o_repr",
    "o_repr_g",
    "obj2dict",
    "repr_call",
    "repr_cut",
    "sign",
    "simple_memoize_argless",
    "slstrip",
    "split_dict",
    "split_list",
    "stdin_bin_lines",
    "stdin_lines",
    "stdout_lines",
    "throttled_call",
    "to_bytes",
    "to_text",
    "try_parse",
)


TKey = TypeVar("TKey", bound=Hashable)
TVal = TypeVar("TVal")
TRet = TypeVar("TRet")


def repr_call(args, kwargs):
    """A helper function for pretty-printing a function call arguments"""
    res = ", ".join(f"{val!r}" for val in args)
    if kwargs:
        if res:
            res += ", "
        res += ", ".join(f"{key}={val!r}" for key, val in kwargs.items())
    return res


dbgs: dict[str, Any] = {}  # global object for easier later access of dumped `__call__`s


def debug_plug(name, mklogger=None):
    """
    Create and return a recursive duck-object for plugging in
    place of other objects for debug purposes.

    :param name: name for tracking the object and its (child) attributes.

    :param mklogger: a function of `name` (str) that returns a new callable(msg:
      str) used for logging.  See code for an example.
    """

    # The construction with mkClass is for removing the need of
    #   `__getattr__`ing the name and logger.
    def mklogger_default(name):
        logger = logging.getLogger(name)
        return logger.debug

    if mklogger is None:
        mklogger = mklogger_default

    log = mklogger(name)

    class DebugPlugInternal:
        """An actual internal class of the DebugPlug"""

        def __call__(self, *ar, **kwa):
            log("called with (%s)", repr_call(ar, kwa))
            # NOTE: global `dbgs`
            dbgs.setdefault(name, {})
            dbgs[name]["__call__"] = (ar, kwa)

        def __getattr__(self, attname):
            namef = f"{name}.{attname}"
            # Recursive!
            dpchild = debug_plug(name=namef, mklogger=mklogger)
            # setattr(self, attname, dpchild)
            object.__setattr__(self, attname, dpchild)
            return dpchild

        def __setattr__(self, attname, value):
            log("setattr: %s = %r", attname, value)
            # NOTE: global `dbgs`
            dbgs.setdefault(name, {})
            dbgs[name][attname] = value
            return object.__setattr__(self, attname, value)

    return DebugPlugInternal()


def split_list(iterable, condition):
    """Split list items into `(matching, non_matching)` by `cond(item)` callable."""
    matching = []
    non_matching = []
    for item in iterable:
        if condition(item):
            matching.append(item)
        else:
            non_matching.append(item)
    return matching, non_matching


def dict_maybe_items(value):
    items = getattr(value, "items", None)
    if items is not None:
        return items()
    return value


def split_dict(source, condition, cls=dict):
    source = dict_maybe_items(source)
    matching, nonmatching = split_list(source, lambda item: condition(item[0], item[1]))
    return cls(matching), cls(nonmatching)


# TODO: make a recurser that supports and recurses, maintains,
# optionally-replaces various classes such as tuple, defaultdict, and
# other containers. Possibly use pickle/deepcopy's logic.


def obj2dict(obj, *, add_type=False, add_instance=False, do_lists=True, dict_class=dict):
    """Recursive obj -> obj.__dict__"""
    kwa = dict(
        add_type=add_type,
        add_instance=add_instance,
        do_lists=do_lists,
        dict_class=dict_class,
    )

    if hasattr(obj, "__dict__"):
        res = dict_class()
        for key, val in obj.__dict__.items():
            res[key] = obj2dict(val, **kwa)
        if add_type:
            res["__class__"] = obj.__class__
        if add_instance:
            res["__instance__"] = obj
        return res

    # Recurse through other types too:
    # NOTE: There might be subclasses of these that would not be
    # processed here.
    if isinstance(obj, dict):
        return dict_class((key, obj2dict(val, **kwa)) for key, val in obj.items())

    if isinstance(obj, list):
        return [obj2dict(val, **kwa) for val in obj]

    return obj  # something else - return as-is.


def mk_logging_property(actual_name, logger_name="_log"):
    """
    Creates a property that logs the value and the caller in the
    setter, using logger under `self`'s logger_name, and stores the value
    under `actual_name` on `self`.
    """

    def do_get(self):
        return getattr(self, actual_name)

    def do_set(self, val):
        tb = traceback.extract_stack(limit=2)[0]
        # # or:
        # next((r.f_code.co_filename, r.f_lineno, r.f_code.co_name) for r in (sys._getframe(1),))
        # # that is,
        # r = sys._getframe(1)
        # co = r.f_code
        # co.co_filename, r.f_lineno, co.co_name
        setattr(self, actual_name, val)
        getattr(self, logger_name).debug("%s set to %r from %s:%d, in %s", actual_name, val, tb[0], tb[1], tb[2])

    return property(do_get, do_set)


def sign(value: float | Decimal) -> Literal[-1, 0, 1]:
    """
    Sign of value.

    One of the many possible ways to implement this.

    In [10]: sign(-10)
    Out[10]: -1

    In [11]: sign(0)
    Out[11]: 0

    In [12]: sign(10)
    Out[12]: 1
    """
    if value == 0:
        return 0
    if value > 0:
        return 1
    if value < 0:
        return -1
    raise ValueError("Inconsistent value")


# #######  "Human" sorting, advanced #######
# partially from quodlibet/quodlibet/util/__init__.py
# partially from comix/src/filehandler.py


def try_parse(val, fn=int):  # NOTE: generally similar to `.madness._try`
    """'try parse' (with fn)"""
    try:
        return fn(val)
    except Exception:
        return val


# Note: not localized (i.e. always as dot for decimal separator)
_re_alphanum_f = re.compile(r"[0-9]+(?:\.[0-9]+)?|[^0-9]+")


def _split_numeric_f(string):
    return [try_parse(val, fn=float) for val in _re_alphanum_f.findall(string)]


# Or to avoid interpreting numbers as float:
_re_alphanum_int = re.compile(r"\d+|\D+")


def _split_numeric(string):
    return [try_parse(val, fn=int) for val in _re_alphanum_int.findall(string)]


# Primary function:
def human_sort_key(string, *, normalize=unicodedata.normalize, floats=True):
    """Sorting key for 'human' sorting"""
    string = to_text(string)
    string = normalize("NFD", string.lower())
    split_fn = _split_numeric_f if floats else _split_numeric
    return string and split_fn(string)


# ####### ...


class ThrottledCall:
    """
    Decorator for throttling calls to some functions (e.g. logging).
    Defined as class for various custom attributes and methods.
    Attributes:
      `handle_skip`: function(self, *ar, **kwa) to call when a call is
        skipped. (default: return None)
    Methods: `call_something`
    """

    # _last_call_time = None
    _call_time_throttle = 0.0
    _call_cnt = 0  # (kept accurate; but can become ineffectively large)
    _call_cnt_throttle = 0  # next _call_cnt to call at
    _call_val = object()  # (some unique value at start)

    def __init__(self, fn=None, sec_limit=None, cnt_limit=None):
        """
        :param fn: function to call (can be customized later).
        :param sec_limit: skip call if less than `sec_limit` seconds since the last call.
        :param cnt_limit: call only once each `cnt_limit` calls.
        """
        self.fn = fn
        # # mimickry, v2
        # self.__call__ = wraps(fn)(self.__call__)
        self.sec_limit = sec_limit
        self.cnt_limit = cnt_limit
        doc = f"{fn.__doc__} (throttled)"

        self.__doc__ = doc
        self.__call__.__doc__ = doc
        _func_obj = getattr(self.__call__, "__func__", None)
        if _func_obj:
            _func_obj.__doc__ = doc
        self.handle_skip = lambda self, *ar, **kwa: None

    def __call__(self, *ar, **kwa):
        return self.call_something(self.fn, *ar, **kwa)

    def call_something(self, fn, *ar, **kwa):
        """Call some (other) function with the same throttling"""
        now = time.time()
        # do_call = True
        # # NOTE: `throttle_cnt(throttle_sec(fn))` is emulated if both
        # # are set.
        if self.cnt_limit is not None:
            self._call_cnt += 1
            if self._call_cnt >= self._call_cnt_throttle:
                self._call_cnt_throttle += self.cnt_limit
            else:
                return self.handle_skip(self, *ar, **kwa)
        if self.sec_limit is not None:
            if now > self._call_time_throttle:
                self._call_time_throttle = now + self.sec_limit
            else:
                return self.handle_skip(self, *ar, **kwa)
        return fn(*ar, **kwa)

    def call_value(self, val, fn, *ar, **kwa):
        """
        Call if the value hasn't changed (applying the other
        throttling parameters as well). Contains undocumented feature
        """
        if self._call_val != val:
            self._call_val = val
            if fn is None:
                fn = self.fn
            return self.call_something(fn, *ar, **kwa)
        return None

    def __repr__(self):
        return f"<throttled_call({self.fn!r})>"

    # # Optional: mimickry
    # def __repr__(self):
    #     return repr(self.fn)
    # def __getattr__(self, v):
    #     return getattr(self.fn, v)


@functools.wraps(ThrottledCall)
def throttled_call(*args, **kwargs):
    """
    Wraps the supplied function with ThrottledCall (or generates a
    wrapper with the supplied parameters).
    """
    if args:
        func = args[0]
        args = args[1:]
        if callable(func):
            # mimickry, v3
            return functools.wraps(func)(ThrottledCall(func, *args, **kwargs))
        # else:  # supplied some arguments as positional?
        # TODO: make a warning
        args = (func, *args)

    return lambda func: functools.wraps(func)(ThrottledCall(func, *args, **kwargs))


class LazyStr:
    """
    A simple class for lazy-computed processing into string,
    e.g. for use in logging.

    Example:

        log(13, "stuff is %r",
            lazystr(lambda: ', '.join(stuff)))

    Note: no caching. Use `memoize` if it is needed.
    """

    def __init__(self, fn):
        self.fn = fn

    def __str__(self):
        return str(self.fn())

    def __repr__(self):
        return repr(self.fn())


class LazyRepr:
    """
    Alternative of `lazystr` that does not do additional `repr()`ing, i.e. the
    `func` must return a string.
    """

    def __init__(self, func):
        self.func = func

    def __repr__(self):
        return to_text(self.func())

    def __str__(self):
        return to_text(self.func())


# Helper for o_repr that displays '???'
class ReprObj:
    """A class for inserting specific text in __repr__ outputs."""

    def __init__(self, txt):
        self.txt = txt

    def __repr__(self):
        return self.txt


# _err_obj = type(b'ErrObj', (object,), dict(__repr__=lambda self: '???'))()
_err_obj = ReprObj("???")


# It is similar to using self.__dict__ in repr() but works over dir()
def o_repr_g(
    o,
    *,
    _colors=False,
    _colors256=False,
    _colorvs=None,
    _method=2,
    _private=False,
    _callable=False,
):
    """
    Represent (most of) data on a python object in readable
    way. Useful default for a __repr__.
    WARN: does not handle recursive structures; use carefully.
    """
    # TODO: handle recursive structures (similar to dict.__repr__)
    # TODO: process base types (dict / list / ...) in a special way

    def _color(x16, x256=None):
        if not _colors:
            return ""
        if x16 is None and x256 is None:
            return "\x1b[00m"
        if _colors256 and x256:
            return "\x1b[38;5;" + str(x256) + "m"
        return "\x1b[0" + str(x16) + "m"

    _colorvs_add = _colorvs
    _colorvs = dict(
        base=("1;37", "230"),  # Base (punctuation)  # white / pink-white
        clsn=("1;36", "123"),  # Class name  # bright cyan / cyan-white
        attr=("0;32", "120"),  # Attribute name  # dark-green / green-white
        func=("0;34", "75"),  # Function name  # blue / blue-cyan
        val=("0;37", "252"),  # Value data  # light-gray / light-light-gray
        clear=(None, None),
    )
    _colorvs.update(_colorvs_add or {})

    def _colorv(n):
        return _color(*_colorvs[n])

    yield _colorv("base")
    yield "<"
    yield _colorv("clsn")
    yield str(o.__class__.__name__)
    yield _colorv("base")
    yield "("

    if _method == 3:
        # V3: check type for properties
        o_type = type(o)

    first = True

    for n in sorted(dir(o)):
        # skip 'private' stuff
        if n.startswith("_") and not _private:
            continue

        if first:
            first = False
        else:
            yield _colorv("base")
            yield ", "

        keytype = "attr"
        has_val = True

        # V2: try but fail
        if _method == 2:
            try:
                v = getattr(o, n)
                if callable(v):  # skip functions (... and other callables)
                    if not _callable:
                        has_val = False
                    keytype = "func"
            except Exception:
                v = _err_obj

        if _method == 3:
            # V3: check type for properties
            v_m = getattr(o_type, n, None)
            if v_m is not None and isinstance(v_m, property):
                continue  # skip properties
            v = getattr(o, n)

            # skip functions (... and other callables)
            if callable(v):
                if not _callable:
                    has_val = False
                keytype = "func"

        yield _colorv(keytype)
        yield str(n)  # NOTE: some cases (e.g. functions) will remain just names

        if has_val:
            try:
                v = repr(v)
            except Exception:
                v = _err_obj
            yield _colorv("base")
            yield "="
            yield _colorv("val")
            yield v

    yield _colorv("base")
    yield ")>"
    yield _colorv("clear")


def o_repr(o, **kwa):
    return "".join(o_repr_g(o, **kwa))


class OReprMixin:
    def __repr__(self):
        return o_repr(self)


def stdin_bin_lines(*, strip_newlines=True):
    """Iterate over stdin lines in a 'line-buffered' way"""
    while True:
        try:
            line = sys.stdin.buffer.readline()
        except KeyboardInterrupt:
            # Generally, there's no point in dropping a traceback in a
            # script within an interrupted shell pipe.
            return
        if not line:
            # No more data to read (otherwise it would at least have an "\n")
            break
        # This might not be the case if the stream terminates with a non-newline at the end.
        if strip_newlines and line[-1] == b"\n":
            line = line[:-1]
        yield line


def stdin_lines(*, strip_newlines=True, errors="replace"):
    """Iterate over stdin lines in a 'line-buffered' way"""
    for line_raw in stdin_bin_lines(strip_newlines=strip_newlines):
        line = to_text(line_raw, errors=errors)
        yield line


def stdout_lines(gen, *, flush=True):
    """
    Send lines from a generator / iterable to stdout in a line-buffered way.

    Generally intended to work with text strings rather than bytestrings.
    """
    for line_raw in gen:
        line = to_bytes(line_raw)
        sys.stdout.buffer.write(line)
        sys.stdout.buffer.write(b"\n")
        if flush:
            sys.stdout.flush()


def _sqrt(var):
    """
    Duck-compatible sqrt(), needed to support classes like Decimal.

    Approximately the same as in the `statistics`.
    """
    try:
        return var.sqrt()
    except AttributeError:
        return math.sqrt(var)


def chunks(lst, size):
    """Yield successive chunks from lst. No padding."""
    for idx in range(0, len(lst), size):
        yield lst[idx : idx + size]


def groupby(lst: Iterable[tuple[TKey, TVal]], res_type: Callable[[], dict] = dict) -> dict[TKey, list[TVal]]:
    """
    Groups `[(key, value), ...]` iterable into `{key: [value, ...], ...}` dict.

    >>> groupby([(1, 1), (2, 2), (1, 3)])
    {1: [1, 3], 2: [2]}
    """
    res = res_type()
    for key, val in lst:
        group_list = res.get(key, [])
        if not group_list:
            res[key] = group_list
        group_list.append(val)
    return res


group = groupby  # compat alias


def groupbykey(
    lst: Iterable[TVal], key: Callable[[TVal], TKey] = cast("Callable[[Any], Any]", lambda v: v[0])
) -> dict[TKey, list[TVal]]:
    """
    Groups iterable by key-function result into `{key: [value, ...], ...}` dict.

    Not particularly better than `group((key(val), val) for val in lst)`.
    """
    res: dict[TKey, list[TVal]] = {}
    for item in lst:
        res.setdefault(key(item), []).append(item)
    return res


def mangle_items(items, include=None, exclude=None, add=None, replace=None, replace_inplace=None):
    """
    Functional-style dict editing core (working with a list of pairs).

    >>> items = [(1, 2), (3, 4), (5, 6), (7, 8)]
    >>> mangle_items(items, include=[3, 5], add=[(9, 10)], replace=[(5, 66)])
    [(3, 4), (9, 10), (5, 66)]
    >>> mangle_items(items, include=[3, 5], replace_inplace=[(5, 66)])
    [(3, 4), (5, 66)]
    >>> mangle_items(items, exclude=[3, 7], add=[(9, 10)])
    [(1, 2), (5, 6), (9, 10)]
    """
    include = set(include) if include is not None else None
    exclude = set(exclude) if exclude is not None else None

    if replace is not None:
        if isinstance(replace, dict):
            replace = replace.items()
        add = add + replace
        exclude = exclude if exclude is not None else set()
        exclude = exclude | {key for key, val in replace}

    res = items
    if include is not None:
        res = [(key, val) for key, val in res if key in include]
    if replace_inplace is not None:
        if not isinstance(replace_inplace, dict):
            replace_inplace = dict(replace_inplace)
        res = [(key, replace_inplace.get(key, val)) for key, val in res]
    if exclude is not None:
        res = [(key, val) for key, val in res if key not in exclude]

    # Make sure we end up with a copy in any case:
    if res is items:
        res = list(items)

    # ... functional-style `update`.
    # Almost the `dict(input_dict, **add)`, but better.
    if add is not None:
        if isinstance(add, dict):
            add = add.items()
        res.extend(add)
    return res


def mangle_dict(input_dict, *, include=None, exclude=None, add=None, _return_list=False, dcls=dict):
    """Functional-style dict editing"""
    items = input_dict.items()
    res = mangle_items(items, include=include, exclude=exclude, add=add)
    if _return_list:
        return res
    return dcls(res)


def colorize(text, fmt, outfmt="term", *, lexer_kwa=None, formatter_kwa=None, **kwa):
    """Convenience method for running pygments"""
    from pygments import formatters, highlight, lexers

    _colorize_lexers = dict(
        yaml="YamlLexer",
        diff="DiffLexer",
        py="PythonLexer",
        py3="Python3Lexer",
    )
    _colorize_formatters = dict(
        term="TerminalFormatter",
        term256="Terminal256Formatter",
        html="HtmlFormatter",
    )
    fmt = _colorize_lexers.get(fmt, fmt)
    outfmt = _colorize_formatters.get(outfmt, outfmt)

    lexer_cls = getattr(lexers, fmt)
    formatter_cls = getattr(formatters, outfmt)
    return highlight(text, lexer_cls(**(lexer_kwa or {})), formatter_cls(**(formatter_kwa or {})))


def colorize_yaml(text, **kwa):
    """
    Attempt to colorize the yaml text using pygments (for console
    output)
    """
    return colorize(text, "yaml", **kwa)


def colorize_diff(text, **kwa):
    """
    Attempt to colorize the [unified] diff text using pygments
    (for console output)
    """
    return colorize(text, "diff", **kwa)


def _dict_hashable_1(dct):
    """Simple non-recursive dict -> hashable"""
    return tuple(sorted(dct.items()))


_dict_hashable = _dict_hashable_1


def configurable_wrapper(wrapper_func):
    """
    Wrap a wrapper to make it conveniently configurable.

    The wrapper_func should accept a positional argument
    `func_to_wrap` and optional keyword arguments
    (e.g. `some_func = wrapper_func(some_func, option1=123)`).

    The resulting function accepts optional keyword arguments and
    optional function `func_to_wrap`. If `func_to_wrap` is not
    specified, it returns a wrapper, otherwise it returns a wrapped
    function.

    Saves from the need to remember to write `@wrapper()`, making it
    possible to write both `@wrapper_func` and
    `@wrapper_func(option1=123)`.

    >>> @configurable_wrapper
    ... def wrap_stuff(func, **options):
    ...     def wrapped(*ar, **kwa):
    ...         print("wrapped", func, ar, kwa, "with", options)
    ...         return func(*ar, **kwa)
    ...
    ...     return wrapped
    >>> @wrap_stuff
    ... def some_func(*ar, **kwa):
    ...     print("some_func", ar, kwa)
    >>> some_func(1, 2, b=3)  # doctest: +ELLIPSIS
    wrapped <function some_func at 0x...> (1, 2) {'b': 3} with {}
    some_func (1, 2) {'b': 3}
    >>>
    >>>
    >>> @wrap_stuff(option1="value1")
    ... def another_func(*ar, **kwa):
    ...     print("another_func", ar, kwa)
    >>> another_func(4, 5, c=6)  # doctest: +ELLIPSIS
    wrapped <function another_func at 0x...> (4, 5) {'c': 6} with {'option1': 'value1'}
    another_func (4, 5) {'c': 6}
    """
    # TODO?: use `decorator` module here?

    @functools.wraps(wrapper_func)
    def configurable_wrapper_func(func_to_wrap=None, **options):
        def configured_wrapper_func(func_to_wrap):
            return wrapper_func(func_to_wrap, **options)

        # Cases of `@wrapper_func` and `wrapper_func(func, **options)`
        if func_to_wrap is not None:
            return configured_wrapper_func(func_to_wrap)

        # Case of `wrapper_func(**options)`
        return configured_wrapper_func

    return configurable_wrapper_func


def simple_memoize_argless(func: Callable[..., TRet], *, cache_attr: str = "_cache") -> Callable[..., TRet]:
    """
    A very simple memoizer that saves the first call result permanently
    (ignoring the argument values).
    """
    _cache: dict[None, TRet] = {}
    _sentinel = object()

    @functools.wraps(func)
    def simple_cached_wrapped(*args: Any, **kwargs: Any) -> TRet:
        result = _cache.get(None, _sentinel)
        if result is not _sentinel:
            return cast("TRet", result)

        result = func(*args, **kwargs)
        _cache[None] = result
        return result

    # Make the cache more easily accessible
    if cache_attr:
        setattr(simple_cached_wrapped, cache_attr, _cache)

    return simple_cached_wrapped


# TODO?: some clear-all-global-memos method. By singleton and weakrefs.
class Memoize:
    def __init__(
        self,
        fn,
        timelimit=None,
        *,
        single_value=False,
        force_kwarg="_memoize_force_new",
        timelimit_kwarg="_memoize_timelimit_override",
    ):
        """
        ...

        :param fn: function to memoize.

        :param timelimit: seconds, float: consider the cached value invalid if
        it is older than that.

        :param single_value: keep only one value memoized, i.e. clear the cache
        on function call.
        """
        self.log = logging.getLogger(f"{__name__}.{self!r}")
        self.fn = fn
        self.mem = {}
        self.timelimit = timelimit
        self.single_value = single_value
        self.force_kwarg = force_kwarg
        self.timelimit_kwarg = timelimit_kwarg
        # Internal attribute, for `memoize_method`.
        self.skip_first_arg = False
        functools.update_wrapper(self, fn)

    def memoize_clear_mem(self):
        self.mem.clear()

    def __call__(self, *ar, **kwa):
        now = time.time()  # NOTE: before the call
        override = kwa.pop(self.force_kwarg, False)
        timelimit = kwa.pop(self.timelimit_kwarg, "_")
        if timelimit == "_":
            timelimit = self.timelimit
        # TODO?: cleanup obsolete keys here sometimes.
        try:
            key = (ar[1:], _dict_hashable(kwa)) if self.skip_first_arg else (ar, _dict_hashable(kwa))
            # TODO: make `key` a weakref
            then, res = self.mem[key]
        except KeyError:
            pass
        except TypeError:  # e.g. unhashable args
            self.log.warning("memoize: Trying to memoize unhashable args %r, %r", ar, kwa)
            return self.fn(*ar, **kwa)
        else:
            if override:
                pass  # asked to ignore the cache
            elif timelimit is None or (now - then) < timelimit:
                return res  # valid cache
            else:
                pass  # no valid cache
        # KeyError or obsolete result.
        if self.single_value:
            self.memoize_clear_mem()
        res = self.fn(*ar, **kwa)
        self.mem[key] = (now, res)
        return res


@configurable_wrapper
def memoize_method(func, memo_attr=None, **cfg):
    """
    `memoize` for a method, saving the cache on an instance
    attribute.

    :param memo_attr: name of the attribute to save the cache on.

    :param timelimit: see `memoize`.
    """
    if memo_attr is None:
        # Have to use func id because the func can be subclassed, and
        # will have the same name on the same instance despite
        # different contents. And figuring out the correct class name
        # at this point (like `self.__some_attr` does) is not viable.
        memo_attr = f"_cached_{func.__name__}_{id(func):x}"

    @functools.wraps(func)
    def _memoized_method(self, *c_ar, **c_kwa):
        # Has to be done after the instantiation, to make the cache have the
        # same lifetime as the instance.
        cache = getattr(self, memo_attr, None)
        if cache is None:
            cache = Memoize(func, **cfg)
            cache.skip_first_arg = True
            setattr(self, memo_attr, cache)

        return cache(self, *c_ar, **c_kwa)

    return _memoized_method


def memoized_property(*ar, **cfg):
    """
    Return a property attribute for new-style classes that only calls its getter on the first
    access. The result is stored and on subsequent accesses is returned, preventing the need to
    call the getter any more.

    >>> import time
    >>> class C(object):
    ...     load_name_count = 0
    ...
    ...     @memoized_property
    ...     def name(self):
    ...         '''name's docstring'''
    ...         self.load_name_count += 1
    ...         return "the name"
    ...
    ...     @memoized_property(timelimit=0.0001)
    ...     def timelimited(self):
    ...         time.sleep(0.0005)
    ...         return self.load_name_count
    >>> c = C()
    >>> c.load_name_count
    0
    >>> c.timelimited
    0
    >>> c.name
    'the name'
    >>> c.load_name_count
    1
    >>> c.name
    'the name'
    >>> c.load_name_count
    1
    >>> c.timelimited
    1
    """
    func = None
    if ar and callable(ar[0]):
        func = ar[0]
        ar = ar[1:]

    memoize_method_configured = memoize_method(None, *ar, **cfg)

    def mk_property(a_func):
        return property(memoize_method_configured(a_func))

    if func is not None:
        return mk_property(func)

    return mk_property


memoize_property = memoized_property


def mkdir_p(path):
    """Probably no better than `os.makedirs(path, exist_ok=True)`"""
    try:
        Path(path).mkdir(parents=True)
    except OSError as exc:
        if exc.errno == errno.EEXIST and Path.is_dir(path):
            pass
        else:
            raise


def _dict_to_hashable_json(dct, dumps=json.dumps):
    """
    ...

    NOTE: Not meant to be performant; tends towards collisions.

    Use `id(dct)` for a performant way with the reverse tendency.
    """
    return dumps(dct, skipkeys=True, default=id)


class HashableDictST(dict):
    """sorted-tuple based hashable subclass of `dict`"""

    def __hash__(self):  # type: ignore[override]
        return hash(tuple(sorted(self.items())))


def groupbyany(items, to_hashable=_dict_to_hashable_json):
    """Same as `groupby` but supports dicts as keys (and returns list of items instead of a dict)."""
    annotated = [(to_hashable(key), key, val) for key, val in items]
    hashes = {keyhash: key for keyhash, key, val in annotated}
    groups = groupby((keyhash, val) for keyhash, key, val in annotated).items()
    return [(hashes[keyhash], lst) for keyhash, lst in groups]


def to_bytes(value, default=None, encoding="utf-8", errors="strict"):
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        return value.encode(encoding, errors)
    if default is not None:
        return default(value)
    return value


def to_text(value, default=None, encoding="utf-8", errors="strict"):
    if isinstance(value, str):
        return value
    if isinstance(value, bytes):
        return value.decode(encoding, errors)
    if default is not None:
        return default(value)
    return value


def import_module(name, package=None):
    """`django.utils.importlib.import_module` without the package support"""
    __import__(name)
    return sys.modules[name]


def import_func(func_path, *, _check_callable=True):
    """
    Get an object (e.g. a function / callable) by import path.

    supports '<module>:<path>' notation as well as '<module>.<func_name>'.
    """
    # # Somewhat borrowed from django.core.handlers.base.BaseHandler.load_middleware
    # from django.utils.importlib import import_module

    _exc_cls = Exception

    if ":" in func_path:
        f_module, f_name = func_path.split(":", 1)
    else:
        try:
            f_module, f_name = func_path.rsplit(".", 1)
        except ValueError as exc:
            raise _exc_cls("func_path isn't a path", func_path, exc) from exc

    f_name_parts = f_name.split(".")

    try:
        mod = import_module(f_module)
    except ImportError as exc:
        raise _exc_cls("func_path's module cannot be imported", func_path, exc) from exc

    try:
        here = mod
        for f_name_part in f_name_parts:
            if not f_name_part:
                continue  # allows for weirder things to be done.
            here = getattr(here, f_name_part)
        func = here
    except AttributeError as exc:
        raise _exc_cls("func_path's module does not have the specified func", func_path, exc) from exc

    if _check_callable and not callable(func):
        raise _exc_cls("func does not seem to be a callable", func_path, func)

    return func


def find_files(
    in_dir,
    fname_re=None,
    *,
    older_than=None,
    skip_last=None,
    _prewalk=True,
    strip_dir=False,
    include_base=False,
):
    """
    Return all full file paths under the directory `in_dir` whose
    *filenames* match the `fname_re` regexp (if not None).
    """
    now = time.time()
    TWalkItem = tuple[str, list[str], list[str]]
    TPathPair = tuple[str, str]
    walk: Iterator[TWalkItem] | list[TWalkItem]
    walk = os.walk(in_dir)
    if _prewalk:
        walk = list(walk)
    file_list: list[str] | Iterator[str]
    for dir_name, _, file_list_raw in walk:
        file_list = file_list_raw
        if fname_re is not None:
            file_list = (val for val in file_list if re.match(fname_re, val))

        # Annotate with full path:
        filedir_list: list[TPathPair] | Iterator[TPathPair]
        filedir_list = ((os.path.join(dir_name, file_name), file_name) for file_name in file_list)  # noqa: PTH118

        if strip_dir:
            # Strip the top dir from it
            filedir_list = ((slstrip(fpath, dir_name).lstrip("/"), fname) for fpath, fname in filedir_list)

        if older_than is not None:
            filedir_list = (
                (fpath, fname) for fpath, fname in filedir_list if now - Path(fpath).stat().st_mtime >= older_than
            )

        # Convenience shortcut
        if skip_last:
            filedir_list_l = sorted(filedir_list, key=lambda val: val[1])
            filedir_list = filedir_list_l[: -int(skip_last)]

        if not include_base:
            for _, fname in filedir_list:
                yield fname
        else:
            yield from filedir_list


@Memoize
def get_requests_session():
    """
    Singleton with the common requests session (for maximal connection reuse).

    WARNING: Effectively deprecated; see `pyaux.req`.
    """
    import requests

    return requests.session()


def request(
    url,
    data=None,
    method=None,
    *,
    _w_method="post",
    # Conveniences for overriding:
    _extra_headers=None,
    _extra_params=None,
    _default_host=None,
    # NOTE: using JSON by default here.
    _dataser="json",
    timeout=5,
    _callinfo=True,
    session=True,
    _rfs=False,
    **kwa,
):
    """
    `requests.request` wrapper with conveniences.

    :param session: default session if `True`, new session if `False`, or the specified session.
    :param _w_method: method to use for writing (if `data` or `files` are present).
    :param _dataser: data-dict serialization format (WARN: default is 'json'). 'json' or 'url'.
    :param _callinfo: add the caller file and line to the user-agent.

    WARNING: Effectively deprecated; see `pyaux.req`.
    """
    import requests

    log = logging.getLogger("request")

    # Different default, basically.
    kwa["timeout"] = timeout

    if url.startswith("/"):
        if _default_host is None:
            raise Exception("Must specify _default_host for host-relative URLs")
        if "://" not in _default_host:
            _default_host = f"http://{_default_host}"
        url = urllib.parse.urljoin(_default_host, url)

    params = kwa.get("params") or {}
    if _extra_params:
        params.update(_extra_params)
    kwa["params"] = params

    headers = kwa.get("headers") or {}
    if _extra_headers:
        headers.update(_extra_headers)

    if _callinfo:
        if isinstance(_callinfo, tuple) and len(_callinfo) == 3:
            _cfile, _cline, _cfunc = _callinfo
        else:
            # TODO: custom function, extra_depth param.
            _cfile, _cline, _cfunc, _ = logging.root.findCaller()
        _prev_ua = headers.get("User-Agent") or requests.utils.default_user_agent()
        headers.setdefault("User-Agent", f"{_prev_ua}, {_cfile}:{_cline}: {_cfunc}")

    is_writing = data is not None or kwa.get("files") is not None
    method = method if method is not None else (_w_method if is_writing else "get")
    if method == "get":
        # From requests.get:
        kwa.setdefault("allow_redirects", True)

    # Put them back
    kwa["headers"] = headers

    if session in (0, False, None):
        reqr = requests
    elif session in (1, True):
        reqr = get_requests_session()
    else:
        reqr = session

    if data:
        if isinstance(data, (bytes, str)):
            # Assume the data is already serialised
            pass
        elif _dataser == "json":
            data = json.dumps(data)
            kwa.setdefault("headers", {}).setdefault("content-type", "application/json")
        elif _dataser in ("url", "urlencode", None):
            pass  # pretty much the default in `requests`
        else:
            raise Exception("Unknown _dataser", _dataser)

        kwa["data"] = data
        # TODO?: log a piece of the data?

    # TODO?: put the params either entirely inthe url or entirely in
    # the dict (which shouldn't necessarily be a dict, although MVOD
    # is more convenient)?
    log.info("%s %s  params=%r", method.upper(), url, params)
    resp = reqr.request(method, url, **kwa)

    try:
        elapsed = f"{resp.elapsed.total_seconds():.3f}s"
    except Exception as exc:  # Just in case
        elapsed = f"???({repr(exc)[:32]})"
    # NOTE: assuming that the reponse content is never too large
    log.info(
        "Response: %s %s %s   %db in %s",
        resp.status_code,
        resp.request.method,
        resp.url,
        len(resp.content),
        elapsed,
    )

    if _rfs:
        resp.raise_for_status()

    return resp  # The sufficiently convenient way


def exclogwrap(func=None, name=None, log=logging):
    """
    Wrap the function to exception-log its exceptions.

    Useful for e.g. send_robust signals.
    """

    def exclogwrap_configured(func):
        name_actual = name
        if name_actual is None and func is not None:
            name_actual = repr(func)

        @functools.wraps(func)
        def _wrapped(*ar, **kwa):
            try:
                return func(*ar, **kwa)
            except Exception as exc:
                log.exception("%r failed: %r", name_actual, exc)
                raise

        return _wrapped

    if func is not None:
        return exclogwrap_configured(func)

    return exclogwrap_configured


def repr_cut(some_str, length):
    if len(some_str) <= length:
        return some_str
    return some_str[:length] + "…"


def slstrip(self, substring):
    """
    Strip a substring from the string at left side.
    Similar to `removeprefix` but requires the prefix.
    """
    if not self.startswith(substring):
        val_repr = repr_cut(self, len(substring) * 2)
        raise ValueError(f"Value {val_repr} does not start with substring {substring!r}")
    return self[len(substring) :]


def get_env_flag(name, *, default=False, falses=("0",)):
    """
    Get a boolean flag from os.environ with support for `default`
    and some of the shell trickiness.

    To reset a value in shell, use `unset $name`.
    """
    try:
        value = os.environ[name]
    except KeyError:
        return default
    if value in falses:
        return False
    return value  # Still can be e.g. an empty string.


def current_frame(depth=1):
    """(from logging/__init__.py)"""
    func = getattr(sys, "_getframe", None)
    if func is not None:
        return func(depth)
    # fallback; probably not relevant anymore.
    try:
        raise Exception
    except Exception:  # pylint: disable=broad-except
        _, _, e_tb = sys.exc_info()
        assert e_tb is not None
        frame: FrameType = e_tb.tb_frame
        for _ in range(depth):
            if frame.f_back is not None:
                frame = frame.f_back
        return frame


def find_caller(extra_depth=1, skip_packages=()):
    """
    Find the stack frame of the caller so that we can note the source
    file name, line number and function name.

    Mostly a copypaste from `logging`.

    :param skip_packages: ...; example: `[getattr(logging, '_srcfile', None)]`.
    """
    cur_frame = current_frame(depth=2 + extra_depth)  # our caller, i.e. parent frame
    frame = cur_frame
    # On some versions of IronPython, currentframe() returns None if
    # IronPython isn't run with -X:Frames.
    result = "(unknown file)", 0, "(unknown function)"
    while hasattr(frame, "f_code"):
        codeobj = frame.f_code
        filename = os.path.normcase(codeobj.co_filename)
        # Additionally skip
        if any(filename.startswith(pkg) for pkg in skip_packages if pkg):
            frame = frame.f_back
            continue
        result = (codeobj.co_filename, frame.f_lineno, codeobj.co_name)
        break
    return result


_sh_find_unsafe = re.compile(r"[^\w@%+=:,./-]").search


def sh_quote_prettier(value):
    r"""
    Quote a value for copypasteability in a posix commandline.

    A more readable version than the `shlex.quote`.

    >>> sh_quote_prettier("'one's one'")
    "\\''one'\\''s one'\\'"
    """
    if not value:
        return "''"
    if _sh_find_unsafe(value) is None:
        return value

    # A shorter version: backslash-escaped single quote.
    result = "'" + value.replace("'", "'\\''") + "'"
    # Cleanup the empty excesses at the ends
    _overedge = "''"
    result = result.removeprefix(_overedge)
    return result.removesuffix(_overedge)


if __name__ == "__main__":
    import doctest

    doctest.testmod()
