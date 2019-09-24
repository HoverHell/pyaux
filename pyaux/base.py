# coding: utf8
# pylint: disable=unused-import,wildcard-import,unused-wildcard-import,useless-object-inheritance

# NOTE: no modules imported here should import `decimal` (otherwise
#   `use_cdecimal` might become problematic for them)

from __future__ import absolute_import, print_function

import os
import sys

from copy import deepcopy
import errno
import functools
import itertools
from itertools import chain, repeat, islice
import json
import logging
import math
import re
import time
import traceback
import unicodedata


# Note: no `__all__` here so that for all things defined here, `from pyaux import ...` works too.

from .minisix import PY3, PY_3, text_type, unicode, izip, xrange, reraise

# Compat.
from . import ranges
from .ranges import *

from . import interpolate
from .interpolate import *

from . import iterables
from .iterables import *

from . import monkeys
from .monkeys import *
PY_35 = sys.version_info >= (3, 5)
PY_352 = sys.version_info >= (3, 5, 2)


def bubble(*args, **kwargs):
    """
    Prettified super():
    Calls `super(ThisClass, this_instance).this_method(...)`.

    Not super-performant but quite prettifying ("Performance is 5
    times worse than super() call").

    src:
    http://stackoverflow.com/questions/2706623/super-in-python-2-x-without-args/2706703#2706703
    """
    import inspect

    def find_class_by_code_object(back_self, method_name, code):
        for cls in inspect.getmro(type(back_self)):
            if method_name in cls.__dict__:
                method_fun = getattr(cls, method_name)
                if method_fun.im_func.func_code is code:
                    return cls
        raise Exception("Should not have ended here")

    frame = inspect.currentframe().f_back
    back_self = frame.f_locals['self']
    method_name = frame.f_code.co_name

    for _ in xrange(5):
        code = frame.f_code
        cls = find_class_by_code_object(back_self, method_name, code)
        if cls:
            super_ = super(cls, back_self)
            return getattr(super_, method_name)(*args, **kwargs)
        try:
            frame = frame.f_back
        except Exception:
            return None
    raise Exception("Went too far")


class dotdict(dict):
    """ A simple dict subclass with items also available over attributes """

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            # A little less confusing way:
            _et, _ev, _tb = sys.exc_info()
            reraise(AttributeError, AttributeError(*_ev.args), _tb)

    def __setattr__(self, name, value):
        self[name] = value


# Compat alias
SmartDict = dotdict


_dotdictify_marker = object()


class dotdictify(dict):
    """ Recursive automatic doctdict thingy """

    def __init__(self, value=None):
        if value is None:
            pass
        elif isinstance(value, dict):
            for key in value:
                self.__setitem__(key, value[key])
        else:
            raise TypeError('expected a dict')

    def __setitem__(self, key, value):
        if isinstance(value, dict) and not isinstance(value, dotdictify):
            value = dotdictify(value)
        dict.__setitem__(self, key, value)

    def __getitem__(self, key):
        found = self.get(key, _dotdictify_marker)
        if found is _dotdictify_marker:
            found = dotdictify()
            dict.__setitem__(self, key, found)
        return found

    __setattr__ = __setitem__
    __getattr__ = __getitem__


def repr_call(args, kwargs):
    """ A helper function for pretty-printing a function call arguments """
    res = ', '.join("%r" % (val,) for val in args)
    if kwargs:
        if res:
            res += ', '
        res += ', '.join('%s=%r' % (key, val) for key, val in kwargs.items())
    return res


dbgs = {}   # global object for easier later access of dumped `__call__`s


