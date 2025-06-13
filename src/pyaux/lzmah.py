#!/usr/bin/env python
"""
lzma (pylzma) helpers.
Also can be used as a script for compressing a file.
"""

from __future__ import annotations

import contextlib
import sys
from pathlib import Path
from typing import BinaryIO

try:
    import pylzma
except Exception:
    pylzma = None


def lzma_compress_i(fi, fo, cm: contextlib.ExitStack, bufs=65535):
    if pylzma is None:
        raise ValueError("`pylzma` is not available")

    if isinstance(fi, str):
        fi = cm.enter_context(Path(fi).open("rb"))  # noqa: SIM115
    if isinstance(fo, str):
        fo = cm.enter_context(Path(fo).open("wb"))  # noqa: SIM115
    # fi.seek(0)
    s = pylzma.compressfile(fi)
    while True:
        tmp = s.read(bufs)
        if not tmp:
            break
        fo.write(tmp)
    return fi, fo


def lzma_compress(fi, fo, bufs=65535):
    """Compress `fi` into `fo` (fileobj or filename)"""
    with contextlib.ExitStack() as cm:
        return lzma_compress_i(fi=fi, fo=fo, bufs=bufs, cm=cm)


class _IgnoreTheError(Exception):
    """Used in `unjsllzma` to signify that the exception should be simply ignored"""


def _handle_fail_default(v, e):
    raise _IgnoreTheError
    # supposedly can do simple `raise` to re-raise the original (parse) exception


def unjsllzma_i(fi, cm: contextlib.ExitStack, parse_fn=None, handle_fail=None, bufs=655350):
    if pylzma is None:
        raise ValueError("`pylzma` is not available")

    if parse_fn is None:
        try:
            import orjson

            parse_fn = orjson.loads
        except ImportError:
            sys.stderr.write("Error importing (preferred) `orjson`\n")
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
        fi = cm.enter_context(Path(fi).open("rb"))  # noqa: SIM115

    tmp2 = ""  # buffer for unfunushed lines
    in_bufs = int(bufs / 100)  # see lzcat.py note around in_bufs
    decomp = pylzma.decompressobj()
    cont = True
    while cont:
        tmp = fi.read(in_bufs)
        if not tmp:  # nothing more can be read
            tmp2 += decomp.flush()
            cont = False
        else:
            # TODO: use bytearray.extend (likely).
            tmp2 = tmp2 + decomp.decompress(tmp, bufs)
        tmp3 = tmp2.split("\n")  # finished and unfinished lines
        for val in tmp3[:-1]:
            try:
                res = try_loads(val)
            except _IgnoreTheError:
                continue  # no more handling requested, just skip it
            yield res
        tmp2 = tmp3[-1]


def unjsllzma(fi, parse_fn=None, handle_fail=None, bufs=655350):
    """
    Make a generator for reading an lzma-compressed file with
    json(or something else) in lines.
    `parse_fn` is th function(v) to process lines with (defaults to
      `json.loads`)
    `handle_fail` if a fuction(value, exception) for handling a failure to
    parse the value; value is skipped if it raises _IgnoreTheError
    exception, otherwise its return value is yielded.  default: skip all
    failures.
    """
    with contextlib.ExitStack() as cm:
        return unjsllzma_i(fi=fi, parse_fn=parse_fn, handle_fail=handle_fail, bufs=bufs, cm=cm)


def _lzma_main():
    fi_a_raw = sys.argv[1]
    fo_a_raw = sys.argv[2]

    fi_a: BinaryIO | str = sys.stdin.buffer if fi_a_raw == "-" else fi_a_raw
    fo_a: BinaryIO | str = sys.stdout.buffer if fo_a_raw == "-" else fo_a_raw
    lzma_compress(fi_a, fo_a)


if __name__ == "__main__":
    _lzma_main()
