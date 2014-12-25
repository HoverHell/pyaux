pyaux
=====

Personal collection of helpers and often-useful snippets for Python

Install the latest version with
`pip install -U -e "git+https://github.com/HoverHell/pyaux.git#egg=pyaux"`


Contains:

* **bubble**: syntactic sugar for super(...)
* **window**: iterator over a 'window' of N adjacent elements
* **SmartDict**: attr→item dict subclass (e.g. for `d.key` instead of
  `d['key']`)
* **DebugPlug**: recursive duck-object for debug and testing
  purposes
* **repr_call**: convenient syntactically-appropriate representation of
  call arguments (also used in DebugPlug)
* **fxrange**, **frange**, **dxrange**, **drange**: `xrange()` / `range()`
  equivalents for float (without error accumulation) and Decimal
* **dict_fget**, **dict_fsetdefault**: versions of `dict.get` and
  `dict.setdefault` with lazy-computation of the default value
* **interp**, **edi**: two versions (simplified and format-supporting) of
  convenient string interpolation (or simplified templating)
* **split_list**: simple one-pass splitting of list into two by a condition
* **use_cdecimal**: forced instance-wide use (by monkey-hack) of `cdecimal`
  instead of `decimal` (for performance)
* **use_exc_ipdb**: set unhandled exception handler to run `ipdb.pm()`
* **use_exc_log**: set unhandled exception handler to log (by `logging`) the
  exception and the stack trace including (when possible) the local
  variables.
* **use_colorer**: monkey-patch `logging` for colored logging
* **obj2dict**: recursive converter of tree-structure of classes into a
  tree-structure of dicts, e.g. for pretty-printing the result
* **mk_logging_property**: make a property that debug-logs the value and
  caller info when set
* Some other things that are too minor to be listed here.

Also, in separate submodules:

* **psql**: helpers for saving Django ORM objects into an SQL 'COPY'-like
  file and loading it in one SQL command (for high-performance loading of
  large amounts of data into the database)
* **lzmah**: lzma compress (as function and as an executable file); also
  provides a function `unjsllzma` to stream-read (json) lines from a
  pylzma-compressed file
* **lzcat**: lzcat for pylzma-specific format (as function and as an
  executale file)
* **runlib**: various things for runscripts:

  * **init_logging**: logging.basicConfig with useful defaults (for
    development runscripts).
  * **sigeventer**: list-based signal handler for SIGINT and SIGTERM (for
    appending handler functions, similarly to `atexit`)
  * **make_manhole**: init a Twisted SSH manhole with set up locals,
    key-based auth, etc.

* **twisted_aux**: use_exc_log-equivalent for twisted (and a helper to
  remove the default logger).