def DebugPlug(name, mklogger=None):
    """ Create and return a recursive duck-object for plugging in
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

    class DebugPlugInternal(object):
        """ An actual internal class of the DebugPlug """

        def __call__(self, *ar, **kwa):
            log("called with (%s)", repr_call(ar, kwa))
            global dbgs  ## Just to note it
            dbgs.setdefault(name, {})
            dbgs[name]['__call__'] = (ar, kwa)

        def __getattr__(self, attname):
            namef = "%s.%s" % (name, attname)
            # Recursive!
            dpchild = DebugPlug(name=namef, mklogger=mklogger)
            # setattr(self, attname, dpchild)
            object.__setattr__(self, attname, dpchild)
            return dpchild

        def __setattr__(self, attname, value):
            log("setattr: %s = %r", attname, value)
            global dbgs
            dbgs.setdefault(name, {})
            dbgs[name][attname] = value
            return object.__setattr__(self, attname, value)

    return DebugPlugInternal()


# ###### dict-lazies

def dict_fget(D, k, d):
    """ dict_get(D, k, d) -> D[k] if k in D, else d().
      - a lazy-evaluated dict.get.
      (d is mandatory but can be None). """
    if k in D:
        return D[k]
    return d() if d is not None else d


def dict_fsetdefault(D, k, d):
    """ dict_fsetdefault(D, k, d) -> dict_fget(D, k, d), also set D[k]=d() if k not in D.
      - a lazy-evaluated dict.setdefault.
      (d is mandatory but can be None).  """
    # Can be `D[k] = dict_fget(D, k, d); return D[k]`, but let's micro-optimize.
    # NOTE: not going over 'keyerror' for the defaultdict or alike classes.
    if k in D:
        return D[k]
    v = d() if d is not None else d
    D[k] = v
    return v



def split_list(iterable, condition):
    """
    Split list items into `(matching, non_matching)` by `cond(item)` callable.
    """
    matching = []
    non_matching = []
    for item in iterable:
        if condition(item):
            matching.append(item)
        else:
            non_matching.append(item)
    return matching, non_matching


def dict_maybe_items(value):
    items = getattr(value, 'items', None)
    if items is not None:
        return items()
    return value


def split_dict(source, condition, cls=dict):
    source = dict_maybe_items(source)
    matching, nonmatching = split_list(
        source,
        lambda item: condition(item[0], item[1]))
    return cls(matching), cls(nonmatching)


# ...
# TODO: make a recurser that supports and recurses, maintains,
# optionally-replaces various classes such as tuple, defaultdict, and
# other containers. Possibly use pickle/deepcopy's logic.


def obj2dict(obj, add_type=False, add_instance=False, do_lists=True,
             dict_class=dotdict):
    """" Recursive obj -> obj.__dict__ """
    kwa = dict(
        add_type=add_type, add_instance=add_instance,
        do_lists=do_lists, dict_class=dict_class)

    if hasattr(obj, '__dict__'):
        res = dict_class()
        for key, val in obj.__dict__.items():
            res[key] = obj2dict(val, **kwa)
        if add_type:
            res['__class__'] = obj.__class__
        if add_instance:
            res['__instance__'] = obj
        return res

    # Recurse through other types too:
    # NOTE: There might be subclasses of these that would not be
    # processed here.
    if isinstance(obj, dict):
        return dict_class(
            (key, obj2dict(val, **kwa))
            for key, val in obj.items())

    if isinstance(obj, list):
        return [obj2dict(val, **kwa) for val in obj]

    return obj  # something else - return as-is.


def mk_logging_property(actual_name, logger_name='_log'):
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
        getattr(self, logger_name).debug(
            "%s set to %r from %s:%d, in %s",
            actual_name, val, tb[0], tb[1], tb[2])

    return property(do_get, do_set)


def sign(value):
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
    """ 'try parse' (with fn) """
    try:
        return fn(val)
    except Exception:
        return val


# Note: not localized (i.e. always as dot for decimal separator)
_re_alphanum_f = re.compile(r'[0-9]+(?:\.[0-9]+)?|[^0-9]+')


def _split_numeric_f(string):
    return [
        try_parse(val, fn=float)
        for val in _re_alphanum_f.findall(string)]


# Or to avoid interpreting numbers as float:
_re_alphanum_int = re.compile(r'\d+|\D+')


def _split_numeric(string):
    return [
        try_parse(val, fn=int)
        for val in _re_alphanum_int.findall(string)]


# Primary function:
def human_sort_key(string, normalize=unicodedata.normalize, floats=True):
    """ Sorting key for 'human' sorting """
    string = to_text(string)
    string = normalize("NFD", string.lower())
    split_fn = _split_numeric_f if floats else _split_numeric
    return string and split_fn(string)


