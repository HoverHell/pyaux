#!/usr/bin/env python
""" json -> yaml for pretty-reading. """

import sys
import json
import yaml
import argparse
from pyaux.base import colorize_yaml as colorize


def cmd_make_parser(**kwa):
    parser = argparse.ArgumentParser(
        description=(
            "json -> yaml for pretty-reading"
        )
    )
    parser.add_argument(
        '-f', '--no-default-flow-style',
        dest='default_flow_style', action='store_false',
        default=None,
        help="pyyaml's `default_flow_style=False` (generally longer)",
    )
    parser.add_argument(
        '-x', '--default-flow-style',
        dest='default_flow_style', action='store_true',
        default=None,
        help="pyyaml's `default_flow_style=True` (more json-like)",
    )
    parser.add_argument(
        '-c', '--color',
        choices=('yes', 'always', 'no', 'never', 'auto'),
        default='auto',
        nargs='?',
        help=("Colorize the output (requires pygments) (default: 'auto')"
              " (`ls --color` semantics)"),
    )
    # parser.add_argument(
    #     '-c', dest='color', action='store_true',
    #     help="Colorize the output (requires pygments) (same as `--color=yes`)",
    # )
    parser.add_argument(
        '-nu',
        dest='allow_unicode', action='store_false',
        default=True,
        help="Do not allow unicode in output (pyyaml's 'allow_unicode')",
    )

    return parser


def main():

    parser = cmd_make_parser()
    params = parser.parse_args()

    ## TODO?: support input file
    data = sys.stdin.read()
    data_data = json.loads(data)

    kwa = dict(
        default_flow_style=params.default_flow_style,
        allow_unicode=params.allow_unicode,
    )

    out = yaml.safe_dump(data_data, **kwa)

    ## Result:
    ##   `--color=no` always skips this
    ##   `--color`, `--color=yes`, `-c` always do this
    ##   ``, `--color=auto` make this isatty-conditional.
    if ((params.color == 'auto' and sys.stdout.isatty())
            ## NOTE: `'auto'` is default, `None` means it was
            ## specified without an argument (equals to 'always')
            or params.color in ('yes', 'always', True, None)):

        ## pygments doesn't like utf-8 as-is; make it unicode
        if isinstance(out, bytes):
            out = out.decode('utf-8')

        ## TODO?: support --color=auto
        out = colorize(out)

    ## Apply the default encoding and don't even allow to change it
    if isinstance(out, unicode):
        out = out.encode('utf-8')

    ## TODO?: support output file
    sys.stdout.write(out)
    if out[-1] != '\n':  ## Just in case
        sys.stdout.write('\n')
    sys.stdout.flush()


if __name__ == '__main__':
    sys.exit(main())
