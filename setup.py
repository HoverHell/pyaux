#!/usr/bin/env python

version = '1.3'

LONG_DESCRIPTION = """
Collection of helpers and useful things for Python
"""  ## TODO: describe. everything.
## XX: automatically use contents of the 'README.md' instead?

#from distutils.core import setup
from setuptools import setup, find_packages

setup(
  name='pyaux',
  version=version,
  description='pyaux',  ## XX
  long_description=LONG_DESCRIPTION,
  #classifiers=[],
  #keywords='...,...',
  author='HoverHell',
  author_email='hoverhell@gmail.com',
  url='https://github.com/HoverHell/pyaux',
  packages=['pyaux'],  #find_packages(),
  entry_points={
      'console_scripts': [
          'lzcat.py = pyaux.lzcat:_lzcat_main',
          'lzma.py = pyaux.lzmah:_lzma_main',
          'fjson_yaml = pyaux.bin.fjson_yaml:main',
      ],
  },
  install_requires=['ipdb',],
  extras_require={
      ## Things that are useful to simply have around:
      'recommended': [
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
