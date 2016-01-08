# coding: utf8
"""
Sting interpolation functions.

For convenience, not performance.

Generally not particularly recommended.
"""

from __future__ import print_function, absolute_import, division

import sys
import re


__all__ = (
    'interp',
    'edi',
    'InterpolationEvaluationException',
)


# http://rightfootin.blogspot.com/2007/02/string-interpolation-in-python.html
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
    # Do eval and replacement separately and replacement in one regex
    # go to avoid interpolating already interpolated values.
    for item_outer, item in items:
        item_to_str[item] = str(eval(item, fglobals, flocals))
    string = re.sub(_regexp, lambda match: item_to_str[match.group(2)], string)
    return string


class InterpolationEvaluationException(KeyError):
    pass


class edi(dict):  # "expression_dictionary"...
    """ Yet another string interpolation helper.

    >>> var1 = 313; f = lambda x: x*2
    >>> print("1 is %(var1)05d, f1 is %(f(var1))d, f is %(f)r, 1/2 is %(float(var1)/2)5.3f." % edi())  #doctest: +ELLIPSIS
    1 is 00313, f1 is 626, f is <function <lambda> at 0x...>, 1/2 is 156.500.

    """
    # No idea for what sake this is subclassed from dictionary, actually. A
    # neat extra, perhaps.

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
            except Exception as exc:
                raise InterpolationEvaluationException(key, exc)
