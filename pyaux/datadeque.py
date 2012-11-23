""" Entry-module for the pyx-compiled `_datadeque` module """

try:
    from . import _datadeque
except ImportError as e1:
    #try:
    import pyximport
    ## XX: problematic: this will: 1. install pyximport for everything
    ##   (can be unintended), 2. try to compile the module on import,
    ##   which can take a while and fail with an error too. For that
    ##   reason, it is not done in the main module.
    pyximport.install()
    from . import _datadeque
    #except ImportError as e2:
    #    warnings.warn("Error importing pyx (Cython) modules: %r" % (e1,))
from ._datadeque import *
