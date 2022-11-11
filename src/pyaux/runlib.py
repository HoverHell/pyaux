""" Various (un)necessary stuff for runscripts """

from __future__ import annotations

import atexit
import logging
import signal
import sys
import traceback

__all__ = [
    "init_logging",
    "sigeventer",
]


def _make_short_levelnames(shortnum=True):
    """Return a dict (levelnum -> levelname) with short names for logging.
    `shortnum`: also shorten all 'Level #' names to 'L##'.
    """
    _names = dict(
        [
            (logging.DEBUG, "DBG"),
            (logging.INFO, "INFO"),  # d'uh
            (logging.WARN, "WARN"),
            (logging.ERROR, "ERR"),
            (logging.CRITICAL, "CRIT"),
        ]
    )
    if shortnum:
        for i in range(1, 100):
            _names.setdefault(i, "L%02d" % (i,))
    return _names


# Current attempt: use bytes in py2, unicode in py3 (i.e. subvert unicode_literals just for these).
BASIC_LOG_FORMAT = "%(asctime)s: %(levelname)-13s: %(name)s: %(message)s"
BASIC_LOG_FORMAT_TD = str(
    "%(asctime)s(+%(time_diff)5.3fs): %(levelname)-13s: %(name)s: %(message)s"
)


def init_logging(*args, **kwargs):
    """Simple shorthand for neat and customizable logging init"""
    _td = kwargs.pop("_td", False)
    # Support for https://pypi.python.org/pypi/coloredlogs
    # Also, notable: https://pypi.python.org/pypi/verboselogs
    # (but no special support here at the moment)
    _try_coloredlogs = kwargs.pop("_try_coloredlogs", False)

    if _try_coloredlogs:
        try:
            import coloredlogs
        except Exception:
            coloredlogs = None
            _try_coloredlogs = False

    colored = kwargs.pop("colored", True)
    if colored and not _try_coloredlogs:
        from . import use_colorer

        use_colorer()

    short_levelnames = kwargs.pop("short_levelnames", True)
    if short_levelnames:
        _names = _make_short_levelnames()
        for lvl, name in _names.items():
            logging.addLevelName(lvl, str(name))

    kwargs.setdefault("level", logging.DEBUG)

    logformat = BASIC_LOG_FORMAT
    if _td:
        logformat = BASIC_LOG_FORMAT_TD
    kwargs.setdefault("format", logformat)

    if _try_coloredlogs:
        kwargs["fmt"] = kwargs["format"]
        coloredlogs.install(*args, **kwargs)
    else:
        logging.basicConfig(*args, **kwargs)

    if _td:
        # XX: do the same for all `logging.Logger.manager.loggerDict.values()`?
        from .logging_annotators import time_diff_annotator

        flt = time_diff_annotator()
        logging.root.addFilter(flt)
        for logger in logging.Logger.manager.loggerDict.values():
            if hasattr(logger, "addFilter"):
                logger.addFilter(flt)


def argless_wrap(fn):
    """Wrap function to re-try calling it if calling it with arguments
    failed"""

    def argless_internal(*ar, **kwa):
        try:
            return fn(*ar, **kwa)
        except TypeError:
            try:
                return fn()
            except TypeError:
                # raise e  # - traceback-inconvenient
                raise  # - error-inconvenient

    return argless_internal


# convenience wrappers:
def _sysexit_wrap(n=None, f=None):
    return sys.exit()


def _atexit_wrap(n=None, f=None):
    return atexit._run_exitfuncs()


class ListSigHandler(list):
    def __init__(self, try_argless, ignore_exc, verbose):
        self.try_argless = try_argless
        self.ignore_exc = ignore_exc
        self.verbose = verbose

    def __call__(self, n, f):
        for func in reversed(self):
            try:
                if self.verbose:
                    sys.stderr.write(f"ListSigHandler: running {func!r}\n")
                if self.try_argless:
                    func = argless_wrap(func)
                func(n, f)
            except Exception as exc:
                if self.ignore_exc:
                    if self.verbose:
                        traceback.print_exc()
                    else:
                        # Still print something
                        sys.stderr.write(f"Exception ignored: {exc!r}\n")
                else:
                    raise


def sigeventer(
    add_defaults=True,
    add_previous=True,
    do_sysexit=True,
    try_argless=True,
    ignore_exc=True,
    verbose=False,
):
    """
    Puts one list-based handler for SIGINT and SIGTERM that can be `append`ed to.

    NOTE: arguments are ignored if it was called previously.

    :param add_defaults: add the `atexit` handler.
    :param add_previous: add the previously-set handlers (NOTE: will
        mix sigterm/sigint handlers if different).
    :param try_argless: re-call handled function without parameters if
        they raise TypeError.
    :param do_sysexit: do `sys.exit()` at the end of handler.
    :param ignore_exc: ...

    Use `signal.getsignal(signal.SIGINT).append(some_func)` to add a handler.
    Handlers are called in reverse order (first in, last out).
    """
    # XXXX/TODO: a version that only sets itself on one of the signals
    # (optionally).
    # Check if already done something like this:
    curhandler_int = signal.getsignal(signal.SIGINT)
    curhandler_term = signal.getsignal(signal.SIGTERM)

    if isinstance(curhandler_int, list) and isinstance(curhandler_term, list):
        # probaby us already; just return
        assert (
            curhandler_int is curhandler_term
        ), "unexpected: different list-based term/int handlers"
        return curhandler_term

    the_handler = ListSigHandler(try_argless=try_argless, ignore_exc=ignore_exc, verbose=verbose)
    signal.signal(signal.SIGINT, the_handler)
    signal.signal(signal.SIGTERM, the_handler)

    # Useful since this all will only be done once.
    if do_sysexit:
        the_handler.append(_sysexit_wrap)
    if add_previous:
        # Note that signal.SIG_DFL will be basically ignored.
        if callable(curhandler_term):
            the_handler.append(curhandler_term)
        if callable(curhandler_int) and curhandler_int != curhandler_term:
            # (Note that same previous handler still can be called twice)
            the_handler.append(curhandler_int)
    if add_defaults:
        the_handler.append(_atexit_wrap)
    return the_handler
