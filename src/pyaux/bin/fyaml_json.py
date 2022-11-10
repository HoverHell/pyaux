#!/usr/bin/env python
# pylint: disable=broad-except
""" yaml -> json for pretty-writing. """

import argparse
import json
import sys

import yaml


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
            f"ERROR: fjson_yaml: {msg}; original data as follows (on stdout)\n")
        sys.stdout.write(data_in)
        return 13

    Loader = getattr(yaml, 'CSafeLoader', None) or yaml.SafeLoader
    try:
        data_data = yaml.load(data_in, Loader=Loader)
    except Exception as exc:
        return bailout(f"Error parsing as yaml: {exc}")

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
        return bailout(f"Error dumping as json: {exc}")

    sys.stdout.write(out)
    if out[-1] != '\n':  # Just in case
        sys.stdout.write('\n')
    sys.stdout.flush()


if __name__ == '__main__':
    sys.exit(main())
