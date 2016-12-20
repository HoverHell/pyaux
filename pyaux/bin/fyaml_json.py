#!/usr/bin/env python
""" yaml -> json for pretty-writing. """

import os
import sys
try:
    import simplejson as json
except Exception:
    import json
import yaml
import argparse
from pyaux.base import to_bytes


def cmd_make_parser(**kwa):
    parser = argparse.ArgumentParser(
        description=(
            "yaml -> json for pretty-writing"
        )
    )
    parser.add_argument(
        '-nu',
        dest='ensure_ascii', action='store_true',
        default=False,
        help="Do not allow unicode in output (reverse of json's 'ensure_ascii')",
    )
    parser.add_argument(
        '-i', '--indent',
        dest='indent',
        default=None,
        help="Indentation ('-' to disable pretty-formatting)",
    )
    parser.add_argument(
        '-c', '--compact',
        dest='compact', action='store_true',
        default=False,
        help="Compact representation (without some of the extra whitespaces)",
    )

    return parser


def main():

    parser = cmd_make_parser()
    params = parser.parse_args()

    # TODO?: support input file
    data_in = sys.stdin.read()

    def bailout(msg):
        sys.stderr.write(
            "ERROR: fjson_yaml: %s; original data as follows (on stdout)\n" % (msg,))
        sys.stdout.write(data_in)
        return 13

    Loader = getattr(yaml, 'CSafeLoader', None) or yaml.SafeLoader
    try:
        data_data = yaml.load(data_in, Loader=Loader)
    except Exception as exc:
        return bailout("Error parsing as yaml: %s" % (exc,))

    kwa = dict(
        ensure_ascii=params.ensure_ascii,
    )
    if params.indent is None:
        kwa['indent'] = None if params.compact else 2
    elif params.indent == '-':
        kwa['indent'] = None
    else:
        kwa['indent'] = int(params.indent)
    kwa['separators'] = (',', ':') if params.compact else None

    try:
        out = json.dumps(data_data, **kwa)
    except Exception as exc:
        return bailout("Error dumping as json: %s" % (exc,))

    # TODO?: support output file
    sys.stdout.write(to_bytes(out))
    if out[-1] != '\n':  # Just in case
        sys.stdout.write('\n')
    sys.stdout.flush()


if __name__ == '__main__':
    sys.exit(main())
