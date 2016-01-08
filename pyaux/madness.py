# coding: utf8
""" Things that are not quite okay to use in most cases.

Also, things that are useful in an ipython interactice shell.
"""

from __future__ import print_function, unicode_literals, absolute_import, division

from six.moves import builtins
from . import madness_datadiff
from .madness_datadiff import *
from . import madness_oneliny
from .madness_oneliny import *
from . import madness_reprstuff
from .madness_reprstuff import *
from . import madness_stuffstuff
from .madness_stuffstuff import *


__all__ = (
    # __builtin__ hacks
    '_olt_into_builtin',
    '_into_builtin',
)
__all__ += madness_datadiff.__all__
__all__ += madness_oneliny.__all__
__all__ += madness_reprstuff.__all__
__all__ += madness_stuffstuff.__all__


# # Builtin-madness # #


def _into_builtin(dct):
    """ Helper to put stuff (like the one-liner-helpers) into builtins """
    for key, val in dct.items():
        setattr(builtins, key, val)


# For _into_builtin
__all_stuff = locals()
__all_stuff_e = dict((key, globals().get(key)) for key in __all__)


try:
    # better pprint
    from IPython.lib.pretty import pprint, pretty
    __all_stuff.update(pprint=pprint, pretty=pretty, pformat=pretty)
    __all_stuff_e.update(pprint=pprint, pretty=pretty, pformat=pretty)
except ImportError as __e:
    print("What, no IPython?", __e)


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
