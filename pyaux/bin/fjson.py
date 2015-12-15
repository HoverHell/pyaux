#!/usr/bin/env python
# coding: utf8

import os
import json
import sys

from pyaux.base import to_bytes


def main():
    indent = int(os.environ.get('INDENT') or '2')
    data_in = sys.stdin.read()

    def bailout(msg):
        sys.stderr.write(
            "ERROR: fjson.py: %s; original data as follows (on stdout)\n" % (msg,))
        sys.stdout.write(data_in)
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

    sys.stdout.write(to_bytes(data_out))
    sys.stdout.write("\n")
    sys.stdout.flush()


if __name__ == '__main__':
    sys.exit(main())
