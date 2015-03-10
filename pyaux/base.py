# coding: utf8
## NOTE: no modules imported here should import `decimal` (otherwise
##   `use_cdecimal` might become problematic for them)


__all__ = [
    'bubble',
    'window',
    'dotdict',
    'SmartDict',
    'DebugPlug', 'repr_call',
    'fxrange', 'frange', 'dxrange', 'drange',
    'dict_fget',
    'dict_fsetdefault',
    'interp',
    'edi', 'InterpolationEvaluationException',
    'split_list',
    'use_cdecimal',
    'use_exc_ipdb',
    'use_exc_log',
    'use_colorer',
    'obj2dict',
    'mk_logging_property',
    'sign',
    'try_parse',
    'human_sort_key',
    'reversed_blocks',
    'reversed_lines',
    'lazystr',
    'list_uniq',
    'o_repr',
    'chunks',
    'chunks_g',
    # 'runlib',
    # 'lzmah',
    # 'lzcat',
    # 'psql',
]


import os
import sys
import inspect
import six

import math
import time
import functools
from itertools import chain, repeat, islice
import traceback
import re


def bubble(*args, **kwargs):
    """ Prettified super():
    Call `super(ThisClass, this_instance).this_method(...)`.
    Not super-performant but quite prettifying ("Performance is 5 times
      worse than super() call")
    src: http://stackoverflow.com/questions/2706623/super-in-python-2-x-without-args/2706703#2706703
    """
    def find_class_by_code_object(back_self, method_name, code):
        for cls in inspect.getmro(type(back_self)):
            if method_name in cls.__dict__:
                method_fun = getattr(cls, method_name)
                if method_fun.im_func.func_code is code:
                    return cls

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
            return


## Iterate over a 'window' of adjacent elements
## http://stackoverflow.com/questions/6998245/iterate-over-a-window-of-adjacent-elements-in-python
def window(seq, size=2, fill=0, fill_left=False, fill_right=False):
    """ Returns a sliding window (of width n) over data from the iterable:
      s -> (s0,s1,...s[n-1]), (s1,s2,...,sn), ...
    """
    ssize = size - 1
    it = chain(
        repeat(fill, ssize * fill_left),
        iter(seq),
        repeat(fill, ssize * fill_right))
    result = tuple(islice(it, size))
    if len(result) == size:  # `<=` if okay to return seq if len(seq) < size
        yield result
    for elem in it:
        result = result[1:] + (elem,)
        yield result


class dotdict(dict):
    """ A simple dict subclass with items also available over attributes """

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            ## A little less confusing way:
            _et, _ev, _tb = sys.exc_info()
            six.reraise(AttributeError, _ev, _tb)

    def __setattr__(self, name, value):
        self[name] = value


## Compat alias
SmartDict = dotdict


def repr_call(ar, kwa):
    """ A helper function for pretty-printing a function call arguments """
    r = ', '.join("%r" % (v,) for v in ar)
    if kwa:
        r += ', ' + ', '.join('%s=%r' % (k, v) for k, v in kwa.iteritems())
    return r


dbgs = {}   # global object for easier later access of dumped `__call__`s


def DebugPlug(name, mklogger=None):
    """ Create and return a recursive duck-object for plugging in
    place of other objects for debug purposes.

    :param name: name for tracking the object and its (child) attributes.

    :param mklogger: a function of `name` (str) that returns a new callable(msg:
      str) used for logging.  See code for an example.
    """
    ## The construction with mkClass is for removing the need of
    ##   `__getattr__`ing the name and logger.
    import logging

    def mklogger_default(name):
        logger = logging.getLogger(name)
        return logger.debug

    if mklogger is None:
        mklogger = mklogger_default

    log = mklogger(name)

    class DebugPlugInternal(object):
        """ An actual internal class of the DebugPlug """

        def __call__(self, *ar, **kwa):
            log("called with (%s)" % repr_call(ar, kwa))
            global dbgs  ## Just to note it
            dbgs.setdefault(name, {})
            dbgs[name]['__call__'] = (ar, kwa)

        def __getattr__(self, attname):
            namef = "%s.%s" % (name, attname)
            ## Recursive!
            dpchild = DebugPlug(name=namef, mklogger=mklogger)
            #setattr(self, attname, dpchild)
            object.__setattr__(self, attname, dpchild)
            return dpchild

        def __setattr__(self, attname, value):
            log("setattr: %s = %r" % (attname, value))
            global dbgs
            dbgs.setdefault(name, {})
            dbgs[name][attname] = value
            return object.__setattr__(self, attname, value)

    return DebugPlugInternal()


