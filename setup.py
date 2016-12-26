#!/usr/bin/env python

from __future__ import print_function, unicode_literals, absolute_import, division

import os
from setuptools import setup, find_packages

version = '1.13.0'  # should be the same as pyaux.__version__

LONG_DESCRIPTION = """
Collection of helpers and useful things for Python

"""

try:
    LONG_DESCRIPTION = (
        LONG_DESCRIPTION +
        open(os.path.join(os.path.dirname(__file__), 'README.rst'), 'rb').read().decode('utf-8'))
except Exception as _exc:
    print("Pkg-description error:", _exc)


setup_kwargs = dict(
    name='pyaux',
    version=version,
    description='pyaux',  ## XX
    long_description=LONG_DESCRIPTION,
    # classifiers=[],
    # keywords='...,...',
    author='HoverHell',
    author_email='hoverhell@gmail.com',
    url='https://github.com/HoverHell/pyaux',
    download_url='https://github.com/HoverHell/pyaux/tarball/%s' % (version,),
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'pylzcat = pyaux.lzcat:_lzcat_main',
            'pyunlzma = pyaux.lzcat:_lzcat_main',
            # NOTE: cannot name it 'lzma.py' as it will get imported
            # and break py3's zipfile
            'pylzma = pyaux.lzmah:_lzma_main',
            # And naming it 'pylzma' is confusing too, so provide a
            # preferred alias.
            'pyenlzma = pyaux.lzmah:_lzma_main',
            'fjson_yaml = pyaux.bin.fjson_yaml:main',
            'fyaml_json = pyaux.bin.fyaml_json:main',
            'fjson.py = pyaux.bin.fjson:main',
            'fmsgp_json = pyaux.bin.fmsgp_json:main',
        ],
    },
    install_requires=['six'],
    extras_require={
        # Things that are useful to simply have around:
        'recommended': [
            'ipython', 'ipdb', 'PyYAML',
            'atomicfile', 'cdecimal',
            # 'requests', 'pycurl',
        ],
        # All things that are known to be used in some part of this
        # library or another.
        'known': [
            'django',  # in the psql helper
            'Twisted',  # bunch of twisted stuff here
            'Cython',  # at least one pyx module
            'pandas',  # here and there
            'Pygments',  # json / yaml coloring
            'pylzma',  # helpers for it
            'simplejson',  # optional, for speed
            # 'pp',  # so special I won't even include it here
            'line_profiler',
            # 'pyzmq',  # also too rare
        ],
    },
    dependency_links=[
        # 'https://github.com/sashka/atomicfile/tarball/master#egg=atomicfile',  # on pypi now
    ],
    # package_data={},
    # include_package_data=True,
    # zip_safe=False,
)


if __name__ == '__main__':
    setup(**setup_kwargs)
