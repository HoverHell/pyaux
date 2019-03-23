#!/usr/bin/env python
''' Serialization formats converter '''

from __future__ import print_function, unicode_literals, absolute_import, division

import sys
import argparse
import functools
from pyaux.iterables import prefetch_first


def _bytes_stdin():
    return getattr(sys.stdin, 'buffer', sys.stdin)


def _bytes_stdout():
    return getattr(sys.stdout, 'buffer', sys.stdout)


# ARG_TRUES = ('yes', 'true', 't', 'y', 1)
# ARG_FALSES = ('no', 'false', 'f', 'n', '0')
# ARG_NULLS = ('', 'null', 'none')
# def argument_bool(value):
#     value = value.lower()
#     if value in ARG_TRUES:
#         return True
#     if value in ARG_FALSES:
#         return False
#     raise argparse.ArgumentTypeError('Boolean value expected.')
# def argument_ternary(value):
#     value = value.lower()
#     if value in ARG_TRUES:
#         return True
#     if value in ARG_FALSES:
#         return False
#     if value in ARG_NULLS:
#         return None
#     raise argparse.ArgumentTypeError('Boolean value expected.')


def cmd_make_parser(**kwa):
    parser = argparse.ArgumentParser(
        description='Serialization formats converter')
    parser.add_argument(
        '-i', '--input',
        default=_bytes_stdin(),
        type=argparse.FileType('rb'),
        help='Source file; empty to use stdin',
    )
    parser.add_argument(
        '-f', '--input-format',
        default='auto',
        choices=('auto', 'json', 'msgp', 'msgpack', 'yaml'),
        help='Serialization format of the input',
    )
    parser.add_argument(
        '-cp', '--input-encoding',
        default='utf-8',
        help=(
            'Character encoding for the input;'
            ' use "" to disable when possible;'
            ' mostly for msgpack'
        ),
    )
    parser.add_argument(
        '-t', '--output-format',
        default='yaml',
        choices=('json', 'msgp', 'msgpack', 'yaml'),
        help='Serialization format for the input',
    )
    parser.add_argument(
        '-ocp', '--output-encoding',
        default='utf-8',
        help='Character encoding for the output',
    )
    parser.add_argument(
        '-o', '--output',
        default=_bytes_stdout(),
        type=argparse.FileType('wb'),
        help='Destination file; empty to use stdout',
    )

    parser.add_argument(
        '-od', '--original-data-on-failure',
        dest='original_data_on_failure', action='store_true',
        help=(
            "Dump the input data on (de)serialization failure"
            " (useful when parsing the output with the eyes)"
            " (default)"
        ),
    )
    parser.add_argument(
        '-nod', '--no-original-data-on-failure',
        dest='original_data_on_failure', action='store_false',
        help="Do not dump the input data on (de)serialization failure")
    parser.set_defaults(original_data_on_failure=True)

    # # YAML
    parser.add_argument(
        '-yf', '--no-default-flow-style',
        dest='default_flow_style', action='store_false',
        help="pyyaml's `default_flow_style=False` (generally larger output) (default is None)",
    )
    parser.add_argument(
        '-yx', '--default-flow-style',
        dest='default_flow_style', action='store_true',
        help="pyyaml's `default_flow_style=True` (more json-like) (default is None)",
    )
    parser.set_defaults(default_flow_style=None)

    # # YAML/JSON
    parser.add_argument(
        '-c', '--color',
        choices=('yes', 'always', 'no', 'never', 'auto'),
        default='auto',
        help=(
            "Colorize the output (requires pygments) (default: 'auto')"
            " (`ls --color` semantics)"
        ),
    )
    parser.add_argument(
        '-u', '--allow-unicode', dest='allow_unicode',
        default='yes', choices=('yes', 'no'),
        help=(
            "Allow non-ascii in output"
            " (yaml's 'allow_unicode', json's 'ensure_ascii')"
        ),
    )
    # # TODO:
    # parser.add_argument(
    #     '-nu',
    #     dest='allow_unicode', action='store_false',
    #     help="Do not allow non-ascii in output (shorthand)",
    # )
    parser.set_defaults(allow_unicode=True)

    parser.add_argument(
        '--indent',
        type=int, default=2,
        help=(
            "Formatting indent; use 0 for compact JSON"
            " (Note: pyyaml seems to ignore indent outside [2, 9])"
        ),
    )

    # Currently JSON-only.
    parser.add_argument(
        '--sk', '--sort-keys', dest='sort_keys',
        default='auto', choices=('yes', 'no', 'auto'),
        help="Sort the keys in mappings (default: yes)")

    return parser


class Bailout(Exception):
    """ Cannot do as requested """


def main():
    parser = cmd_make_parser()
    params = parser.parse_args()
    # TODO: streamed/chunked/prefetched/whatever.
    data_in = params.input.read()
    if not data_in:
        sys.stderr.write('Empty input.\n')
        return 17
    try:
        return main_i(data_in, params)
    except Bailout as exc:
        msg = exc.args[0]
        err_msg_pieces = ['ERROR: f_convert: {}'.format(msg)]
        if params.original_data_on_failure:
            err_msg_pieces.append('; original data as follows (on stdout):')
        err_msg_pieces.append('\n')
        sys.stderr.write(''.join(err_msg_pieces))
        if params.original_data_on_failure:
            _bytes_stdout().write(data_in)
        return 13


def get_json():
    """ Only two versions support most of the required parameters """
    try:
        import simplejson as json
    except Exception:
        import json
    return json


def parse_json(data_in):
    json = get_json()
    # TODO: support json-lines.
    # (but might have to switch to streaming completely for that)
    yield json.loads(data_in)


