#!/usr/bin/env python
""" lzma (pylzma) helpers.
Also can be used as a script for compressing a file.
"""

from __future__ import print_function, unicode_literals, absolute_import, division

import sys
import pylzma


def lzma_compress(fi, fo, fi_close=True, fo_close=True, bufs=65535):
    """ Compress `fi` into `fo` (`file` or filename) """
    if isinstance(fi, str):
        fi, fi_n = open(fi, 'rb'), fi
        #fi_close = True
    if isinstance(fo, str):
        fo, fo_n = open(fo, 'wb'), fo
        #fo_close = True
    #fi.seek(0)
    s = pylzma.compressfile(fi)
    while True:
        tmp = s.read(bufs)
        if not tmp:
            break
        fo.write(tmp)
    if fo_close:
        fo.close()
    if fi_close:
        fi.close()
    return fi, fo


class _IgnoreTheError(Exception):
    """ Used in `unjsllzma` to signify that the exception should be simply ignored
    """


def _handle_fail_default(v, e):
    raise _IgnoreTheError
    # supposedly can do simple `raise` to re-raise the original (parse) exception


def unjsllzma(fi, fi_close=True, parse_fn=None, handle_fail=None, bufs=655350):
    """ Make a generator for reading an lzma-compressed file with
    json(or something else) in lines.
    `parse_fn` is th function(v) to process lines with (defaults to
      `json.loads`)
    `handle_fail` if a fuction(value, exception) for handling a failure to
    parse the value; value is skipped if it raises _IgnoreTheError
    exception, otherwise its return value is yielded.  default: skip all
    failures.
    """
    if parse_fn is None:
        try:
            import simplejson as json
        except ImportError:
            print("Error importing (preferred) simplejson")
            import json
        parse_fn = json.loads

    if handle_fail is None:
        handle_fail = _handle_fail_default

    def try_loads(v):
        try:
            return parse_fn(v)
        except Exception as e:
            return handle_fail(v, e)

    if isinstance(fi, str):
        fi = open(fi, 'rb')

    tmp2 = ''  # buffer for unfunushed lines
    in_bufs = int(bufs / 100)  # XXX: see lzcat.py note around in_bufs
    s = pylzma.decompressobj()
    cont = True
    while cont:
        tmp = fi.read(in_bufs)
        if not tmp:  # nothing more can be read
            tmp2 += s.flush()
            cont = False
        else:
            # XXX: TODO: use bytearray.extend (likely).
            tmp2 = tmp2 + s.decompress(tmp, bufs)
        tmp3 = tmp2.split('\n')  # finished and unfinished lines
        for v in tmp3[:-1]:
            try:
                r = try_loads(v)
            except _IgnoreTheError:
                continue  # no more handling requested, just skip it
            yield r
        tmp2 = tmp3[-1]
    if fi_close:
        fi.close()


def get_stdin():
    """
    Get a stdin fileobject that can (possibly) read bytes.
    """
    try:
        return sys.stdin.buffer  # py3
    except AttributeError:
        return sys.stdin  # py2


def get_stdout():
    """
    Get stdout fileobject that can possibly read bytes.
    """
    try:
        return sys.stdout.buffer  # py3
    except AttributeError:
        return sys.stdout  # py2


def _lzma_main():
    fi_a = sys.argv[1]
    fo_a = sys.argv[2]

    if fi_a == '-':
        fi_a = get_stdin()
    if fo_a == '-':
        fo_a = get_stdout()
    lzma_compress(fi_a, fo_a)


if __name__ == '__main__':
    _lzma_main()