#######
## `range`-like things
#######


def fxrange(start, end=None, inc=None):
    """ The xrange function for float """
    assert inc != 0, "inc should not be zero"
    if end is None:
        end = start
        start = 0.0
    if inc is None:
        inc = 1.0
    i = 0  # to prevent error accumulation
    while True:
        nextv = start + i * inc
        if (inc > 0 and nextv >= end
                or inc < 0 and nextv <= end):
            break
        yield nextv
        i += 1


def frange(start, end=None, inc=None):
    """ list(fxrange) """
    return list(fxrange(start, end, inc))


def dxrange(start, end=None, inc=None, include_end=False):
    """ The xrange function for Decimal """
    # Imported here mostly because of use_cdecimal in this module
    from decimal import Decimal
    assert inc != 0, "inc should not be zero"
    if end is None:
        end = start
        start = 0
    if inc is None:
        inc = 1
    inc = Decimal(inc)
    start = Decimal(start)
    end = Decimal(end)
    nextv = start
    while True:
        if ((inc > 0) and (not include_end and nextv == end or nextv > end)
                or (inc < 0) and (not include_end and nextv == end or nextv < end)):
            break
        yield nextv
        nextv += inc


def drange(*ar, **kwa):
    """ list(dxrange) """
    return list(dxrange(*ar, **kwa))


def date_xrange(start, end, inc=None, include_end=False, precise=False):
    """ The xrange function for datetime.

    NOTE: the semantics of 'start' and 'end' are different here: with
    end=None an infinite generator is returned.

    :param precise: do more calculations but potentially produce more
        precise results (especially for precise `inc`).

    >>> import datetime
    >>> dt = datetime.datetime
    >>> dta = dt(2011, 11, 11)
    >>> dtb = dt(2011, 11, 14)
    >>> dsl = lambda dtl: [dt.strftime('%Y-%m-%d') for dt in dtl]
    >>> dtsl = lambda dtl: [dt.isoformat() for dt in dtl]
    >>> dsl(date_xrange(dta, dt(2011, 11, 13)))
    ['2011-11-11', '2011-11-12']
    >>> dsl(date_xrange(dta, dt(2011, 11, 13), include_end=True))
    ['2011-11-11', '2011-11-12', '2011-11-13']
    >>> dsl(date_xrange(dta, dtb, inc=2))
    ['2011-11-11', '2011-11-13']
    >>> dtsl(date_xrange(dta, dtb, inc=1111.11111111111 / 86400, precise=True))[-1]
    '2011-11-13T23:54:48.888889'
    >>> dtsl(date_xrange(dta, dtb, inc=1111.11111111111 / 86400))[-1]
    '2011-11-13T23:54:48.888863'
    """
    import datetime
    if inc is None:
        inc = 1  # default: 1 day

    if not isinstance(inc, datetime.timedelta):
        # NOTE: days, by default
        inc_days = inc
        inc = datetime.timedelta(inc)
    else:
        inc_days = inc.total_seconds() / 86400  # py2.7 required

    assert inc_days  # should be nonzero

    is_forward = (inc_days > 0)

    idx = 0
    current = start
    while True:
        if end is not None:
            if include_end:
                to_break = current > end if is_forward else current < end
            else:
                to_break = current >= end if is_forward else current <= end
            if to_break:
                break
        yield current
        if precise:
            idx += 1
            current = start + datetime.timedelta(inc_days * idx)
        else:
            current = current + inc


def date_range(*ar, **kwa):
    """ list(date_xrange) """
    return list(date_xrange(*ar, **kwa))


def date_add_months(sourcedate, months=1):
    """ Add months to date; can cap the day to the maximal value for
    the month """
    import calendar
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    day = min(sourcedate.day, calendar.monthrange(year, month)[1])
    # return datetime.date(year, month, day)
    # On the other hand, we can keep the type and the time:
    return sourcedate.replace(year=year, month=month, day=day)


def date_months_xrange(start, end, inc=1, include_end=False):
    """ date_range with delta measured in months.

    Similar semantics to date_xrange.
    Only accepts integer `inc` values.

    >>> import datetime
    >>> dt = datetime.datetime
    >>> dsl = lambda dtl: [dt.strftime('%Y-%m-%d') for dt in dtl]
    >>> dsl(date_months_xrange(dt(2011, 10, 31), dt(2012, 1, 1)))
    ['2011-10-31', '2011-11-30', '2011-12-31']
    """
    assert isinstance(inc, int)
    inc = int(inc)
    assert inc  # should be nonzero
    is_forward = inc > 0
    current = start
    idx = 0
    while True:
        if end is not None:
            if include_end:
                to_break = current > end if is_forward else current < end
            else:
                to_break = current >= end if is_forward else current <= end
            if to_break:
                break
        yield current
        idx += 1
        current = date_add_months(start, months=inc * idx)


