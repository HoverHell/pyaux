# coding: utf8
""" Various modules for use in older python versions which don't have them natively yet """

import re

# Py3.3's shlex.quote piece backport

_sh_find_unsafe = re.compile(r'[^\w@%+=:,./-]').search


def sh_quote(s):
    if not s:
        return "''"
    if _sh_find_unsafe(s) is None:
        return s

    # use single quotes, and put single quotes into double quotes
    # the string $'b is then quoted as '$'"'"'b'
    return "'" + s.replace("'", "'\"'\"'") + "'"
