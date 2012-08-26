#!/usr/bin/env python

version = '1.1'

LONG_DESCRIPTION = """
Collection of helpers and useful things for Python
"""  ## TODO: describe. everything.
## XX: automatically use contents of the 'README.md' instead?

#from distutils.core import setup
from setuptools import setup, find_packages

setup(name='pyaux',
  version=version,
  description='pyaux',  ## XX
  long_description=LONG_DESCRIPTION,
  #classifiers=[],
  #keywords='...,...',
  author='HoverHell',
  author_email='hoverhell@gmail.com',
  url='https://github.com/HoverHell/pyaux',
  packages=find_packages(),
  #package_data={},
  #include_package_data=True,
  #zip_safe=False,
)