# ####### ...

class ThrottledCall(object):
    """ Decorator for throttling calls to some functions (e.g. logging).
    Defined as class for various custom attributes and methods.
    Attributes:
      `handle_skip`: function(self, *ar, **kwa) to call when a call is
        skipped. (default: return None)
    Methods: `call_something`
    """

    # _last_call_time = None
    _call_time_throttle = None
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
        doc = "%s (throttled)" % (fn.__doc__,)

        self.__doc__ = doc
        self.__call__.__doc__ = doc
        _f = getattr(self.__call__, '__func__')
        if _f:
            _f.__doc__ = doc
        self.handle_skip = lambda self, *ar, **kwa: None

    def __call__(self, *ar, **kwa):
        return self.call_something(self.fn, *ar, **kwa)

    def call_something(self, fn, *ar, **kwa):
        """ Call some (other) function with the same throttling """
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
        res = fn(*ar, **kwa)
        return res

    def call_value(self, val, fn, *ar, **kwa):
        """ Call if the value hasn't changed (applying the other
        throttling parameters as well). Contains undocumented feature
        """
        if self._call_val != val:
            self._call_val = val
            if fn is None:
                fn = self.fn
            return self.call_something(fn, *ar, **kwa)
        return None

    def __repr__(self):
        return "<throttled_call(%r)>" % (self.fn,)

    # # Optional: mimickry
    # def __repr__(self):
    #     return repr(self.fn)
    # def __getattr__(self, v):
    #     return getattr(self.fn, v)


@functools.wraps(ThrottledCall)
def throttled_call(*args, **kwargs):
    """ Wraps the supplied function with ThrottledCall (or generates a
    wrapper with the supplied parameters). """
    if args:
        func = args[0]
        args = args[1:]
        if callable(func):
            # mimickry, v3
            return functools.wraps(func)(ThrottledCall(func, *args, **kwargs))
        # else:  # supplied some arguments as positional?
        # TODO: make a warning
        args = (func,) + args

    return lambda func: functools.wraps(func)(ThrottledCall(func, *args, **kwargs))


class lazystr(object):
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


class LazyRepr(object):
    """
    Alternative of `lazystr` that does not do additional `repr()`ing, i.e. the
    `func` must return a string.
    """

    def __init__(self, func):
        self.func = func

    def __repr__(self):
        return to_str(self.func())

    def __str__(self):
        return to_str(self.func())

    def __unicode__(self):
        return to_text(self.func())


uniq_g = iterables.uniq  # Compat.


def uniq(lst, key=lambda v: v):  # pylint: disable=function-redefined
    """ RTFS """
    return list(iterables.uniq(lst, key=key))


list_uniq = uniq_g  # Compat.  # pylint: disable=invalid-name


# Helper for o_repr that displays '???'
class ReprObj(object):
    """ A class for inserting specific text in __repr__ outputs.  """

    def __init__(self, txt):
        self.txt = txt

    def __repr__(self):
        return self.txt


# _err_obj = type(b'ErrObj', (object,), dict(__repr__=lambda self: '???'))()
_err_obj = ReprObj('???')


# It is similar to using self.__dict__ in repr() but works over dir()
def o_repr_g(
        o, _colors=False, _colors256=False, _colorvs=None, _method=2,
        _private=False, _callable=False):
    """ Represent (most of) data on a python object in readable
    way. Useful default for a __repr__.
    WARN: does not handle recursive structures; use carefully.  """

    # TODO: handle recursive structures (similar to dict.__repr__)
    # TODO: process base types (dict / list / ...) in a special way

    def _color(x16, x256=None):
        if not _colors:
            return ''
        if x16 is None and x256 is None:
            return '\x1b[00m'
        if _colors256 and x256:
            return '\x1b[38;5;' + str(x256) + 'm'
        return '\x1b[0' + str(x16) + 'm'

    _colorvs_add = _colorvs
    _colorvs = dict(
        base=('1;37', '230'),  # Base (punctuation)  # white / pink-white
        clsn=('1;36', '123'),  # Class name  # bright cyan / cyan-white
        attr=('0;32', '120'),  # Attribute name  # dark-green / green-white
        func=('0;34', '75'),  # Function name  # blue / blue-cyan
        val=('0;37', '252'),  # Value data  # light-gray / light-light-gray
        clear=(None, None),
    )
    _colorvs.update(_colorvs_add or {})

    def _colorv(n):
        return _color(*_colorvs[n])

    yield _colorv("base")
    yield '<'
    yield _colorv("clsn")
    yield str(o.__class__.__name__)
    yield _colorv("base")
    yield '('

    if _method == 3:
        # V3: check type for properties
        o_type = type(o)

    first = True

    for n in sorted(dir(o)):

        # skip 'private' stuff
        if n.startswith('_') and not _private:
            continue

        if first:
            first = False
        else:
            yield _colorv("base")
            yield ', '

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
            yield '='
            yield _colorv("val")
            yield v

    yield _colorv("base")
    yield ')>'
    yield _colorv("clear")


