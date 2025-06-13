"""madstuff: datadiff stuff"""

from __future__ import annotations

import difflib
import itertools
import re
import sys

from ..base import colorize_diff, colorize_yaml

__all__ = (
    "_diff_datadiff_data",
    "_diff_pre_diff",
    "_dumprepr",
    "datadiff",
    "p_datadiff",
)


def _dumprepr(
    val,
    *,
    no_anchors=True,
    colorize=False,
    try_ujson=True,
    allow_unsorted_dicts=False,
    **kwa,
):
    """Advanced-ish representation of an object (using YAML)"""
    import yaml

    dumper: type[yaml.emitter.Emitter] = yaml.Dumper

    # NOTE: this means it'll except on infinitely-recursive data.
    if no_anchors:
        dumper = type("NoAliasesDumper", (dumper,), dict(ignore_aliases=lambda *args, **kwargs: True))

    params = dict(
        # Convenient upper-level kwarg for the most often overridden thing:
        default_flow_style=kwa.pop("default_flow_style", False),
        allow_unicode=True,
        encoding=None,  # return text
        Dumper=dumper,
        sort_keys=not allow_unsorted_dicts,
    )
    params.update(kwa.get("yaml_kwa", {}))

    def maybe_colorize(text):
        if not colorize:
            return text
        return colorize_yaml(text, **kwa)

    res = ""
    try:
        res += maybe_colorize(yaml.dump(val, **params))
    except Exception as exc:
        if not try_ujson:
            raise
        # ujson can handle many objects somewhat-successfully. But can
        # segfault while doing that.
        import ujson

        res += f"# Unable to serialize directly! ({exc!r})\n"
        prepared_value = ujson.loads(ujson.dumps(val))  # pylint: disable=c-extension-no-member
        res += maybe_colorize(yaml.dump(prepared_value, **params))

    return res


def _diff_pre_diff(val, **kwa):
    """Prepare a value for diff-ing"""
    _repr = kwa.get("_repr", _dumprepr)
    res = _repr(val, **kwa)
    return res.splitlines()


def word_diff_color(val1, val2, add="\x1b[32m", rem="\x1b[31;01m", clear="\x1b[39;49;00m", n=3):
    """Proper-ish word-diff represented by colors"""

    def _preprocess(val):
        return re.split(r"(?u)(\w+)", val)

    diffs = list(difflib.unified_diff(_preprocess(val1), _preprocess(val2), n=n))

    def _postprocess(line):
        if line in ("--- \n", "+++ \n"):
            return ""
        if line.startswith("+"):
            color = add
        elif line.startswith("-"):
            color = rem
        else:
            color = ""
        return f"{color}{line[1:]}{clear}"

    diffs_colored = (_postprocess(line) for line in diffs)
    # return diffs_colored
    sys.stdout.write("".join(diffs_colored))
    sys.stdout.write("\n")


def _diff_datadiff_data(val1, val2, n=3, **kwa):
    """Do the diff and return the data"""
    val1_p = _diff_pre_diff(val1, **kwa)
    val2_p = _diff_pre_diff(val2, **kwa)
    return difflib.unified_diff(val1_p, val2_p, n=n)


def datadiff(val1, val2, *, colorize=False, colorize_as_yaml=False, **kwargs):
    """Return a values diff string"""
    kwargs["colorize"] = colorize_as_yaml  # NOTE: controversial
    data = _diff_datadiff_data(val1, val2, **kwargs)

    # line_limit
    _ll = kwargs.pop("line_limit", 200)
    if _ll:
        data_base = data
        data = list(itertools.islice(data_base, _ll))
        try:
            next(data_base)
        except StopIteration:
            pass
        else:
            data.append("...")  # u'…'

    res = "\n".join(data)
    if colorize:
        res = colorize_diff(res, **kwargs)
    return res


def p_datadiff(val1, val2, **kwargs):
    """Print the values diff"""
    # TODO: yaml coloring *and* diff coloring?
    sys.stdout.write(datadiff(val1, val2, **kwargs))
    sys.stdout.write("\n")
