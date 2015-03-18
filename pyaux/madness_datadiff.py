# coding: utf8
""" madstuff: datadiff stuff """

import yaml
import difflib
import itertools


__all__ = (
    '_dumprepr',
    '_diff_pre_diff', '_diff_datadiff_data', 'datadiff', 'p_datadiff',
)


def _dumprepr(val, no_anchors=True, **kwa):
    """ Advanced-ish representation of an object (using YAML) """
    dumper = yaml.SafeDumper

    # NOTE: this means it'll except on infinitely-recursive data.
    if no_anchors:
        dumper = type(
            'NoAliasesSafeDumper', (dumper,),
            dict(ignore_aliases=lambda self, data: True))

    params = dict(default_flow_style=False, Dumper=dumper)
    params.update(kwa.get('yaml_kwa', {}))

    res = ''
    try:
        res += yaml.dump(val, **params)
    except Exception:
        # ujson can handle many objects somewhat-successfully. But can
        # segfault while doing that.
        import ujson
        res += "# Unable to serialize directly!\n"
        prepared_value = ujson.loads(ujson.dumps(val))
        res += yaml.dump(prepared_value, **params)

    return res


def _diff_pre_diff(val, **kwa):
    """ Prepare a value for diff-ing """
    _repr = kwa.get('_repr', _dumprepr)
    res = _repr(val, **kwa)
    res = res.splitlines()
    return res


def _diff_datadiff_data(val1, val2, **kwa):
    """ Do the diff and return the data """
    res = difflib.unified_diff(_diff_pre_diff(val1), _diff_pre_diff(val2))
    return res


def datadiff(val1, val2, **kwa):
    """ Return a values diff string """
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
            data.append(u'...')  # u'…'

    return '\n'.join(data)


def p_datadiff(val1, val2, **kwa):
    """ Print the values diff """
    # TODO: yaml coloring, diff coloring? Using pygments. Example in pyaux.bin.fjson_yaml
    print datadiff(val1, val2, **kwa)
