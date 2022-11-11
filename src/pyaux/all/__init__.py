"""
The most simple and backwards-compatible way of getting something. Not
necessarily performant.

Does not contain unsafe-to-import modules.
"""
from __future__ import annotations

from .. import base, dicts, madness, ranges, runlib, urlhelpers
from ..base import *
from ..dicts import *
from ..madness import *
from ..ranges import *
from ..runlib import *
from ..urlhelpers import *

__all__ = (
    *base.__all__,
    *dicts.__all__,
    *madness.__all__,
    *ranges.__all__,
    *runlib.__all__,
    urlhelpers.__all__,
)
