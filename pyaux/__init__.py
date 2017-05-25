# coding: utf8
"""
A collection of useful helpers.
 """

__version__ = "1.15.0"

# Note: no modules imported here should import `decimal` (otherwise
# `use_cdecimal` might become problematic for them)

from .base import *

from . import ranges
from .ranges import *

from . import interpolate
from .interpolate import *


__all__ = (
    'bubble',
    'window',
    'dotdict',
    'SmartDict',
    'DebugPlug', 'repr_call',
    'dict_fget',
    'dict_fsetdefault',
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
    'to_bytes',
    'to_unicode',
) + ranges.__all__ + interpolate.__all__
