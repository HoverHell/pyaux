# coding: utf8
""" Things that are not quite okay to use in most cases.

Also, things that are useful in an ipython interactice shell.
"""

__all__ = [
    ## reprstuff
    'GenReprWrap', 'GenReprWrapWrap',
    ## the most useful stuff
    '_try', '_try2', '_iter_ar', '_filter',
    '_filter_n', '_print', '_ipdbg', '_uprint',
    ## diffstuff
    '_dumprepr',
    '_diff_pre_diff', '_diff_datadiff_data', 'datadiff', 'p_datadiff',
    ## stuffstuff
    'Url',
    '_url_re',
    '_cut', 'IPNBDFDisplay',
    ## __builtin__ hacks
    '_olt_into_builtin',
    '_into_builtin',
]


import re
import sys


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
        res.append('(')
        if cache:
            res.append(', '.join(repr(v) for v in cache))
        if self._probably_more:
            res.append(', ...')
        res.append(')')
        return ''.join(res)

    def next(self):
        try:  # Exhaust cache first.
            return self.cache_list.pop(0)
        except IndexError as e:
            return next(self.gen)

    def __iter__(self):
        return self


def GenReprWrapWrap(fn=None, **wrap_kwa):
    import functools

    def _wrap(w_fn):
        @functools.wraps(w_fn)
        def _wrapped(*ar, **kwa):
            res = fn(*ar, **kwa)
            if hasattr(res, '__iter__') and hasattr(res, 'next'):
                return GenReprWrap(res, **wrap_kwa)
            return res

        return _wrapped

    if fn is not None:
        return _wrap(fn)

    return _wrap


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


@GenReprWrapWrap
def _filter(*ar):
    """ Mostly the same as `filter(None, …)` but as a generator with conveniences. """
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


###
## Data diff tools
###


import yaml
import difflib
import itertools


def _dumprepr(val, no_anchors=True, **kwa):
    """ Advanced-ish representation of an object (using YAML) """
    dumper = yaml.SafeDumper

    ## NOTE: this means it'll except on infinitely-recursive data.
    if no_anchors:
        dumper = type(
            'NoAliasesSafeDumper', (dumper,),
            dict(ignore_aliases=lambda self, data: True))

    params = dict(default_flow_style=False, Dumper=dumper)
    params.update(kwa.get('yaml_kwa', {}))

    res = ''
    try:
        res += yaml.dump(val, **params)
    except Exception as e:
        ## ujson can handle many objects somewhat-successfully.
        import ujson
        res += "# Unable to serialize directly!\n"
        res += yaml.dump(ujson.loads(ujson.dumps(val)), **params)

    return res


def _diff_pre_diff(val, **kwa):
    """ Prepare a value for diff-ing """
    _repr = kwa.get('_repr', _dumprepr)
    res = _repr(val, **kwa)
    res = res.splitlines()
    return res


def _diff_datadiff_data(val1, val2, **kwa):
    """ Do the diff and return the data """
    res = difflib.unified_diff(_diff_pre_diff(val1), _diff_pre_diff(val2))
    return res


def datadiff(val1, val2, **kwa):
    """ Return a values diff string """
    data = _diff_datadiff_data(val1, val2, **kwa)

    ## line_limit
    _ll = kwa.pop('line_limit', 200)
    if _ll:
        data_base = data
        data = list(itertools.islice(data_base, _ll))
        try:
            next(data_base)
        except StopIteration:
            pass
        else:
            data.append(u'...')  # u'…'

    return '\n'.join(data)


def p_datadiff(val1, val2, **kwa):
    """ Print the values diff """
    print datadiff(val1, val2, **kwa)


###
## Other conveniences
###


import urlparse
from pyaux import SmartDict as dotdict
class Url(dotdict):
    """ urlparse.ParseResult and parse_qs[l] in a dict-like non-lazy form """
    _components = (
        'scheme', 'netloc', 'path', 'params', 'query', 'fragment',
        ## from ResultMixin
        'username', 'password', 'hostname', 'port',
    )  ## <scheme>://<netloc>/<path>;<params>?<query>#<fragment>
    ## TODO: urlunescaped parts
    def __init__(self, url, **kwa):
        self.url = url
        data1 = urlparse.urlparse(url, **kwa)
        for k in self._components:
            val = getattr(data1, k)
            setattr(self, k, val)

        self.query_str = self.query
        self.queryl = urlparse.parse_qs(self.query)
        self.query = dict(urlparse.parse_qsl(self.query))

_url_re = (
    ur'''(?i)\b((?:[a-z][\w-]+:(?:/{1,3}|[a-z0-9%])|www\d{0,3}[.]|[a-z0-9.\-]+'''
    ur'''[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+'''
    ur'''(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'".,<>?«»“”‘’]))''')
def _cut(s, l):
    if len(s) <= l:
        return s
    return s[:l] + u'…'


def IPNBDFDisplay(df, *ar, **kwa):
    """ A helper to display a pandas DataFrame in the IPython notebook.

    Recommended things to do:
    pandas.options.display.max_colwidth = 2000
    H = IPNBDFDisplay
    """
    from IPython.display import display, HTML
    kwa.setdefault('max_rows', 300)
    kwa.setdefault('float_format', lambda v: '%.6f' % (v,))
    tail = kwa.pop('tail', None)
    head = kwa.pop('head', 200)
    cutlinks = kwa.pop('cutlinks', True)
    do_display = kwa.pop('display', True)

    if head:
        df = df.head(head)
    if tail:
        df = df.tail(tail)

    html = df.to_html(*ar, **kwa)

    if cutlinks:
        cutlinks = 80 if cutlinks is True else cutlinks

        def cutlink(link):
            return '<a href="%s">%s</a>' % (link, _cut(link, cutlinks))
        html = re.sub(
            _url_re,
            lambda match: cutlink(match.group(0)),
            html)

    ## TODO?: option to insert copious '<wb/>'s in all cells

    if do_display:
        display(HTML(html))
    else:
        return HTML(html)


# pd.options.display.max_colwidth = 9000


###
## Builtin-forcer
###

## For _into_builtin
__all_stuff = locals()
__all_stuff_e = dict(_try2=_try2, _try=_try, _iter_ar=_iter_ar,
  _filter=_filter, _filter_n=_filter_n, _print=_print, _ipdbg=_ipdbg,
  _uprint=_uprint)
__all_stuff_e.update((k, globals().get(k)) for k in __all__)


try:
    from IPython.lib.pretty import pprint, pretty
    # sys.stderr.write("IPytoo\n")
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
