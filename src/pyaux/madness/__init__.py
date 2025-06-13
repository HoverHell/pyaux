"""
Things that are not quite okay to use in most cases.

Also, things that are useful in an ipython interactice shell.
"""

from __future__ import annotations

import builtins
import sys
from typing import Any

from .. import aio
from ..aio import _await
from . import (
    datadiff as madness_datadiff,
    oneliny as madness_oneliny,
    reprstuff as madness_reprstuff,
    stuffstuff as madness_stuffstuff,
)
from .datadiff import (
    _diff_datadiff_data,
    _diff_pre_diff,
    _dumprepr,
    datadiff,
    p_datadiff,
)
from .oneliny import (
    _filter,
    _filter_n,
    _ipdbg,
    _ipdbt,
    _iter_ar,
    _mrosources,
    _print,
    _try,
    _try2,
    _uprint,
    _yprint,
    p_o_repr,
)
from .reprstuff import GenReprWrapper, genreprwrap
from .stuffstuff import Url, _cut, _re_largest_matching_start, _url_re, displaydf

# *aio.__all__,
# *madness_datadiff.__all__,
# *madness_oneliny.__all__,
# *madness_reprstuff.__all__,
# *madness_stuffstuff.__all__,
# __builtin__ hacks
__all__ = (
    "GenReprWrapper",
    "Url",
    "_await",
    "_cut",
    "_diff_datadiff_data",
    "_diff_pre_diff",
    "_dumprepr",
    "_filter",
    "_filter_n",
    "_into_builtin",
    "_ipdbg",
    "_ipdbt",
    "_iter_ar",
    "_mrosources",
    "_olt_into_builtin",
    "_print",
    "_re_largest_matching_start",
    "_try",
    "_try2",
    "_uprint",
    "_url_re",
    "_yprint",
    "aio",
    "datadiff",
    "displaydf",
    "genreprwrap",
    "madness_datadiff",
    "madness_oneliny",
    "madness_reprstuff",
    "madness_stuffstuff",
    "p_datadiff",
    "p_o_repr",
)


# # Builtin-madness # #


def _into_builtin(dct: dict[str, Any]) -> None:
    """Helper to put stuff (like the one-liner-helpers) into builtins"""
    for key, val in dct.items():
        setattr(builtins, key, val)


# For _into_builtin
__all_stuff = locals()
__all_stuff_e = {key: globals().get(key) for key in __all__}


try:
    # better pprint
    from IPython.lib.pretty import pprint, pretty

    __all_stuff.update(pprint=pprint, pretty=pretty, pformat=pretty)
    __all_stuff_e.update(pprint=pprint, pretty=pretty, pformat=pretty)
except ImportError as __e:
    sys.stderr.write(f"What, no IPython? {__e!r}\n")


# For explicit call:
def _olt_into_builtin() -> None:
    _into_builtin(__all_stuff_e)


# For use as execfile()
if locals().get("__into_builtin"):
    _olt_into_builtin()


# Recommendation: put
#     from pyaux import madness
#     madness._olt_into_builtin()
# in the
#     ~/.config/ipython/profile_default/ipython_config.py
