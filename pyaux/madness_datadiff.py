# coding: utf8
""" madstuff: datadiff stuff """

from __future__ import print_function, unicode_literals, absolute_import, division

import re
import sys
import difflib
import itertools

import yaml

from .base import colorize_yaml, colorize_diff


__all__ = (
    '_dumprepr',
    '_diff_pre_diff', '_diff_datadiff_data', 'datadiff', 'p_datadiff',
)


def _dumprepr(val, no_anchors=True, colorize=False, try_ujson=True, allow_unsorted_dicts=False, **kwa):
    """ Advanced-ish representation of an object (using YAML) """
    dumper = yaml.SafeDumper

    # NOTE: this means it'll except on infinitely-recursive data.
    if no_anchors:

        class NoAliasesSafeDumper(dumper):

            def ignore_aliases(self, *args, **kwargs):  # pylint: disable=arguments-differ
                return True

        dumper = NoAliasesSafeDumper

    if allow_unsorted_dicts and sys.version_info >= (3, 7):
        from yaml.nodes import MappingNode, ScalarNode

        class UnsortingDumper(dumper):
            """ ... """

            def represent_mapping(self, tag, mapping, flow_style=None):
                value = []
                node = MappingNode(tag, value, flow_style=flow_style)
                if self.alias_key is not None:
                    self.represented_objects[self.alias_key] = node
                best_style = True
                if hasattr(mapping, 'items'):
                    mapping = list(mapping.items())
                for item_key, item_value in mapping:
                    node_key = self.represent_data(item_key)
                    node_value = self.represent_data(item_value)
                    if not (isinstance(node_key, ScalarNode) and not node_key.style):
                        best_style = False
                    if not (isinstance(node_value, ScalarNode) and not node_value.style):
                        best_style = False
                    value.append((node_key, node_value))
                if flow_style is None:
                    if self.default_flow_style is not None:
                        node.flow_style = self.default_flow_style
                    else:
                        node.flow_style = best_style
                return node

        dumper = UnsortingDumper

    params = dict(
        # Convenient upper-level kwarg for the most often overridden thing:
        default_flow_style=kwa.pop('default_flow_style', False),
        allow_unicode=True,
        encoding=None,  # return text
        Dumper=dumper,
    )
    params.update(kwa.get('yaml_kwa', {}))

    def maybe_colorize(text):
        if not colorize:
            return text
        return colorize_yaml(text, **kwa)

    res = ''
    try:
        res += maybe_colorize(yaml.dump(val, **params))
    except Exception as exc:
        if not try_ujson:
            raise
        # ujson can handle many objects somewhat-successfully. But can
        # segfault while doing that.
        import ujson
        res += "# Unable to serialize directly! (%r)\n" % (exc,)
        prepared_value = ujson.loads(ujson.dumps(val))  # pylint: disable=c-extension-no-member
        res += maybe_colorize(yaml.dump(prepared_value, **params))

    return res


def _diff_pre_diff(val, **kwa):
    """ Prepare a value for diff-ing """
    _repr = kwa.get('_repr', _dumprepr)
    res = _repr(val, **kwa)
    res = res.splitlines()
    return res


def word_diff_color(val1, val2, add='\x1b[32m', rem='\x1b[31;01m',
                    clear='\x1b[39;49;00m', n=3):
    """ Proper-ish word-diff represented by colors """

    def _preprocess(val):
        return re.split(r'(?u)(\w+)', val)

    diffs = difflib.unified_diff(_preprocess(val1), _preprocess(val2), n=n)

    def _postprocess(line):
        if line in ('--- \n', '+++ \n'):
            return ''
        if line.startswith('+'):
            color = add
        elif line.startswith('-'):
            color = rem
        else:
            color = ''
        return '%s%s%s' % (color, line[1:], clear)

    diffs = list(diffs)
    diffs_colored = (_postprocess(line) for line in diffs)
    # return diffs_colored
    print(''.join(diffs_colored))


def _diff_datadiff_data(val1, val2, n=3, **kwa):
    """ Do the diff and return the data """
    val1_p = _diff_pre_diff(val1, **kwa)
    val2_p = _diff_pre_diff(val2, **kwa)
    res = difflib.unified_diff(val1_p, val2_p, n=n)
    return res


def datadiff(val1, val2, colorize=False, colorize_as_yaml=False, **kwargs):
    """ Return a values diff string """
    kwargs['colorize'] = colorize_as_yaml  # NOTE: controversial
    data = _diff_datadiff_data(val1, val2, **kwargs)

    # line_limit
    _ll = kwargs.pop('line_limit', 200)
    if _ll:
        data_base = data
        data = list(itertools.islice(data_base, _ll))
        try:
            next(data_base)
        except StopIteration:
            pass
        else:
            data.append('...')  # u'…'

    res = '\n'.join(data)
    if colorize:
        res = colorize_diff(res, **kwargs)
    return res


def p_datadiff(val1, val2, **kwargs):
    """ Print the values diff """
    # TODO: yaml coloring *and* diff coloring?
    print(datadiff(val1, val2, **kwargs))
