# coding: utf8
""" Things that are not quite okay to use in most cases.

Also, things that are useful in an ipython interactice shell.
"""


class GenReprWrap(object):
    """ Generator proxy-wrapper that prints part of the child generator
    on __repr__ (saving it in a list).  """
    def __init__(self, gen, max_repr=20):
        self.gen = gen
        self.max_repr = max_repr
        self.cache_list = []
        self._probably_more = True
    def _make_cache(self):
        while len(self.cache_list) < self.max_repr:
            ## NOTE: Not checking self._probably_more here, assuming
            ##   that generator will continue to give out StopIteration
            ##   many times.
            try:
                v = next(self.gen)
            except StopIteration as e:
                self._probably_more = False
                return self.cache_list
            self.cache_list.append(v)
        return self.cache_list
    def __repr__(self):
        cache = self._make_cache()
        res = []
        res.append('[')
        if cache:
            res.append(', '.join(repr(v) for v in cache))
        if self._probably_more:
            res.append(', ...')
        res.append(']')
        return ''.join(res)
    def next(self):
        try:  # Exhaust cache first.
            return self.cache_list.pop(0)
        except IndexError as e:
            return next(self.gen)
    def __iter__(self):
        return self


#######  One-liner tools  #######
def _try2(_function_thingie, *ar, **kwa):
    """ Returns (res, None) on success or (None, exception) """
    ## The weird names are to minimize kwa collision
    _exc_clss = kwa.pop('_exc_clss', Exception)
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


def _filter(*ar):
    """ Mostly the same as `filter(None, …)` but as a generator with conveniences. """
    it = _iter_ar(*ar)
    for i in it:
        if i:
            yield i
def _filter_n(*ar):
    """ Filter out None specifically (also a generator with conveniences) """
    it = _iter_ar(*ar)
    for i in it:
        if i is not None:
            yield i


def _into_builtin(d):
    """ Helper to put stuff (like the one-liner-helpers) into builtins """
    import __builtin__
    for k, v in d.items():
        setattr(__builtin__, k, v)


def _print(s):
    """ Simple one-argument `print` one-liner; returns the argument.  """
    print s
    return s


def _ipdbg(_a_function_thingie, *ar, **kwa):
    import ipdb
    import traceback
    import sys
    try:
        return _a_function_thingie(*ar, **kwa)
    except Exception as e:
        _, _, sys.last_traceback = sys.exc_info()
        traceback.print_exc()
        ipdb.pm()
        return None


def _uprint(o):
    from IPython.lib.pretty import pretty
    print pretty(o).decode('unicode-escape')
    return o


## For _into_builtin
__all_stuff = locals()
__all_stuff_e = dict(_try2=_try2, _try=_try, _iter_ar=_iter_ar, _filter=_filter, _filter_n=_filter_n, _print=_print, _ipdbg=_ipdbg, _uprint=_uprint)


try:
    from IPython.lib.pretty import pprint, pretty
    print "IPytoo"
    __all_stuff.update(pprint=pprint, pretty=pretty, pformat=pretty)
    __all_stuff_e.update(pprint=pprint, pretty=pretty, pformat=pretty)
except ImportError as __e:
    print "What, no IPython?", __e

## For use as execfile()
try:
    __into_builtin = __into_builtin
except NameError:
    pass
else:
    _into_builtin(__all_stuff_e)


## For explicit call:
def _olt_into_builtin():
    return _into_builtin(__all_stuff_e)


## Recommendation: put `from pyaux import madness; madness._olt_into_builtin()` in the `~/.config/ipython/profile_default/ipython_config.py`.
