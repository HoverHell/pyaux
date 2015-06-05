#!/bin/sh
#######
## Script to run all the known used testing for this library
#######

# python -m doctest pyaux/dicts.py pyaux/base.py pyaux/interpolate.py pyaux/ranges.py "$@"
py.test --doctest-modules "$@"
