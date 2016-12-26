# coding: utf8
""" A collection of useful helpers """

__version__ = "1.13.0"

## NOTE: no modules imported here should import `decimal` (otherwise
##   `use_cdecimal` might become problematic for them)

from .base import *

# import warnings


## Put the other primary modules in the main module namespace
## ... but do not fail
## Conclusion: this is generally a bad idea.
# from . import runlib
# try:
#     from . import lzmah, lzcat
# except ImportError as e:
#     warnings.warn("Unable to import lzma helpers: %r" % (e,))
# try:
#     from . import psql
# except ImportError as e:
#     warnings.warn("Unable to import psql helpers: %r" % (e,))
# try:
#     from . import twisted_aux
# except ImportError as e:
#     warnings.warn("Unable to import twisted helpers: %r" % (e,))
