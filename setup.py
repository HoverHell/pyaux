#!/usr/bin/env python

try:
    from pyaux import __version__ as version
except Exception as _exc:
    print "Pkg-version error:",_exc
    version = '1.3.1'

import os


LONG_DESCRIPTION = """
Collection of helpers and useful things for Python

"""

try:
    LONG_DESCRIPTION = (
        LONG_DESCRIPTION
        + open(os.path.join(os.path.dirname(__file__), 'README.rst')).read())
except Exception as _exc:
    print "Pkg-description error:", _exc


#from distutils.core import setup
from setuptools import setup, find_packages

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
    packages=['pyaux'],  # find_packages(),
    entry_points={
        'console_scripts': [
            'lzcat.py = pyaux.lzcat:_lzcat_main',
            'lzma.py = pyaux.lzmah:_lzma_main',
            'fjson_yaml = pyaux.bin.fjson_yaml:main',
        ],
    },
    install_requires=[],
    extras_require={
        ## Things that are useful to simply have around:
        'recommended': [
            'ipdb',
            'atomicfile', 'cdecimal', 'ipython', 'django',
            #'requests', 'pycurl',
        ],
    },
    dependency_links=[
       # 'https://github.com/sashka/atomicfile/tarball/master#egg=atomicfile',  # on pypi
    ],
    #package_data={},
    #include_package_data=True,
    #zip_safe=False,
)


if __name__ == '__main__':
    setup(**setup_kwargs)
