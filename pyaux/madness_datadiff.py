# coding: utf8
""" madstuff: datadiff stuff """

from __future__ import print_function, unicode_literals, absolute_import, division

import re
import yaml
import difflib
import itertools
from pyaux.base import colorize_yaml, colorize_diff, to_unicode


__all__ = (
    '_dumprepr',
    '_diff_pre_diff', '_diff_datadiff_data', 'datadiff', 'p_datadiff',
)


def _dumprepr(val, no_anchors=True, colorize=False, try_ujson=True, **kwa):
    """ Advanced-ish representation of an object (using YAML) """
    dumper = yaml.SafeDumper

    # NOTE: this means it'll except on infinitely-recursive data.
    if no_anchors:
        dumper = type(
            b'NoAliasesSafeDumper', (dumper,),
            dict(ignore_aliases=lambda self, data: True))

    params = dict(default_flow_style=False, allow_unicode=True,
                  encoding=None,  # return text
                  Dumper=dumper)
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
        prepared_value = ujson.loads(ujson.dumps(val))
        res += maybe_colorize(yaml.dump(prepared_value, **params))

    return res


def _diff_pre_diff(val, **kwa):
    """ Prepare a value for diff-ing """
    _repr = kwa.get('_repr', _dumprepr)
    res = _repr(val, **kwa)
    res = res.splitlines()
    return res


def word_diff_color(val1, val2, add='\x1b[32m', rem='\x1b[31;01m',
                    clear='\x1b[39;49;00m'):
    """ Proper-ish word-diff represented by colors """

    def _preprocess(val):
        return re.split(r'(?u)(\w+)', val)

    diffs = difflib.unified_diff(_preprocess(val1), _preprocess(val2))

    def _postprocess(line):
        if line == '--- \n' or line == '+++ \n':
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


def _diff_datadiff_data(val1, val2, **kwa):
    """ Do the diff and return the data """
    val1_p = _diff_pre_diff(val1, **kwa)
    val2_p = _diff_pre_diff(val2, **kwa)
    res = difflib.unified_diff(val1_p, val2_p)
    return res


def datadiff(val1, val2, colorize=False, colorize_yaml=False, **kwa):
    """ Return a values diff string """
    kwa['colorize'] = colorize_yaml  # NOTE: controversial
    data = _diff_datadiff_data(val1, val2, **kwa)

    # line_limit
    _ll = kwa.pop('line_limit', 200)
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
        res = colorize_diff(res, **kwa)
    return res


def p_datadiff(val1, val2, **kwa):
    """ Print the values diff """
    # TODO: yaml coloring *and* diff coloring?
    print(datadiff(val1, val2, **kwa))
