#!/usr/bin/env python
# coding: utf8

import os
import json
import sys

from pyaux.base import to_bytes


def main():
    indent = int(os.environ.get('INDENT') or '2')
    data_in = sys.stdin.read()

    try:
        data = json.loads(data_in)
    except ValueError as exc:
        sys.stderr.write("#  -!!---- %s\n" % (exc,))
        sys.stdout.write(data_in)
        return 13
    data_out = json.dumps(
        data, indent=indent, sort_keys=True, ensure_ascii=False)
    sys.stdout.write(to_bytes(data_out))
    sys.stdout.write("\n")


if __name__ == '__main__':
    sys.exit(main())
