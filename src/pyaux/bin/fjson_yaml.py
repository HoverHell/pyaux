#!/usr/bin/env python
""" json -> yaml for pretty-reading. """
from __future__ import annotations

import argparse
import os
import sys

import yaml

from pyaux.base import colorize_yaml as colorize, to_text


def cmd_make_parser(**kwa):
    parser = argparse.ArgumentParser(description=("json -> yaml for pretty-reading"))
    parser.add_argument(
        "-f",
        "--no-default-flow-style",
        dest="default_flow_style",
        action="store_false",
        default=None,
        help="pyyaml's `default_flow_style=False` (generally longer)",
    )
    parser.add_argument(
        "-x",
        "--default-flow-style",
        dest="default_flow_style",
        action="store_true",
        default=None,
        help="pyyaml's `default_flow_style=True` (more json-like)",
    )
    parser.add_argument(
        "-s",
        "--sort-keys",
        dest="sort_keys",
        action="store_true",
        default=False,
        help="sort dict keys",
    )
    parser.add_argument(
        "-c",
        "--color",
        choices=("yes", "always", "no", "never", "auto"),
        default="auto",
        nargs="?",
        help=(
            "Colorize the output (requires pygments) (default: 'auto')" " (`ls --color` semantics)"
        ),
    )
    # parser.add_argument(
    #     '-c', dest='color', action='store_true',
    #     help="Colorize the output (requires pygments) (same as `--color=yes`)",
    # )
    parser.add_argument(
        "-nu",
        dest="allow_unicode",
        action="store_false",
        default=True,
        help="Do not allow unicode in output (pyyaml's 'allow_unicode')",
    )

    return parser


def main():

    parser = cmd_make_parser()
    params = parser.parse_args()

    # TODO?: support input file
    data_in = sys.stdin.read()

    def bailout(msg):
        sys.stderr.write(f"ERROR: fjson_yaml: {msg}; original data as follows (on stdout)\n")
        sys.stdout.write(data_in)
        return 13

    try:
        data_data = yaml.safe_load(data_in)
    except Exception as exc:
        return bailout(f"Error parsing as json/yaml: {exc}")

    kwa = dict(
        default_flow_style=params.default_flow_style,
        allow_unicode=params.allow_unicode,
        sort_keys=params.sort_keys,
    )
    try:
        kwa["width"] = int(os.environ["WIDTH"])
    except Exception:
        pass

    try:
        out = yaml.safe_dump(data_data, **kwa)
    except Exception as exc:
        return bailout(f"Error dumping as yaml: {exc}")

    # Result:
    #   `--color=no` always skips this
    #   `--color`, `--color=yes`, `-c` always do this
    #   ``, `--color=auto` make this isatty-conditional.
    if (
        (params.color == "auto" and sys.stdout.isatty())
        # NOTE: `'auto'` is default, `None` means it was
        # specified without an argument (equals to 'always')
        or params.color in ("yes", "always", True, None)
    ):
        # pygments doesn't like utf-8 as-is; make it unicode
        if isinstance(out, bytes):
            out = out.decode("utf-8")

        # TODO?: support --color=auto
        out = colorize(out)

    # TODO?: support output file
    sys.stdout.write(to_text(out))
    if out[-1] != "\n":  # Just in case
        sys.stdout.write("\n")
    sys.stdout.flush()


if __name__ == "__main__":
    sys.exit(main())
