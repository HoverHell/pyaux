""" Various (un)necessary stuff for runscripts """

from __future__ import print_function, unicode_literals, absolute_import, division

import os
import sys
import random
import time
import warnings
import logging
import signal
import atexit
import traceback
from pyaux.logging_helpers import LoggingStreamHandlerTD
from six.moves import xrange


__all__ = [
    'init_logging',
    'sigeventer',
]


# TODO: lazy-imports
try:
    from pyaux.twisted_aux import (
        make_manhole_telnet,
        make_manhole,
    )
except ImportError:
    pass


def _make_short_levelnames(shortnum=True):
    """ Return a dict (levelnum -> levelname) with short names for logging.
    `shortnum`: also shorten all 'Level #' names to 'L##'.
    """
    _names = dict([
        (logging.DEBUG, 'DBG'),
        (logging.INFO, 'INFO'),  # d'uh
        (logging.WARN, 'WARN'),
        (logging.ERROR, 'ERR'),
        (logging.CRITICAL, 'CRIT'),
    ])
    if shortnum:
        for i in xrange(1, 100):
            _names.setdefault(i, "L%02d" % (i,))
    return _names


BASIC_LOG_FORMAT = '%(asctime)s: %(levelname)-13s: %(name)s: %(message)s'
BASIC_LOG_FORMAT_TD = '%(asctime)s(+%(time_diff)5.3fs): %(levelname)-13s: %(name)s: %(message)s'


def init_logging(*ar, **kwa):
    """ Simple shorthand for neat and customizable logging init """
    _td = kwa.pop('_td', False)

    colored = kwa.pop('colored', True)
    if colored:
        from . import use_colorer
        use_colorer()
    short_levelnames = kwa.pop('short_levelnames', True)
    if short_levelnames:
        _names = _make_short_levelnames()
        for lvl, name in _names.items():
            logging.addLevelName(lvl, str(name))
    kwa.setdefault('level', logging.DEBUG)
    logformat = BASIC_LOG_FORMAT if not _td else BASIC_LOG_FORMAT_TD
    kwa.setdefault('format', logformat)

    if _td:
        # # can't give it a custom handler class
        # logging.basicConfig(*ar, **kwa)
        hdlr = LoggingStreamHandlerTD(kwa.get('stream'))
        fmt = logging.Formatter(kwa.get('format'), kwa.get('datefmt'))
        hdlr.setFormatter(fmt)
        logging.root.addHandler(hdlr)
        logging.root.setLevel(kwa.get('level', logging.INFO))
    else:
        logging.basicConfig(*ar, **kwa)


def argless_wrap(fn):
    """ Wrap function to re-try calling it if calling it with arguments
    failed """

    def argless_internal(*ar, **kwa):
        try:
            return fn(*ar, **kwa)
        except TypeError as e:
            try:
                return fn()
            except TypeError as e2:
                #raise e  # - traceback-inconvenient
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
                    print("ListSigHandler: running %r" % (func,))
                if self.try_argless:
                    func = argless_wrap(func)
                func(n, f)
            except Exception as e:
                if self.ignore_exc:
                    if self.verbose:
                        traceback.print_exc()
                    else:
                        # Still print something
                        print("Exception ignored: %r" % (e,))
                else:
                    raise


def sigeventer(add_defaults=True, add_previous=True, do_sysexit=True,
               try_argless=True, ignore_exc=True, verbose=False):
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
        assert curhandler_int is curhandler_term, \
            "unexpected: different list-based term/int handlers"
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
        if (callable(curhandler_int) and
                curhandler_int != curhandler_term):
            # (Note that same previous handler still can be called twice)
            the_handler.append(curhandler_int)
    if add_defaults:
        the_handler.append(_atexit_wrap)
    return the_handler
