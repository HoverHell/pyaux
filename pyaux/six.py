# coding: utf8
"""
Some of the things that six says it doesn't provide.
"""

try:
    import urlparse
    from urllib import urlencode
except ImportError:
    import urllib.parse as urlparse
    from urllib.parse import urlencode