def date_months_range(*ar, **kwa):
    """ list(date_months_xrange) """
    return list(date_months_xrange(*ar, **kwa))


####### dict-lazies

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
    ## Can be `D[k] = dict_fget(D, k, d); return D[k]`, but let's micro-optimize.
    if k in D:
        return D[k]
    v = d() if d is not None else d
    D[k] = v
    return v


####### String interpolation

## http://rightfootin.blogspot.com/2007/02/string-interpolation-in-python.html
def interp(string, _regexp=r'(#\{([^}]*)\})'):
    """ Inline string interpolation.
    >>> var1 = 213; ff = lambda v: v**2
    >>> interp("var1 is #{var1}")
    'var1 is 213'
    >>> interp("var1 is #{ff(var1)}; also #{ff(12)}")
    'var1 is 45369; also 144'
    """
    fframe = sys._getframe(1)
    flocals = fframe.f_locals
    fglobals = fframe.f_globals
    items = re.findall(_regexp, string)
    item_to_str = {}
    ## Do eval and replacement separately and replacement in one regex
    ## go to avoid interpolating already interpolated values.
    for item_outer, item in items:
        item_to_str[item] = str(eval(item, fglobals, flocals))
    string = re.sub(_regexp, lambda match: item_to_str[match.group(2)], string)
    return string


## Yet another string-interpolation helper
class InterpolationEvaluationException(KeyError):
    pass


class edi(dict):  # "expression_dictionary"...
    """ Yet another string interpolation helper.

    >>> var1 = 313; f = lambda x: x*2
    >>> print "1 is %(var1)5d, f1 is %(f(var1))d, f is %(f)r, 1/2 is %(float(var1)/2)5.3f." % edi()  #doctest: +ELLIPSIS
    1 is   313, f1 is 626, f is <function <lambda> at 0x...>, 1/2 is 156.500.

    """
    ## No idea for what sake this is subclassed from dictionary, actually. A
    ## neat extra, perhaps.

    globals = {}

    def __init__(self, d=None):
        if d is None:  # Grab parent's locals forcible
            self.locals = sys._getframe(1).f_locals
            self.globals = sys._getframe(1).f_globals
            d = self.locals
        super(edi, self).__init__(d)

    def __getitem__(self, key):
        try:
            return dict.__getitem__(self, key)
        except KeyError:
            try:
                return eval(key, self.globals, self)
            except Exception, e:
                raise InterpolationEvaluationException(key, e)


####### ...

def split_list(lst, cond):
    """ Split list items into two into (matching, non_matching) by
      `cond(item)` callable """
    res1, res2 = [], []
    for i in lst:
        if cond(i):
            res1.append(i)
        else:
            res2.append(i)
    return res1, res2


####### Monkey-patching of various things:

def use_cdecimal():
    """ Do a hack-in replacement of `decimal` with `cdecimal`.
    Should be done before importing other modules.  """
    import decimal  # maybe not needed
    import cdecimal
    sys.modules['decimal'] = cdecimal


def use_exc_ipdb():
    """ Set unhandled exception handler to automatically start ipdb """
    import pyaux.exc_ipdb as exc_ipdb
    exc_ipdb.init()


def use_exc_log():
    """ Set unhandled exception handler to verbosely log the exception """
    import pyaux.exc_log as exc_log
    exc_log.init()


def use_colorer():
    """ Wrap logging's StreamHandler.emit to add colors to the logged
      messages based on log level """
    import pyaux.Colorer as Colorer
    Colorer.init()


def obj2dict(o, add_type=False, add_instance=False, do_lists=True,
             dict_class=dotdict):
    """" Recursive o -> o.__dict__ """
    kwa = dict(add_type=add_type, add_instance=add_instance,
               do_lists=do_lists, dict_class=dict_class)

    if hasattr(o, '__dict__'):
        res = dict_class()
        for k, v in o.__dict__.iteritems():
            res[k] = obj2dict(v, **kwa)
        if add_type:
            res['__class__'] = o.__class__
        if add_instance:
            res['__instance__'] = o
        return res
    ## Recurse through other types too:
    ## NOTE: There might be subclasses of these that would not be processed
    ##   here
    elif isinstance(o, dict):
        return dict_class((k, obj2dict(v, **kwa)) for k, v in o.iteritems())
    elif isinstance(o, list):
        return [obj2dict(v, **kwa) for v in o]

    return o  # something else - return as-is.


