# coding: utf8
""" A collection of useful helpers """

__all__ = [
 'bubble',
 'window',
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
 'runlib',
 'lzmah',
 'lzcat',
 'psql',
]


import sys

import inspect
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
from itertools import chain, repeat, islice
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


class SmartDict(dict):
    """ A simple dict subclass with items also available over attributes """
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as e:
            raise AttributeError(e)
    def __setattr__(self, name, value):
        self[name] = value


dbgs = {}   # global object for easier later access of dumped `__call__`s
def repr_call(ar, kwa):
    """ A helper function for pretty-printing a function call arguments """
    r = ', '.join("%r" % (v,) for v in ar)
    if kwa:
        r += ', ' + ', '.join('%s=%r' % (k, v) for k, v in kwa.iteritems())
    return r
def DebugPlug(name, mklogger=None):
    """ Create and return a recursive duck-object for plugging in place of
    other objects for debug purposes.
    `name`: name for tracking the object and its (child) attributes.
    `mklogger`: a function of `name` (str) that returns a new callable(msg:
      str) used for logging.  See code for an example.  """
    ## The construction with mkClass is for removing the need of
    ##   `__getattr__`ing the name and logger.
    import logging
    def mklogger_default(name):
        logger = logging.getLogger(name)
        return logger.debug
    if mklogger == None:
        mklogger = mklogger_default
    log = mklogger(name)
    class DebugPlugInternal(object):
        """ An actual internal class of the DebugPlug """
        def __call__(self, *ar, **kwa):
            log("called with (%s)" % repr_call(ar, kwa))
            global dbgs
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


def fxrange(start, end=None, inc=None):
    """ The xrange function for float """
    assert inc != 0, "inc should not be zero"
    if end == None:
        end = start
        start = 0.0
    if inc == None:
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
    return list(fxrange(start, end, inc))


def dxrange(start, end=None, inc=None, include_end=False):
    """ The xrange function for Decimal """
    # Imported here mostly because of use_cdecimal in this module
    from decimal import Decimal
    assert inc != 0, "inc should not be zero"
    if end == None:
        end = start
        start = 0
    if inc == None:
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
    return list(dxrange(*ar, **kwa))


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


## String interpolation
## http://rightfootin.blogspot.com/2007/02/string-interpolation-in-python.html
import re
def interp(string):
    """ Inline string interpolation.
    >>> var1 = 213; ff = lambda v: v**2
    >>> interp("var1 is #{var1}")
    'var1 is 213'
    >>> interp("var1 is #{ff(var1)}; also #{ff(12)}")
    'var1 is 45369; also 144'
    """
    flocals = sys._getframe(1).f_locals
    fglobals = sys._getframe(1).f_globals
    for item in re.findall(r'#\{([^}]*)\}', string):
        string = string.replace('#{%s}' % item,
          str(eval(item, fglobals, flocals)))
    return string


## Yet another string-interpolation helper
class InterpolationEvaluationException(KeyError):
    pass
class edi(dict):  # "expression_dictionary"...
    """ Yet another string interpolation helper.

    >>> var1 = 313; f = lambda x: x*2
    >>> print "1 is %(var1)5d, f1 is %(f(var1))d, f is %(f)r, 1/2 is %(float(var1)/2)5.3f." % edi()
    1 is   313, f1 is 626, f is <function <lambda> at 0x9ab917c>, 1/2 is 156.500.

    """
    ## No idea for what sake this is subclassed from dictionary, actually. A
    ## neat extra, perhaps.

    globals = {}

    def __init__(self, d=None):
        if d == None:  # Grab parent's locals forcible
            self.locals  = sys._getframe(1).f_locals
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
  dict_class=SmartDict):
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


import traceback
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
        getattr(self, logger_name).debug("%s set to %r from %s:%d, in %s",
          actual_name, val, tb[0], tb[1], tb[2])
    return property(do_get, do_set)


def sign(v):
    """ Sign of value: `return cmp(v, 0)` """
    return cmp(v, 0)


### "Human" sorting, advanced
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


import time
import functools
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
        if not hasattr(self, '_call_val') or self._call_val != val:
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
    return (lambda fn: functools.wraps(fn)(ThrottledCall(fn, *ar, **kwa)))


## Put the other primary modules in the main module namespace
from . import runlib, lzmah, lzcat, psql
