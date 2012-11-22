from collections import deque
import pandas

class datadeque(deque):
    ''' Pandas Dataframe-convertible deque of dicts with fixed fields.
    '''

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