def o_repr(o, **kwa):
    return ''.join(o_repr_g(o, **kwa))


class OReprMixin(object):
    def __repr__(self):
        return o_repr(self)


def stdin_lines(strip_newlines=True):
    """ Iterate over stdin lines in a 'line-buffered' way """
    while True:
        try:
            line = sys.stdin.readline()
        except KeyboardInterrupt:
            # Generally, there's no point in dropping a traceback in a
            # script within an interrupted shell pipe.
            return
        if not line:
            # No more data to read (otherwise it would at least have an "\n")
            break
        # This might not be the case if the stream terminates with a non-newline at the end.
        if strip_newlines and line[-1] == '\n':
            line = line[:-1]
        yield line


def stdout_lines(gen, flush=True):
    """
    Send lines from a generator / iterable to stdout in a line-buffered way.

    Generally intended to work with text strings rather than bytestrings.
    """
    for line in gen:
        if not PY_3:
            line = to_bytes(line)
        sys.stdout.write("%s\n" % (line,))
        if flush:
            sys.stdout.flush()


def dict_merge(target, source, instancecheck=None, dictclass=dict,
               del_obj=object(), _copy=True, inplace=False):
    """ do update() on 'dict of dicts of di...' structure recursively.
    Also, see sources for details.
    NOTE: does not keep target's specific tree structure (forces source's)
    :param del_obj: allows for deletion of keys if the key in the `source` is set to this.

    >>> data = {}
    >>> data = dict_merge(data, {'open_folders': {'my_folder_a': False}})
    >>> data
    {'open_folders': {'my_folder_a': False}}
    >>> data = dict_merge(data, {'open_folders': {'my_folder_b': True}})
    >>> assert data == {'open_folders': {'my_folder_a': False, 'my_folder_b': True}}
    >>> _del = object()
    >>> data = dict_merge(data, {'open_folders': {'my_folder_b': _del}}, del_obj=_del)
    >>> assert data == {'open_folders': {'my_folder_a': False}}
    """
    if instancecheck is None:  # funhorrible ducktypings
        def instancecheck_default(iv):
            return hasattr(iv, 'items')

        instancecheck = instancecheck_default

    # Recursive parameters shorthand
    kwa = dict(instancecheck=instancecheck, dictclass=dictclass, del_obj=del_obj)

    if _copy and not inplace:  # 'both are default'
        target = deepcopy(target)

    for key, val in source.items():
        if val is del_obj:
            target.pop(key, None)
        elif instancecheck(val):  # (val -> source -> items())
            # NOTE: if target[key] wasn't a dict - it will be, now.
            target[key] = dict_merge(
                dict_fget(target, key, dictclass), val, **kwa)
        else:  # nowhere to recurse into - just replace
            # NOTE: if target[key] was a dict - it won't be, anymore.
            target[key] = val

    return target


def _sqrt(var):
    """ Duck-compatible sqrt(), needed to support classes like Decimal.

    Approximately the same as in the python3's `statistics`. """
    try:
        return var.sqrt()
    except AttributeError:
        return math.sqrt(var)


def chunks(lst, size):
    """ Yield successive chunks from lst. No padding.  """
    for idx in xrange(0, len(lst), size):
        yield lst[idx:idx + size]