def mk_logging_property(actual_name, logger_name='_log'):
    """ Creates a property that logs the value and the caller in the
    setter, using logger under `self`'s logger_name, and stores the value
    under actual_name on `self` """

    def do_get(self):
        return getattr(self, actual_name)

    def do_set(self, val):
        tb = traceback.extract_stack(limit=2)[0]
        ## or:
        #next((r.f_code.co_filename, r.f_lineno, r.f_code.co_name) for r in (sys._getframe(1),))
        ## that is,
        #r = sys._getframe(1)
        #co = r.f_code
        #co.co_filename, r.f_lineno, co.co_name
        setattr(self, actual_name, val)
        getattr(self, logger_name).debug(
            "%s set to %r from %s:%d, in %s",
            actual_name, val, tb[0], tb[1], tb[2])

    return property(do_get, do_set)


def sign(v):
    """ Sign of value: `return cmp(v, 0)` """
    return cmp(v, 0)


#######  "Human" sorting, advanced
# partially from quodlibet/quodlibet/util/__init__.py
# partially from comix/src/filehandler.py

import unicodedata


def try_parse(v, fn=int):
    """ 'try parse' (with fn) """
    try:
        return fn(v)
    except Exception, e:
        return v


## Note: not localized (i.e. always as dot for decimal separator)
_re_alphanum_f = re.compile(r'[0-9]+(?:\.[0-9]+)?|[^0-9]+')


def _split_numeric_f(s):
    return [try_parse(v, fn=float) for v in _re_alphanum_f.findall(s)]


## Or to avoid interpreting numbers as float:
_re_alphanum_int = re.compile(r'\d+|\D+')


def _split_numeric(s):
    return [try_parse(v, fn=int) for v in _re_alphanum_int.findall(s)]


## Primary function:
def human_sort_key(s, normalize=unicodedata.normalize, floats=True):
    """ Sorting key for 'human' sorting """
    if not isinstance(s, unicode):
        s = s.decode("utf-8")
    s = normalize("NFD", s.lower())
    split_fn = _split_numeric_f if floats else _split_numeric
    return s and split_fn(s)


####### Reading files backwards
## http://stackoverflow.com/a/260433/62821

def reversed_blocks(fileobj, blocksize=4096):
    """ Generate blocks of file's contents in reverse order.  """
    fileobj.seek(0, os.SEEK_END)
    here = fileobj.tell()
    while 0 < here:
        delta = min(blocksize, here)
        fileobj.seek(here - delta, os.SEEK_SET)
        yield fileobj.read(delta)
        here -= delta


def reversed_lines(fileobj):
    """ Generate the lines of file in reverse order.  """
    tail = []           # Tail of the line whose head is not yet read.
    for block in reversed_blocks(fileobj):
        # A line is a list of strings to avoid quadratic concatenation.
        # (And trying to avoid 1-element lists would complicate the code.)
        linelists = [[line] for line in block.splitlines()]
        linelists[-1].extend(tail)
        for linelist in reversed(linelists[1:]):
            yield ''.join(linelist)
        tail = linelists[0]
    if tail:
        yield ''.join(tail)


######## ...

class ThrottledCall(object):
    """ Decorator for throttling calls to some functions (e.g. logging).
    Defined as class for various custom attributes and methods.
    Attributes:
      `handle_skip`: function(self, *ar, **kwa) to call when a call is
        skipped. (default: return None)
    Methods: `call_something`
    """

    #_last_call_time = None
    _call_time_throttle = None
    _call_cnt = 0  # (kept accurate; but can become ineffectively large)
    _call_cnt_throttle = 0  # next _call_cnt to call at
    _call_val = object()  # (some unique value at start)

    def __init__(self, fn=None, sec_limit=None, cnt_limit=None):
        """ `fn`: function to call (can be customized later).
        `sec_limit`: skip call if less than `sec_limit` seconds since the
          last call
        `cnt_limit`: call only once each `cnt_limit` calls
        """
        self.fn = fn
        # mimickry, v2
        #self.__call__ = wraps(fn)(self.__call__)
        self.sec_limit = sec_limit
        self.cnt_limit = cnt_limit
        doc = "%s (throttled)" % (fn.__doc__,)
        self.__call__.__func__.__doc__ = self.__doc__ = doc
        self.handle_skip = lambda self, *ar, **kwa: None

    def __call__(self, *ar, **kwa):
        return self.call_something(self.fn, *ar, **kwa)

    def call_something(self, fn, *ar, **kwa):
        """ Call some (other) function with the same throttling """
        now = time.time()
        #do_call = True
        ## NOTE: `throttle_cnt(throttle_sec(fn))` is emulated if both are
        ##   set.
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

    def __repr__(self):
        return "<throttled_call(%r)>" % (self.fn,)

    ## Optional: mimickry
    #def __repr__(self):
    #    return repr(self.fn)
    #def __getattr__(self, v):
    #    return getattr(self.fn, v)


