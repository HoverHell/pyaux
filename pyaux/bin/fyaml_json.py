#!/usr/bin/env python
# pylint: disable=broad-except
""" yaml -> json for pretty-writing. """

# import os
import sys
import argparse
try:
    import simplejson as json
except Exception:
    import json
import yaml
from pyaux.base import to_str


def cmd_make_parser():
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

    json_kwargs = dict(
        ensure_ascii=params.ensure_ascii,
    )
    if params.indent is None:
        json_kwargs['indent'] = None if params.compact else 2
    elif params.indent == '-':
        json_kwargs['indent'] = None
    else:
        json_kwargs['indent'] = int(params.indent)
    if params.compact:
        json_kwargs['separators'] = (',', ':')

    try:
        out = json.dumps(data_data, **json_kwargs)
    except Exception as exc:
        return bailout("Error dumping as json: %s" % (exc,))

    # TODO?: support output file
    sys.stdout.write(to_str(out))
    if out[-1] != '\n':  # Just in case
        sys.stdout.write('\n')
    sys.stdout.flush()


if __name__ == '__main__':
    sys.exit(main())