def group(lst, cls=dict):
    """ RTFS.

    Similar to dict(MultiValueDict(lst).lists())

    >>> group([(1, 1), (2, 2), (1, 3)])
    {1: [1, 3], 2: [2]}
    """
    res = cls()
    for key, val in lst:
        try:
            group_list = res[key]
        except KeyError:
            res[key] = [val]
        else:
            group_list.append(val)
    return res


def group2(lst, key=lambda v: v[0]):
    """ RTFS.

    Not particularly better than `group((key(val), val) for val in lst)`.
    """
    res = {}
    for v in lst:
        res.setdefault(key(v), []).append(v)
    return res.items()


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
        exclude = exclude | set(key for key, val in replace)

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


def mangle_dict(input_dict, include=None, exclude=None, add=None, _return_list=False, dcls=dict):
    """ Functional-style dict editing """
    items = input_dict.items()
    res = mangle_items(items, include=include, exclude=exclude, add=add)
    if _return_list:
        return res
    return dcls(res)


filterdict = mangle_dict


def colorize(text, fmt, outfmt='term', lexer_kwa=None, formatter_kwa=None, **kwa):
    """ Convenience method for running pygments """
    from pygments import highlight, lexers, formatters
    _colorize_lexers = dict(
        yaml='YamlLexer', diff='DiffLexer',
        py='PythonLexer', py2='PythonLexer', py3='Python3Lexer',
    )
    _colorize_formatters = dict(
        term='TerminalFormatter', term256='Terminal256Formatter',
        html='HtmlFormatter',
    )
    fmt = _colorize_lexers.get(fmt, fmt)
    outfmt = _colorize_formatters.get(outfmt, outfmt)

    lexer_cls = getattr(lexers, fmt)
    formatter_cls = getattr(formatters, outfmt)
    return highlight(
        text, lexer_cls(**(lexer_kwa or {})),
        formatter_cls(**(formatter_kwa or {})))


def colorize_yaml(text, **kwa):
    """ Attempt to colorize the yaml text using pygments (for console
    output) """
    return colorize(text, 'yaml', **kwa)


def colorize_diff(text, **kwa):
    """ Attempt to colorize the [unified] diff text using pygments
    (for console output) """
    return colorize(text, 'diff', **kwa)


def _dict_hashable_1(dct):
    """ Simple non-recursive dict -> hashable """
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
    ...     return wrapped
    ...
    >>> @wrap_stuff
    ... def some_func(*ar, **kwa):
    ...     print("some_func", ar, kwa)
    ...
    >>> some_func(1, 2, b=3)  #doctest: +ELLIPSIS
    wrapped <function some_func at 0x...> (1, 2) {'b': 3} with {}
    some_func (1, 2) {'b': 3}
    >>>
    >>>
    >>> @wrap_stuff(option1="value1")
    ... def another_func(*ar, **kwa):
    ...     print("another_func", ar, kwa)
    ...
    >>> another_func(4, 5, c=6)  #doctest: +ELLIPSIS
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


def simple_memoize_argless(func):
    """
    A very simple memoizer that saves the first call result permanently
    (ignoring the argument values).
    """

    _cache = {}
    _sentinel = object()

    @functools.wraps(func)
    def simple_cached_wrapped(*args, **kwargs):
        result = _cache.get(None, _sentinel)
        if result is not _sentinel:
            return result

        result = func(*args, **kwargs)
        _cache[None] = result
        return result

    # Make the cache more easily accessible
    simple_cached_wrapped._cache = _cache
    return simple_cached_wrapped


