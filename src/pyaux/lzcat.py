#!/usr/bin/env python
"""lzcat"""

from __future__ import annotations

import contextlib
import sys
from pathlib import Path
from typing import BinaryIO

try:
    import pylzma
except Exception:
    pylzma = None


def unlzma_i(fi, fo, cm: contextlib.ExitStack, bufs=6553500):
    """Decompress `fi` into `fo` (`file` or filename)"""
    if pylzma is None:
        raise ValueError("`pylzma` is not available")

    if isinstance(fi, str):
        fi = cm.enter_context(Path(fi).open("rb"))  # noqa: SIM115
    if isinstance(fo, str):
        fo = cm.enter_context(Path(fo).open("wb"))  # noqa: SIM115
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


def unlzma(fi, fo, bufs=6553500):
    """Decompress `fi` into `fo` (`file` or filename)"""
    with contextlib.ExitStack() as cm:
        unlzma_i(fi=fi, fo=fo, bufs=bufs, cm=cm)


def _lzcat_main():
    fi_a_raw = sys.argv[1] if len(sys.argv) > 1 else "-"
    fo_a_raw = sys.argv[2] if len(sys.argv) == 3 else "-"
    if len(sys.argv) > 3:
        sys.stderr.write(f"Basic usage: {sys.argv[0]} [<from_file> [<to_file>]]\n")
        sys.exit()

    fi_a: BinaryIO | str = sys.stdin.buffer if fi_a_raw == "-" else fi_a_raw
    fo_a: BinaryIO | str = sys.stdout.buffer if fo_a_raw == "-" else fo_a_raw
    unlzma(fi_a, fo_a)


if __name__ == "__main__":
    _lzcat_main()
