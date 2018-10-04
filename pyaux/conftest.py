
import sys

def pytest_ignore_collect(path, config):
    if sys.version_info < (3, 5):
        if path.fnmatch('*/pyaux/aio.py'):
            return True
