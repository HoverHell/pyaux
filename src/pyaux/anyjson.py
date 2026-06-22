"""
Simple `get whatever json`.

See also:
https://bitbucket.org/runeh/anyjson/src/default/anyjson/__init__.py
"""

from __future__ import annotations

try:
    import anyjson

    # Implementation that might be faster but does not provide any extra arguments.
    json_loads_simple = anyjson.loads
    json_dumps_simple = anyjson.dumps
except Exception:
    pass

try:
    import simplejson as json
except Exception:
    import json  # type: ignore[no-redef]


# Implementation that at least supports `ensure_ascii=False`.
json_loads = json.loads
json_dumps = json.dumps
