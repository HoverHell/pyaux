# coding: utf8
# pylint: disable=useless-import-alias
"""
Monkey-patching of various things
"""

from __future__ import division, absolute_import, print_function, unicode_literals


__all__ = (
    'use_cdecimal',
    'use_exc_ipdb',
    'use_exc_log',
    'use_colorer',
)


def use_cdecimal():
    """ Do a hack-in replacement of `decimal` with `cdecimal`.
    Should be done before importing other modules.

    Also see
    http://adamj.eu/tech/2015/06/06/swapping-decimal-for-cdecimal-on-python-2/
    for a possibly more reliable way.
    """
    import sys
    import decimal  # maybe not needed
    import cdecimal  # pylint: disable=import-error
    sys.modules['decimal'] = cdecimal


def use_exc_ipdb():
    """ Set unhandled exception handler to automatically start ipdb """
    import pyaux.exc_ipdb as exc_ipdb
    exc_ipdb.init()


def use_exc_log():
    """ Set unhandled exception handler to verbosely log the exception """
    import pyaux.exc_log as exc_log
    exc_log.init()


def use_colorer():
    """ Wrap logging's StreamHandler.emit to add colors to the logged
      messages based on log level """
    # TODO: make a ColorerHandlerMixin version
    import pyaux.Colorer as Colorer
    Colorer.init()
