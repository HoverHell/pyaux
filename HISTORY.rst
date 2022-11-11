.. :changelog:

Release History
---------------

3.0.0 (2022-11-11)
++++++++++++++++++

 - Update newrelease for pyproject (more)
 - Update newrelease
 - Minor rename
 - Apply more of
 - Fix some of the linting
 - Apply `autoflake`
 - Apply `pyupgrade --py37-plus`
 - Apply `isort` and `black` after reconfiguration again
 - Apply `isort` and `black`
 - Apply src layout
 - Switch to py3.7+


2.11.0 (2021-03-25)
+++++++++++++++++++

 - skip an unfeasible C-dependency
 - avoid a warning in py3.9


2.10.0 (2020-07-07)
+++++++++++++++++++

 - explicit stdin_bin_lines


2.9.0 (2020-06-07)
++++++++++++++++++

 - exc_log py3 and fixes


2.8.0 (2019-09-24)
++++++++++++++++++

 - req: _cut in the middle, raise the retry failures for proper handling
 - stdout_lines py2 fix
 - Requester.response_exception_cls
 - Requester improvements
 - pyaux.net.gai_verbose
 - Correct the links
 - prefetch_first: correction for empty iterable
 - pyaux.iterables.prefetch_first: Transparent-ish iterable wrapper that obtains the first N items on call.
 - f_convert msgpack input improvements
 - f_convert: generalized serialization formats converter
 - fyaml_json fixes


2.7.0 (2019-03-04)
++++++++++++++++++

 - req.APIRequester fixes
 - pylibnewrelease: push then twine for easier intermittent-error recovery


2.6.0 (2019-03-01)
++++++++++++++++++

 - req: APIRequester: support session=None better
 - iterables: pair_window, cumsum
 - Tests fixes
 - Requester module and various refactorings
 - _yprint: allow keeping the dicts order in py3.7+; minor cleanup and linting
 - pylibnewrelease over twine
 - Url: query MVOD, to_string method
 - sre_tools: minor improvements and additions


2.5.0 (2018-12-09)
++++++++++++++++++

 - sre_tools: find_matching_subregexes (AST-based)
 - nb_highcharts: some improvements
 - dict_is_subset fixed version
 - nb_highcharts: update to use a currently working library; requires python-highcharts now


2.4.1 (2018-11-26)
++++++++++++++++++

 - procs: py2 support fix


2.4.0 (2018-11-26)
++++++++++++++++++

 - _dict_hashable fix
 - procs: minor improvement
 - procs: subprocess helpers: run_cmd, poll_fds
 - Minor changes and cleanups


2.3.1 (2018-10-04)
++++++++++++++++++

 - py3.6 fixes
 - wip: dockered tox


2.3.0 (2018-07-18)
++++++++++++++++++

 - to_str, for use in e.g. type()
 - minor notes
 - stdin_lines, stdout_lines: refactoring and improvements
 - iterables.with_last: py3.7 fix
 - minor style fix
 - yet another py23 fix
 - logging annotators support in the .runlib.init_logging
 - yet another py23 fix
 - WARN: refactor logging annotating filters into a separate module, insta-deprecate the time-diff-supporting logging handlers
 - simple_memoize_argless
 - aio: _await for debugging the asyncs
 - PY_3 and such shortcut-flags
 - yet another py3 fix
 - tests: themattrix/tox docker-based tests


2.2.0 (2017-12-20)
++++++++++++++++++

 - reversed_lines: bytes (non-text) joiner by default
 - _uprint default_flow_style upper-level kwarg support
 - _yprint: py23
 - fmsgp_json: support multiple items


2.1.0 (2017-12-18)
++++++++++++++++++

 - deprecation notice
 - pyaux.dicts.DotOrderedDict fix
 - tox addopts cleanup
 - pyaux.dicts.DotOrderedDict
 - pyaux.dicts.OrderedDict repr mixin fix
 - iterables.with_last annotator


2.0.0 (2017-10-26)
++++++++++++++++++

 - cleanup of the things that were moved out to pyauxm
 - _uprint py3
 - newrelease as a library script


1.15.0 (2017-05-25)
+++++++++++++++++++

 - fixes


1.14.0 (2017-05-25)
+++++++++++++++++++

 - 'tox'ability
 - Reorganization (mostly backwards-compatible)
 - logging formats: enforce 'str' type
 - datadiff: n
 - jupyter python highcharts integration
 - tox tests


1.13.0 (2016-12-26)
+++++++++++++++++++

 - split_dict shorthand
 - mangle_items extensions
 - fyaml_json
 - mangle_items, _memoize_timelimit_override
 - py3 fixes


1.12.0 (2016-09-01)
+++++++++++++++++++

 - configurable_wrapper; memoize_method fix for subclassing
 - MultiValueDict variations, MVLOD
 - MultiValueDict.make_from_items


1.11.0 (2016-08-26)
+++++++++++++++++++

 - MVOD.getlist, MultiValueDict from django
 - wittgendoc callable
 - Minor improvements
 - some fixes
 - sh_quote_prettier
 - get_env_flag shortcut
 - find_files: more options
 - datadiff: minor improvements
 - fjson.py: simple support for filename arg
 - sh_quote backport


1.10.0 (2016-02-19)
+++++++++++++++++++

 - FIX: py3 minor fixes
 - hashabledict_st
 - fjson.py: py3
 - IPNBDFDisplay exclude columns
 - py3 gitignore
 - Improved debug-tcp-proxy
 - py23: future imports
 - more style cleanup
 - py23 single-codebase compat
 - py23 single-codebase support, in process
 - madness: plain-pdb versions of _ipdbg and _ipdbt
 - fjson, fjson_yaml: better failure reporting
 - Colorer: proper string interpolation
 - style of the obsolete stuff


1.9.0 (2015-11-09)
++++++++++++++++++

 - fixes
 - logging_helpers
 - mygrequests
 - urlhelpers
 - exclogwrap, repr_cut, slstrip
 - request requests wrapper


1.8.0 (2015-11-09)
++++++++++++++++++

 - memoized_property
 - Various fixes and improvements
 - More conveniences
 - madness: _re_largest_matching_start
 - madness: _ipdbt, reorganisation
 - FIX: make runlib importable without twisted


1.7.2 (2015-06-15)
++++++++++++++++++

 - fix bin/ formatters
 - fix fjson.py


1.7.1 (2015-06-08)
++++++++++++++++++

 - minor notes
 - fix setup.py packages
 - refactor: style, make_manhole moved to twisted_aux


1.7.0 (2015-06-05)
++++++++++++++++++

 - Lots of things, a bit of module-separation
 - separated out ranges
 - bin: fjson.py, fmsgp_json


1.6.0 (2015-05-29)
++++++++++++++++++

 - dicts: __all__
 - dicts: style
 - p_o_repr builtinable
 - more pep8
 - mrosources, colorize in oneliny
 - mangle_dict, generalised pygments-using colorize


1.5.0 (2015-03-19)
++++++++++++++++++

 - _yprint: print data over colored yaml
 - madness reorganised


1.4.0 (2015-03-18)
++++++++++++++++++

 - WIP _newrelease.py
 - pyaux.base.group
 - WARN: dict_merge: deepcopy the target by default (for safety)
 - license file
 - date ranges


1.3.2 (2015-01-28)
++++++++++++++++++

 - 'dicts' module fixes


1.3.1 (2014-12-25)
++++++++++++++++++

 - Packaging fixes


1.3.0 (2014-12-25)
++++++++++++++++++

 - Initial PyPi release
