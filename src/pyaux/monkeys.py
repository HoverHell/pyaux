"""Monkey-patching of various things"""

from __future__ import annotations

__all__ = (
    "use_colorer",
    "use_exc_ipdb",
    "use_exc_log",
)


def use_exc_ipdb() -> None:
    """Set unhandled exception handler to automatically start ipdb"""
    from pyaux import exc_ipdb  # noqa: PLC0415

    exc_ipdb.init()


def use_exc_log() -> None:
    """Set unhandled exception handler to verbosely log the exception"""
    from pyaux import exc_log  # noqa: PLC0415

    exc_log.init()


def use_colorer() -> None:
    """
    Wrap logging's StreamHandler.emit to add colors to the logged
    messages based on log level
    """
    # TODO: make a ColorerHandlerMixin version
    from pyaux import Colorer  # noqa: PLC0415

    Colorer.init()
