# coding: utf8
"""
The most simple and backwards-compatible way of getting something. Not
necessarily performant.

Does not contain unsafe-to-import modules.
"""

# Ordering is from least important to most important, with modules
# themselves last.

from .madness import *
from .runlib import *
from .interpolate import *
from .dicts import *
from .urlhelpers import *
from .ranges import *
from .base import *
from . import madness
from . import runlib
from . import interpolate
from . import dicts
from . import urlhelpers
from . import ranges
from . import base
