"""
The most simple and backwards-compatible way of getting something. Not
necessarily performant.

Does not contain unsafe-to-import modules.
"""

from __future__ import annotations

from .. import base, dicts, madness, ranges, runlib, urlhelpers
from ..base import *  # noqa: F403
from ..dicts import *  # noqa: F403
from ..madness import *  # noqa: F403
from ..ranges import *  # noqa: F403
from ..runlib import *  # noqa: F403
from ..urlhelpers import *  # noqa: F403

__all__ = (  # noqa: PLE0604
    *base.__all__,
    *dicts.__all__,
    *madness.__all__,
    *ranges.__all__,
    *runlib.__all__,
    *urlhelpers.__all__,
)