# TODO?: some clear-all-global-memos method. By singleton and weakrefs.
class memoize(object):

    def __init__(
            self, fn, timelimit=None, single_value=False,
            force_kwarg='_memoize_force_new', timelimit_kwarg='_memoize_timelimit_override'):
        """
        ...

        :param fn: function to memoize.

        :param timelimit: seconds, float: consider the cached value invalid if
        it is older than that.

        :param single_value: keep only one value memoized, i.e. clear the cache
        on function call.
        """
        self.log = logging.getLogger("%s.%r" % (__name__, self))
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
            if self.skip_first_arg:
                key = (ar[1:], _dict_hashable(kwa))
            else:
                key = (ar, _dict_hashable(kwa))
            # XXX/TODO: make `key` a weakref
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
    """ `memoize` for a method, saving the cache on an instance
    attribute.

    :param memo_attr: name of the attribute to save the cache on.

    :param timelimit: see `memoize`.
    """

    if memo_attr is None:
        # Have to use func id because the func can be subclassed, and
        # will have the same name on the same instance despite
        # different contents. And figuring out the correct class name
        # at this point (like `self.__some_attr` does) is not viable.
        memo_attr = '_cached_%s_%x' % (func.__name__, id(func))

    @functools.wraps(func)
    def _memoized_method(self, *c_ar, **c_kwa):
        # Has to be done after the instantiation, to make the cache have the
        # same lifetime as the instance.
        cache = getattr(self, memo_attr, None)
        if cache is None:
            cache = memoize(func, **cfg)
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
    ...     @memoized_property
    ...     def name(self):
    ...         ''' name's docstring '''
    ...         self.load_name_count += 1
    ...         return "the name"
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
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def _dict_to_hashable_json(dct, dumps=json.dumps):
    """ ...

    NOTE: Not meant to be performant; tends towards collisions.

    Use `id(dct)` for a performant way with the reverse tendency.
    """
    return dumps(dct, skipkeys=True, default=id)


class hashabledict_st(dict):
    """ sorted-tuple based hashable subclass of `dict` """
    def __hash__(self):
        return hash(tuple(sorted(list(self.items()))))


def group3(items, to_hashable=_dict_to_hashable_json):
    """ Same as `group` but supports dicts as keys (and returns list
    of pairs) """
    annotated = [(to_hashable(key), key, val) for key, val in items]
    hashes = dict((keyhash, key) for keyhash, key, val in annotated)
    groups = group((keyhash, val) for keyhash, key, val in annotated).items()
    return [(hashes[keyhash], lst) for keyhash, lst in groups]


def to_bytes(value, default=None, encoding='utf-8', errors='strict'):
    if isinstance(value, bytes):
        return value
    if isinstance(value, text_type):
        return value.encode(encoding, errors)
    if default is not None:
        return default(value)
    return value


def to_text(value, default=None, encoding='utf-8', errors='strict'):
    if isinstance(value, text_type):
        return value
    if isinstance(value, bytes):
        return value.decode(encoding, errors)
    if default is not None:
        return default(value)
    return value


to_unicode = to_text  # legacy name  # pylint: disable=invalid-name


if PY_3:
    to_str = to_text  # pylint: disable=invalid-name
else:
    to_str = to_bytes  # pylint: disable=invalid-name


def import_module(name, package=None):
    """ ...

    django.utils.importlib.import_module without the package support
    """
    __import__(name)
    return sys.modules[name]


def import_func(func_path, _check_callable=True):
    """ Get an object (e.g. a function / callable) by import path.

    supports '<module>:<path>' notation as well as '<module>.<func_name>'.
    """
    # # Somewhat borrowed from django.core.handlers.base.BaseHandler.load_middleware
    # from django.utils.importlib import import_module

    _exc_cls = Exception

    if ':' in func_path:
        f_module, f_name = func_path.split(':', 1)
    else:
        try:
            f_module, f_name = func_path.rsplit('.', 1)
        except ValueError as exc:
            raise _exc_cls("func_path isn't a path", func_path, exc)

    f_name_parts = f_name.split('.')

    try:
        mod = import_module(f_module)
    except ImportError as exc:
        raise _exc_cls("func_path's module cannot be imported", func_path, exc)

    try:
        here = mod
        for f_name_part in f_name_parts:
            if not f_name_part:
                continue  ## allows for weirder things to be done.
            here = getattr(here, f_name_part)
        func = here
    except AttributeError as exc:
        raise _exc_cls("func_path's module does not have the specified func", func_path, exc)

    if _check_callable and not callable(func):
        raise _exc_cls("func does not seem to be a callable", func_path, func)

    return func