def parse_yaml(data_in):
    import yaml
    Loader = getattr(yaml, 'CSafeLoader', None) or yaml.SafeLoader
    # TODO: support multi-document streams
    return yaml.load_all(data_in, Loader=Loader)


def parse_msgp(data_in, input_encoding='utf-8'):
    import msgpack
    kwargs = {}
    if input_encoding:
        kwargs.update(encoding=input_encoding)

    # TODO: proper streaming
    try:
        from io import BytesIO as iowrap
    except Exception:
        from cStringIO import StringIO as iowrap
    data_in = iowrap(data_in)

    stream = msgpack.Unpacker(data_in, **kwargs)
    try:
        item = next(stream)
    except StopIteration:
        return
    if isinstance(item, (int, float)):
        raise Exception("msgpack returned a number which is suspicious", item)
    yield item
    for item in stream:
        yield item


def prefetch_first_wrap(func, count=1, require=True):

    @functools.wraps(func)
    def prefetch_first_wrapped(*args, **kwargs):
        result = func(*args, **kwargs)
        return prefetch_first(result, count=count, require=require)

    return prefetch_first_wrapped


def parse_auto(data_in):
    errors = {}
    # TODO: streaming support which would require pre-peeking into data_in.
    try:
        return prefetch_first(parse_json(data_in), require=True)
    except Exception as exc:
        errors.update(json_error=exc)
    try:
        return prefetch_first(parse_yaml(data_in), require=True)
    except Exception as exc:
        errors.update(yaml_error=exc)
    try:
        return prefetch_first(parse_msgp(data_in), require=True)
    except Exception as exc:
        errors.update(msgp_error=exc)
    try:
        return prefetch_first(parse_msgp(data_in, input_encoding=None))
    except Exception as exc:
        errors.update(msgp_bytes_error=exc)
    raise Exception(errors)


def dump_jsons(items, colorize=False, **kwargs):
    json = get_json()
    for item in items:
        res = json.dumps(item, **kwargs)
        # TODO: colorize
        yield res


def dump_yamls(items, colorize=False, **kwargs):
    import yaml
    if colorize:
        from pyaux.base import colorize_yaml
    Dumper = getattr(yaml, 'CSafeDumper', None) or yaml.SafeDumper
    # TODO: streamed
    result = yaml.dump_all(items, Dumper=Dumper, **kwargs)
    if colorize:
        if isinstance(result, bytes):
            result = result.decode('utf-8')
        result = colorize_yaml(result)
    yield result


def dump_msgp(items, use_bin_type=True, **kwargs):
    import msgpack
    for item in items:
        yield msgpack.packb(
            item,
            use_bin_type=use_bin_type,
            **kwargs)


def bailout_wrap(func, err_tpl):

    @functools.wraps(func)
    def bailout_wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            raise Bailout(err_tpl.format(exc=exc))

    return bailout_wrapped


def make_parse_func(params):
    input_format = params.input_format

    if input_format == 'auto':
        parse_func = parse_auto
        err_tpl = 'Error parsing as JSON/YAML/MSGPACK: {exc}'
    elif input_format == 'json':
        parse_func = parse_json
        err_tpl = 'Error parsing as JSON: {exc}'
    elif input_format == 'yaml':
        parse_func = parse_yaml
        err_tpl = 'Error parsing as YAML: {exc}'
    elif input_format in ('msgp', 'msgpack'):
        parse_func = functools.partial(
            parse_msgp,
            input_encoding=params.input_encoding)
        err_tpl = 'Error parsing as MsgPack: {exc}'
    else:
        raise Exception("Unknown input_format")

    parse_func = prefetch_first_wrap(parse_func)
    parse_func = bailout_wrap(parse_func, err_tpl)

    return parse_func


def make_outs_func(params):
    isatty = params.output is _bytes_stdout() and sys.stdout.isatty()

    output_format = params.output_format
    colorize = (
        params.color == 'yes' or
        (params.color == 'auto' and isatty))
    # TODO: add the 'auto => unsorted in py3.7+' feature for JSON and YAML
    sort_keys = params.sort_keys in ('yes', 'auto')

    if output_format == 'json':
        outs_func = functools.partial(
            dump_jsons,
            ensure_ascii=not params.allow_unicode,
            colorize=colorize,
            sort_keys=sort_keys,
            indent=params.indent or None,
            # separators=(',',':'),
            # default=repr,
        )
    elif output_format == 'yaml':

        # TODO: overridable 'width' parameter.
        # Try using the whole terminal width:
        width = None
        try:
            import shutil
            # magic '8'
            width = shutil.get_terminal_size().columns - 8
        except Exception:  # pylint: disable=broad-except
            pass

        outs_func = functools.partial(
            dump_yamls,
            allow_unicode=params.allow_unicode,
            colorize=colorize,
            indent=params.indent or 2,
            default_flow_style=params.default_flow_style,
            width=width,
        )
    elif output_format in ('msgp', 'msgpack'):
        outs_func = dump_msgp
    else:
        raise Exception("Unknown output_format")

    err_tpl = 'Error serializing as {}: {{exc}}'.format(output_format)
    outs_func = prefetch_first_wrap(outs_func)
    outs_func = bailout_wrap(outs_func, err_tpl)

    return outs_func


def main_i(data_in, params):

    parse_func = make_parse_func(params)
    outs_func = make_outs_func(params)

    datas = parse_func(data_in)
    outs_data = outs_func(datas)

    output = params.output

    out_item = None
    for out_item in outs_data:
        if not isinstance(out_item, bytes):
            out_item = out_item.encode(params.output_encoding)
        output.write(out_item)

    if out_item is not None and out_item[-1] != b'\n':
        output.write(b'\n')

    return 0


if __name__ == '__main__':
    sys.exit(main())
