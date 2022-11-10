"""
The most simple and backwards-compatible way of getting something. Not
necessarily performant.

Does not contain unsafe-to-import modules.
"""

# Ordering is from least important to most important, with modules
# themselves last.

from . import base, dicts, madness, ranges, runlib, urlhelpers
from .base import *
from .dicts import *
from .madness import *
from .ranges import *
from .runlib import *
from .urlhelpers import *
