#!/usr/bin/env python
""" lzcat """

from __future__ import annotations

import sys

import pylzma

from pyaux.lzmah import get_stdin, get_stdout


def unlzma(fi, fo, fi_close=True, fo_close=True, bufs=6553500):
    """Decompress `fi` into `fo` (`file` or filename)"""
    if isinstance(fi, str):
        fi = open(fi, "rb")
        fi_close = True
    if isinstance(fo, str):
        fo = open(fo, "wb")
        fo_close = True
    # i.seek(0)

    # XXXX: better way?
    #  * s.decompress *requires* an `output buffer size`, i.e. size of the
    #   unpacked data, otherwise packed data is stored in internal buffers
    #   and returned on flush (which gets problematic).
    #  * Suggested default is to read by 1 byte and use the default buffer
    #   size.  Which gets slow.
    #  * Nearest hax to fix is to use output buffer over 30x (or something)
    #   the size of input buffer.  Which is not a nice thing to do, but
    #   works...  mostly.
    #  * ... anyway, symptoms: slowdown on decompression down to zero speed,
    #   high memory usage (up to almost size of the uncompressed file),
    #   after which all the decompressed data is written in one go.
    in_bufs = int(bufs / 100)
    s = pylzma.decompressobj()
    while True:
        tmp = fi.read(in_bufs)
        if not tmp:
            break
        fo.write(s.decompress(tmp, bufs))
    fo.write(s.flush())
    if fo_close:
        fo.close()
    if fi_close:
        fi.close()
    return fi, fo


def _lzcat_main():
    if len(sys.argv) > 1:
        fi_a = sys.argv[1]
    else:
        fi_a = "-"
    if len(sys.argv) == 3:
        fo_a = sys.argv[2]
    else:
        fo_a = "-"
    if len(sys.argv) > 3:
        sys.stderr.write(f"Basic usage: {sys.argv[0]} [<from_file> [<to_file>]]\n")
        sys.exit()

    if fi_a == "-":
        fi_a = get_stdin()
    if fo_a == "-":
        fo_a = get_stdout()
    unlzma(fi_a, fo_a)


if __name__ == "__main__":
    _lzcat_main()
