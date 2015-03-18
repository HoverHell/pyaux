# coding: utf8
""" madstuff: repr stuff """

__all__ = (
    'GenReprWrap', 'GenReprWrapWrap',
)


class GenReprWrap(object):
    """ Generator proxy-wrapper that prints part of the child generator
    on __repr__ (saving it in a list).  """

    def __init__(self, gen, max_repr=20):
        self.gen = gen
        self.max_repr = max_repr
        self.cache_list = []
        self._probably_more = True

    def _make_cache(self):
        while len(self.cache_list) < self.max_repr:
            # NOTE: Not checking self._probably_more here, assuming
            #   that generator will continue to give out StopIteration
            #   many times.
            try:
                v = next(self.gen)
            except StopIteration:
                self._probably_more = False
                return self.cache_list
            self.cache_list.append(v)
        return self.cache_list

    def __repr__(self):
        cache = self._make_cache()
        res = []
        res.append('(')
        if cache:
            res.append(', '.join(repr(v) for v in cache))
        if self._probably_more:
            res.append(', ...')
        res.append(')')
        return ''.join(res)

    def next(self):
        try:  # Exhaust cache first.
            return self.cache_list.pop(0)
        except IndexError:
            return next(self.gen)

    def __iter__(self):
        return self


def GenReprWrapWrap(fn=None, **wrap_kwa):
    import functools

    def _wrap(w_fn):
        @functools.wraps(w_fn)
        def _wrapped(*ar, **kwa):
            res = fn(*ar, **kwa)
            if hasattr(res, '__iter__') and hasattr(res, 'next'):
                return GenReprWrap(res, **wrap_kwa)
            return res

        return _wrapped

    if fn is not None:
        return _wrap(fn)

    return _wrap