@functools.wraps(ThrottledCall)
def throttled_call(fn=None, *ar, **kwa):
    """ Wraps the supplied function with ThrottledCall (or generates a
    wrapper with the supplied parameters). """
    if fn is not None:
        if callable(fn):
            # mimickry, v3
            return functools.wraps(fn)(ThrottledCall(fn, *ar, **kwa))
        else:  # supplied some arguments as positional?
            ## XX: make a warning?
            ar = (fn,) + ar
    return lambda fn: functools.wraps(fn)(ThrottledCall(fn, *ar, **kwa))


class lazystr(object):
    """ A simple class for lazy-computed processing into string,
      e.g. for use in logging.
    Example: `log(13, "stuff is %r",
      lazystr(lambda: ', '.join(stuff)))`
    Note: no caching.
    """

    def __init__(self, fn):
        self.fn = fn

    def __str__(self):
        return str(self.fn())

    def __repr__(self):
        return repr(self.fn())


def uniq_g(lst, key=lambda v: v):
    """ Get unique elements of an iterable preserving its order and optionally
    determining uniqueness by hash of a key """
    known = set()
    for v in lst:
        k = key(v)
        if k not in known:
            yield v
            known.add(k)
    ## ...


def uniq(lst, key=lambda v: v):
    """ RTFS """
    return list(uniq_g(lst, key=key))


list_uniq = uniq_g


### Helper for o_repr that displays '???'
class ReprObj(object):
    """ A class for inserting specific text in __repr__ outputs.  """

    def __init__(self, txt):
        self.txt = txt

    def __repr__(self):
        return self.txt


#_err_obj = type('ErrObj', (object,), dict(__repr__=lambda self: '???'))()
_err_obj = ReprObj('???')


## It is similar to using self.__dict__ in repr() but works over dir()
def o_repr_g(o, _colors=False, _colors256=False, _colorvs=None):
    """ Represent (most of) data on a python object in readable
    way. Useful default for a __repr__.
    WARN: does not handle recursive structures; use carefully.  """

    ## TODO: handle recursive structures (similar to dict.__repr__)
    ## TODO: process base types (dict / list / ...) in a special way

    def _color(x16, x256=None):
        if not _colors:
            return ''
        if _colors256 and x256:
            return '\x1b[38;5;' + str(x256) + 'm'
        return '\x1b[0' + str(x16) + 'm'

    _colorvs = _colorvs or dict(
        base=('1;37', '230'),  ## Base (punctuation)  # white / pink-white
        clsn=('1;36', '123'),  ## Class name  # cyan / purple-white
        attr=('0;32', '120'),  ## Attribute name  # dark-green / green-white
        val=('0;37', '252'),  ## Value data  # light-gray / light-light-gray
    )

    def _colorv(n):
        return _color(*_colorvs[n])

    yield _colorv("base")
    yield '<'
    yield _colorv("clsn")
    yield str(o.__class__.__name__)
    yield _colorv("base")
    yield '('

    #o_type = type(o)  # V3: check type for properties
    first = True

    for n in sorted(dir(o)):
        if n.startswith('_'):  # skip 'private' stuff
            continue
        if first:
            first = False
        else:
            yield _colorv("base")
            yield ', '
        yield _colorv("attr")
        yield str(n)  ## NOTE: some cases (e.g. functions) will remain just names

        ## V2: try but fail
        try:
            v = getattr(o, n)
            if callable(v):  # skip functions (... and other callables)
                continue
        except Exception as e:
            v = _err_obj

        ## V3: check type for properties
        #v_m = getattr(o_type, n, None)
        #if v_m is not None and isinstance(v_m, property):
        #    continue  # skip properties
        #v = getattr(o, n)
        #if callable(v):  # skip functions (... and other callables)
        #    continue
        yield _colorv("base")
        yield '='
        yield _colorv("val")
        yield repr(v)

    yield _colorv("base")
    yield ')>'
    yield '\x1b[00m'  # color clear


