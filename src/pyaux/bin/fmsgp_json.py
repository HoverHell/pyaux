#!/usr/bin/env python
from __future__ import annotations

import json
import os
import sys


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
                data_out = f"# (json failed: {exc!r})  # {item!r}"
            sys.stdout.write(data_out)
            sys.stdout.write("\n")
            sys.stdout.flush()
    except Exception as exc:
        sys.stderr.write(f"#  -!!---- {exc}\n")
        sys.stdout.write(repr(data_in.read()))
        return 13


if __name__ == '__main__':
    sys.exit(main())
