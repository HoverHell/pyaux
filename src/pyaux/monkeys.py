# pylint: disable=useless-import-alias
"""
Monkey-patching of various things
"""

from __future__ import annotations

__all__ = (
    "use_exc_ipdb",
    "use_exc_log",
    "use_colorer",
)


def use_exc_ipdb():
    """Set unhandled exception handler to automatically start ipdb"""
    import pyaux.exc_ipdb as exc_ipdb

    exc_ipdb.init()


def use_exc_log():
    """Set unhandled exception handler to verbosely log the exception"""
    import pyaux.exc_log as exc_log

    exc_log.init()


def use_colorer():
    """Wrap logging's StreamHandler.emit to add colors to the logged
    messages based on log level"""
    # TODO: make a ColorerHandlerMixin version
    import pyaux.Colorer as Colorer

    Colorer.init()