def dict_is_subset(
        smaller_obj,
        larger_obj,
        recurse_iterables=False,
        require_structure_match=True):
    """ Recursive check "smaller_dict's keys are subset of
    larger_dict's keys.

    NOTE: in practice, supports non-dict values at top.

    >>> value = {"a": 1, "b": [2, {"c": 3, "d": None}]}
    >>> dict_is_subset({}, value)
    True
    >>> dict_is_subset({"a": 1}, value)
    True
    >>> dict_is_subset({"a": 2}, value)
    False
    >>> dict_is_subset({"a": {"x": 4}}, value, require_structure_match=False)
    True
    >>> dict_is_subset({"b": [2]}, value, recurse_iterables=False)
    False
    >>> dict_is_subset({"b": [2]}, value, recurse_iterables=True, require_structure_match=True)
    False
    >>> dict_is_subset({"b": [2]}, value, recurse_iterables=True, require_structure_match=False)
    True
    >>> dict_is_subset({"b": [2, {}]}, value, recurse_iterables=True)
    True
    >>> dict_is_subset({"b": [2, {"c": 3}]}, value, recurse_iterables=True)
    True
    >>> dict_is_subset({"b": [2, {"c": 4}]}, value, recurse_iterables=True)
    False
    """
    kwa = dict(
        recurse_iterables=recurse_iterables,
        require_structure_match=require_structure_match,
    )
    if isinstance(smaller_obj, dict):
        if not isinstance(larger_obj, dict):
            return False if require_structure_match else True

        # Both are dicts.
        for key, val in smaller_obj.items():
            try:
                lval = larger_obj[key]
            except KeyError:
                return False
            # 'compare' the values whatever they are
            if not dict_is_subset(val, lval, **kwa):
                return False

        return True

    # else:
    if recurse_iterables and hasattr(smaller_obj, '__iter__'):
        if not hasattr(larger_obj, '__iter__'):
            return False if require_structure_match else True
        # smaller_value_iter, larger_value_iter
        svi = iter(smaller_obj)
        lvi = iter(larger_obj)
        for sval, lval in izip(svi, lvi):
            if not dict_is_subset(sval, lval, **kwa):
                return False
        if require_structure_match:
            if not iterator_is_over(svi) or not iterator_is_over(lvi):
                # One of the iterables was longer and thus was not
                # consumed entirely by the izip
                return False
        return True

    # else:
    # elif not dict or iterable:
    return smaller_obj == larger_obj


def find_files(
        in_dir, fname_re=None, older_than=None, skip_last=None,
        _prewalk=True, strip_dir=False, include_base=False):
    """ Return all full file paths under the directory `in_dir` whose
    *filenames* match the `fname_re` regexp (if not None) """
    now = time.time()
    walk = os.walk(in_dir)
    if _prewalk:
        walk = list(walk)
    for dir_name, _, file_list in walk:
        if fname_re is not None:
            file_list = (val for val in file_list if re.match(fname_re, val))

        # Annotate with full path:
        file_list = (
            (os.path.join(dir_name, file_name), file_name)
            for file_name in file_list)

        if strip_dir:
            # Strip the top dir from it
            file_list = (
                (slstrip(fpath, dir_name).lstrip('/'), fname)
                for fpath, fname in file_list)

        if older_than is not None:
            file_list = (
                (fpath, fname) for fpath, fname in file_list
                if now - os.path.getmtime(fpath) >= older_than)

        # Convenience shortcut
        if skip_last:
            file_list = sorted(list(file_list), key=lambda val: val[1])
            file_list = file_list[:-int(skip_last)]

        if not include_base:
            file_list = (fpath for fpath, fname in file_list)

        for res_val in file_list:
            yield res_val


@memoize
def get_requests_session():
    """
    Singleton with the common requests session (for maximal connection reuse).

    WARNING: Effectively deprecated; see `pyaux.req`.
    """
    import requests
    return requests.session()


