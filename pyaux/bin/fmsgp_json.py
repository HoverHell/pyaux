#!/usr/bin/env python

import os
import sys
import json

from pyaux.base import to_bytes


def main():
    import msgpack
    indent = int(os.environ.get('INDENT') or '2')
    data_in = sys.stdin.read()
    try:
        data = msgpack.loads(data_in)
    except Exception as exc:
        sys.stderr.write("#  -!!---- %s\n" % (exc,))
        sys.stdout.write(repr(data_in))
        return 13

    data_out = json.dumps(data, indent=indent, sort_keys=True, ensure_ascii=False)
    sys.stdout.write(to_bytes(data_out))
    sys.stdout.write("\n")


if __name__ == '__main__':
    sys.exit(main())
