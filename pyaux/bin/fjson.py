#!/usr/bin/env python
# coding: utf8

from __future__ import print_function, unicode_literals, absolute_import, division

import os
import json
import sys

from pyaux.base import to_bytes


def main():
    indent = int(os.environ.get('INDENT') or '2')
    if len(sys.argv) >= 2:
        with open(sys.argv[1]) as fo:
            data_in = fo.read()
    else:
        data_in = sys.stdin.read()

    try:
        outbuf = sys.stdout.buffer
    except AttributeError:
        outbuf = sys.stdout

    def bailout(msg):
        sys.stderr.write(
            "ERROR: fjson.py: %s; original data as follows (on stdout)\n" % (msg,))
        outbuf.write(data_in)
        return 13

    try:
        data = json.loads(data_in)
    except Exception as exc:
        return bailout("Error parsing as json: %s" % (exc,))

    try:
        data_out = json.dumps(
            data, indent=indent, sort_keys=True, ensure_ascii=False)
    except Exception as exc:
        return bailout("Error dumping as json: %s" % (exc,))

    outbuf.write(to_bytes(data_out))
    outbuf.write(b"\n")
    outbuf.flush()


if __name__ == '__main__':
    sys.exit(main())
