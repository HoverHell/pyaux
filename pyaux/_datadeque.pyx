# coding: utf8
"""
WARNING: this module will be moved to `pyauxm`.
"""

from collections import deque
import pandas


__all__ = [
  'datadeque',
]


class datadeque(deque):
    ''' Pandas Dataframe-convertible deque of dicts with fixed fields.
    '''
    ## TODO: use cases and usage examples

    def todataframe(self):
        ''' Convert dataqueue into pandas.DataFrame '''
        cdef dict d
        cdef dict df = {}
        if len(self) == 0:
            return
        cdef set fields = set(self[0].keys())
        cdef object f
        for f in fields:
            df[f] = list()
        for d in self:
            for f in fields:
                df[f].append(d[f])
        return pandas.DataFrame(df)
