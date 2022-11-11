"""
Automatically start the debugger on an exception.

Replaces sys.excepthook on `init()`.
Can be included in 'sitecustomize.py'

src: http://code.activestate.com/recipes/65287-automatically-start-the-debugger-on-an-exception/
"""
from __future__ import annotations

import sys


def info(type, value, tb):
    if hasattr(sys, "ps1") or not sys.stderr.isatty():
        # we are in interactive mode or we don't have a tty-like
        # device, so we call the default hook
        sys.__excepthook__(type, value, tb)
    else:
        import traceback

        import ipdb

        # we are NOT in interactive mode, print the exception...
        traceback.print_exception(type, value, tb)
        # ...then start the debugger in post-mortem mode.
        ipdb.pm()


def init():
    sys.excepthook = info