def request(
        url, data=None,
        method=None, _w_method='post',
        # Conveniences for overriding:
        _extra_headers=None, _extra_params=None, _default_host=None,
        # NOTE: using JSON by default here.
        _dataser='json', timeout=5,
        _callinfo=True, session=True, _rfs=False, **kwa):
    """ requests.request wrapper with conveniences.

    :param session: default session if `True`, new session if `False`, or the specified session.
    :param _w_method: method to use for writing (if `data` or `files` are present).
    :param _dataser: data-dict serialization format (WARN: default is 'json'). 'json' or 'url'.
    :param _callinfo: add the caller file and line to the user-agent.

    WARNING: Effectively deprecated; see `pyaux.req`.
    """
    import requests
    from .minisix import urllib_parse
    log = logging.getLogger('request')

    # Different default, basically.
    kwa['timeout'] = timeout

    if url.startswith('/'):
        if _default_host is None:
            raise Exception("Must specify _default_host for host-relative URLs")
        if '://' not in _default_host:
            _default_host = 'http://%s' % _default_host
        url = urllib_parse.urljoin(_default_host, url)

    params = kwa.get('params') or {}
    if _extra_params:
        params.update(_extra_params)
    kwa['params'] = params

    headers = kwa.get('headers') or {}
    if _extra_headers:
        headers.update(_extra_headers)

    if _callinfo:
        if isinstance(_callinfo, tuple) and len(_callinfo) == 3:
            _cfile, _cline, _cfunc = _callinfo
        else:
            # TODO: custom function, extra_depth param.
            _cfile, _cline, _cfunc = logging.Logger('').findCaller()
        _prev_ua = headers.get('User-Agent') or requests.utils.default_user_agent()
        headers.setdefault('User-Agent', '%(ua)s, %(cfile)s:%(cline)s: %(cfunc)s' % dict(
            ua=_prev_ua, cfile=_cfile, cline=_cline, cfunc=_cfunc))

    is_writing = data is not None or kwa.get('files') is not None
    method = method if method is not None else (
        _w_method if is_writing else 'get')
    if method == 'get':
        # From requests.get:
        kwa.setdefault('allow_redirects', True)

    # Put them back
    kwa['headers'] = headers

    if session in (0, False, None):
        reqr = requests
    elif session in (1, True):
        reqr = get_requests_session()
    else:
        reqr = session

    if data:
        if isinstance(data, (bytes, unicode)):
            # Assume the data is already serialised
            pass
        elif _dataser == 'json':
            data = json.dumps(data)
            kwa.setdefault("headers", {}).setdefault("content-type", "application/json")
        elif _dataser in ('url', 'urlencode', None):
            pass  # pretty much the default in `requests`
        else:
            raise Exception("Unknown _dataser", _dataser)

        kwa['data'] = data
        # TODO?: log a piece of the data?

    # TODO?: put the params either entirely inthe url or entirely in
    # the dict (which shouldn't necessarily be a dict, although MVOD
    # is more convenient)?
    log.info("%s %s  params=%r", method.upper(), url, params)
    resp = reqr.request(method, url, **kwa)

    try:
        elapsed = '%.3fs' % (resp.elapsed.total_seconds(),)
    except Exception as exc:  # Just in case
        elapsed = '???(%s)' % (repr(exc)[:32],)
    # NOTE: assuming that the reponse content is never too large
    log.info(
        "Response: %s %s %s   %db in %s",
        resp.status_code, resp.request.method, resp.url, len(resp.content), elapsed)

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
    return some_str[:length] + (u'…' if isinstance(some_str, unicode) else '…')


def slstrip(self, substring):
    """ Strip a substring from the string at left side """
    if not self.startswith(substring):
        raise ValueError("Value %r does not start with substring %r" % (
            repr_cut(self, len(substring) * 2), substring))
    return self[len(substring):]


def get_env_flag(name, default=False, falses=('0',)):
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
    """
    (from logging/__init__.py)
    """
    func = getattr(sys, '_getframe', None)
    if func is not None:
        return func(depth)
    # fallback; probably not relevant anymore.
    try:
        raise Exception
    except Exception:  # pylint: disable=broad-except
        frame = sys.exc_info()[2].tb_frame
        for _ in range(depth):
            frame = frame.f_back


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


try:
    monotonic_now = time.monotonic
except Exception:
    try:
        import monotonic  # pylint: disable=import-error
        monotonic_now = monotonic.monotonic
    except Exception:
        # No proper implementation available.
        monotonic_now = time.time


if __name__ == '__main__':
    import doctest
    doctest.testmod()
