"""
Entry-module for the pyx-compiled `_datadeque` module.

WARNING: this module will be moved to `pyauxm`.
"""
from __future__ import annotations

try:
    from . import _datadeque
except ImportError:
    import pyximport

    # WARNING: this will:
    # 1. install pyximport for everything globally.
    # 2. try to compile the module on import,
    #    which can take a while and fail with an error too.
    pyximport.install()
    from . import _datadeque

from ._datadeque import *

__all__ = (*_datadeque.__all__,)