def o_repr(o, **kwa):
    return ''.join(o_repr_g(o, **kwa))


def p_o_repr(o, **kwa):
    kwa = dict(dict(_colors=True, _colors256=True), **kwa)
    print o_repr(o, **kwa)


class OReprMixin(object):
    def __repr__(self):
        return o_repr(self)


def stdin_lines(strip_newlines=True):
    """ Iterate over stdin lines in a 'line-buffered' way """
    while True:
        try:
            l = sys.stdin.readline()
        except KeyboardInterrupt:
            return
        if not l:
            break
        ## This might not be the case if the stream terminates with a non-newline at the end.
        if strip_newlines and l[-1] == '\n':
            l = l[:-1]
        yield l


def stdout_lines(gen):
    """ Send lines from a generator / iterable to stdout in a line-buffered way. """
    for l in gen:
        sys.stdout.write("%s\n" % (l,))
        sys.stdout.flush()


def dict_merge(target, source, instancecheck=None, dictclass=dict, del_obj=object()):
    """ do update() on 'dict of dicts of di...' structure recursively.
    Also, see sources for details.
    NOTE: does not keep target's specific tree structure (forces source's)
    :param del_obj: allows for deletion of keys if the key in the `source` is set to this.

    >>> data = {}
    >>> data = dict_merge(data, {'open_folders': {'my_folder_a': False}})
    >>> data
    {'open_folders': {'my_folder_a': False}}
    >>> data = dict_merge(data, {'open_folders': {'my_folder_b': True}})
    >>> data
    {'open_folders': {'my_folder_b': True, 'my_folder_a': False}}
    >>> _del = object()
    >>> data = dict_merge(data, {'open_folders': {'my_folder_b': _del}}, del_obj=_del)
    >>> data
    {'open_folders': {'my_folder_a': False}}
    """
    if instancecheck is None:  # funhorrible ducktypings
        #instancecheck = lambda iv: isinstance(iv, dict)
        instancecheck = lambda iv: hasattr(iv, 'iteritems')
    ## Recursive parameters shorthand
    kwa = dict(instancecheck=instancecheck, dictclass=dictclass, del_obj=del_obj)

    for k, v in source.iteritems():
        if v is del_obj:
            target.pop(k, None)
        elif instancecheck(v):  # (v -> source -> iteritems())
            ## NOTE: if target[k] wasn't a dict - it will be, now.
            target[k] = dict_merge(
                dict_fget(target, k, dictclass), v, **kwa)
        else:  # nowhere to recurse into - just replace
            ## NOTE: if target[k] was a dict - it won't be, anymore.
            target[k] = v

    return target


def _sqrt(var):
    """ Duck-compatible sqrt(), needed to support classes like Decimal.

    Approximately the same as in the python3's `statistics`. """
    try:
        return var.sqrt()
    except AttributeError:
        return math.sqrt(var)


class IterStat(object):
    """ Iterative single-pass computing of mean and variance.

    Error is on the rate of 1e-08 for 1e6 values in the range of
    0..1e6, both for mean and for stddev. """
    ## http://www.johndcook.com/standard_deviation.html

    def __init__(self, vals=None, start=0):
        self.start = start
        self.old_mean = None
        self.mean = self.stdx = start
        self.cnt = 0

        if vals:
            for val in vals:
                self.send(val)

    def send(self, val):
        self.cnt += 1
        if self.cnt == 1:
            self.mean = val
        else:
            self.mean = self.mean + (val - self.mean) / float(self.cnt)
            self.stdx = self.stdx + (val - self.old_mean) * (val - self.mean)
        self.old_mean = self.mean

    @property
    def variance(self):
        if self.cnt <= 1:
            return self.start
        return self.stdx / (self.cnt)

    @property
    def std(self):
        return _sqrt(self.variance)


def chunks(lst, size):
    """ Yield successive chunks from lst. No padding.  """
    for i in xrange(0, len(lst), size):
        yield lst[i:i + size]


def chunks_g(iterable, size):
    """ Same as 'chunks' but works on any iterable.

    Converts the chunks to tuples for simplicity.
    """
    # http://stackoverflow.com/a/8991553
    it = iter(iterable)
    if size <= 0:
        yield it
        return
    while True:
        chunk = tuple(islice(it, size))
        if not chunk:
            return
        yield chunk
