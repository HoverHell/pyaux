# coding: utf8
"""
Wide variety of helper methods for working with iterables.

A kind-of addition to `itertools`.
"""

from __future__ import print_function, unicode_literals, absolute_import, division

import os
from itertools import chain, repeat, islice


__all__ = (
    'window',
    'reversed_blocks',
    'reversed_lines',
    'uniq_g',
    'IterStat',
    'IterMean',
    'chunks_g',
    'next_or_fdefault',
    'iterator_is_over',
)


# Iterate over a 'window' of adjacent elements
# http://stackoverflow.com/questions/6998245/iterate-over-a-window-of-adjacent-elements-in-python
def window(seq, size=2, fill=0, fill_left=False, fill_right=False):
    """ Returns a sliding window (of width n) over data from the iterable:
      s -> (s0,s1,...s[n-1]), (s1,s2,...,sn), ...
    """
    ssize = size - 1
    it = chain(
        repeat(fill, ssize * fill_left),
        iter(seq),
        repeat(fill, ssize * fill_right))
    result = tuple(islice(it, size))
    if len(result) == size:  # `<=` if okay to return seq if len(seq) < size
        yield result
    for elem in it:
        result = result[1:] + (elem,)
        yield result


# ###### Reading files backwards
# http://stackoverflow.com/a/260433/62821

def reversed_blocks(fileobj, blocksize=4096):
    """ Read blocks of file's contents in reverse order.  """
    fileobj.seek(0, os.SEEK_END)
    here = fileobj.tell()
    while here > 0:
        delta = min(blocksize, here)
        fileobj.seek(here - delta, os.SEEK_SET)
        yield fileobj.read(delta)
        here -= delta


def reversed_lines(fileobj):
    """ Read the lines of file in reverse order """
    tail = []           # Tail of the line whose head is not yet read.
    for block in reversed_blocks(fileobj):
        # A line is a list of strings to avoid quadratic concatenation.
        # (And trying to avoid 1-element lists would complicate the code.)
        linelists = [[line] for line in block.splitlines()]
        linelists[-1].extend(tail)
        for linelist in reversed(linelists[1:]):
            yield ''.join(linelist)
        tail = linelists[0]
    if tail:
        yield ''.join(tail)


def uniq_g(lst, key=lambda value: value):
    """
    Get unique elements of an iterable preserving its order and optionally
    determining uniqueness by hash of a key.
    """
    # TODO?: try `key=lambda value: hash(value)`, check the memory and speed performance.
    known = set()
    for value in lst:
        value_key = key(value)
        if value_key not in known:
            yield value
            known.add(value_key)


uniq = uniq_g


class IterStat(object):
    """
    Iterative single-pass computing of mean and variance.

    Error is on the rate of 1e-08 for 1e6 values in the range of
    0..1e6, both for mean and for stddev.

    http://www.johndcook.com/standard_deviation.html
    """

    def __init__(self, vals=None, start=0):
        self.start = start
        self.old_mean = None
        self.mean = self.stdx = start
        self.cnt = 0

        if vals:
            for val in vals:
                self.send(val)

    def send(self, val):
        self.cnt += 1
        if self.cnt == 1:
            self.mean = val
        else:
            self.mean = self.mean + (val - self.mean) / float(self.cnt)
            self.stdx = self.stdx + (val - self.old_mean) * (val - self.mean)
        self.old_mean = self.mean

    @property
    def variance(self):
        if self.cnt <= 1:
            return self.start
        return self.stdx / (self.cnt)

    @property
    def std(self):
        from .base import _sqrt
        return _sqrt(self.variance)


def IterMean(iterable, dtype=float):
    """ Mean of an iterable """
    res_sum, cnt = dtype(), dtype()
    for val in iterable:
        res_sum += val
        cnt += 1
    if cnt == 0:  # NOTE.
        try:
            return dtype('nan')
        except Exception:
            return float('nan')
    return res_sum / cnt


def chunks_g(iterable, size):
    """
    Same as 'chunks' but works on any iterable.

    Converts the chunks to tuples for simplicity.

    http://stackoverflow.com/a/8991553
    """
    it = iter(iterable)
    if size <= 0:
        yield it
        return
    while True:
        chunk = tuple(islice(it, size))
        if not chunk:
            return
        yield chunk


def next_or_fdefault(it, default=lambda: None, skip_empty=False):
    """
    `next(it, default_value)` with laziness.

    >>> next_or_fdefault([1], lambda: 1/0)
    1
    >>> next_or_fdefault([], lambda: list(range(2)))
    [0, 1]
    """
    if skip_empty:
        it = (val for val in it if val)
    else:
        it = iter(it)
    try:
        return next(it)
    except StopIteration:
        return default()


def iterator_is_over(it, ret_value=False):
    """
    Try to consume an item from an iterable `it` and return False if it
    succeeded (the item stays consumed).
    """
    try:
        val = next(it)
    except StopIteration:
        if ret_value:
            return True, None
        return True
    else:
        if ret_value:
            return False, val
        return False
