#!/usr/bin/env python

import os
import sys
import json

from pyaux.base import to_bytes


def main():
    import msgpack
    indent = int(os.environ.get('INDENT') or '2')
    try:
        data_in = sys.stdin.buffer
    except AttributeError:
        data_in = sys.stdin

    try:
        stream = msgpack.Unpacker(data_in)  # , encoding="utf-8")
        for item in stream:
            try:
                data_out = json.dumps(item, indent=indent, sort_keys=True, ensure_ascii=False)
            except Exception as exc:
                data_out = "# (json failed: %r)  # %r" % (exc, item)
            sys.stdout.write(data_out)
            sys.stdout.write("\n")
            sys.stdout.flush()
    except Exception as exc:
        sys.stderr.write("#  -!!---- %s\n" % (exc,))
        sys.stdout.write(repr(data_in.read()))
        return 13


if __name__ == '__main__':
    sys.exit(main())
