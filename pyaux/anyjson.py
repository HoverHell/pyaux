# coding: utf8
"""
Simple `get whatever json`.

See also:
https://bitbucket.org/runeh/anyjson/src/default/anyjson/__init__.py
"""

from __future__ import division, absolute_import, print_function, unicode_literals

try:
    import anyjson
    # Implementation that might be faster but does not provide any extra arguments.
    json_loads_simple = anyjson.loads  # pylint: disable=invalid-name
    json_dumps_simple = anyjson.dumps  # pylint: disable=invalid-name
except Exception:  # pylint: disable=broad-except
    pass

try:
    import simplejson as json
except Exception:  # pylint: disable=broad-except
    import json


# Implementation that at least supports `ensure_ascii=False`.
json_loads = json.loads  # pylint: disable=invalid-name
json_dumps = json.dumps  # pylint: disable=invalid-name
