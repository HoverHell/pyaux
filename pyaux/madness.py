# coding: utf8
""" Things that are not quite okay to use in most cases.

Also, things that are useful in an ipython interactice shell.
"""

from .madness_datadiff import *
from .madness_oneliny import *
from .madness_reprstuff import *
from .madness_stuffstuff import *


# __all__ includes everything from submodules too
__all__ = (
    # repr stuff
    'GenReprWrap', 'GenReprWrapWrap',
    # the oneliners and debug-useful stuff
    '_try', '_try2', '_iter_ar', '_filter',
    '_filter_n', '_print', '_ipdbg', '_uprint',
    '_yprint', 'p_o_repr',
    # diff stuff
    '_dumprepr',
    '_diff_pre_diff', '_diff_datadiff_data', 'datadiff', 'p_datadiff',
    # stuff stuff
    'Url',
    '_url_re',
    '_cut', 'IPNBDFDisplay',
    # __builtin__ hacks
    '_olt_into_builtin',
    '_into_builtin',
)


# # Builtin-madness # #


def _into_builtin(d):
    """ Helper to put stuff (like the one-liner-helpers) into builtins """
    import __builtin__
    for k, v in d.items():
        setattr(__builtin__, k, v)


# For _into_builtin
__all_stuff = locals()
__all_stuff_e = dict((k, globals().get(k)) for k in __all__)


try:
    # better pprint
    from IPython.lib.pretty import pprint, pretty
    __all_stuff.update(pprint=pprint, pretty=pretty, pformat=pretty)
    __all_stuff_e.update(pprint=pprint, pretty=pretty, pformat=pretty)
except ImportError as __e:
    print "What, no IPython?", __e


# For explicit call:
def _olt_into_builtin():
    return _into_builtin(__all_stuff_e)


# For use as execfile()
if locals().get('__into_builtin'):
    _olt_into_builtin()


# Recommendation: put
#     from pyaux import madness
#     madness._olt_into_builtin()
# in the
#     ~/.config/ipython/profile_default/ipython_config.py
