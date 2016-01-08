# coding: utf8
""" Various methods and helpers for code profiling (especially
LineProfiler)

Example usage of this all:
  * `
    prof.wrap_packages(['mypackage.somemodule'])
    try:
        run_it_all()
    finally:
        prof.profile.dump_stats('some_file.prof')
    `
  * `python -m line_profiler some_file.prof`
  * Bang you head into the output
It is also possible to use `get_prof()` before all other imports and add
 `@profile` wrapper specifically to the target functions, instead of
 using the `wrap_packages`; it is also possible to use `kernprof.py`
 instead of `get_prof` and this whole module.
"""

from __future__ import print_function, unicode_literals, absolute_import, division

import sys
import inspect
import traceback


class DummyProfiler(object):
    """ Dummy LineProfiler-like wrapper """
    def __call__(self, fn, *ar, **kwa):
        return fn  # do nothing as a wrapper
    def __enter__(self):
        return self  # do nothing as a context
    ## Do nothing for other LineProfiler-like functions
    __exit__ = enable = disable = dump_stats = print_stats = lambda self, *ar, **kwa: None


profile = None
profile_type = None


def _check_add_builtin(force=True):
    ## Do the scary global-state stuff
    global profile


def get_prof(proftype='lp', add_builtin=True):
    """ Initialize the global and buitin profiler *wrapper* (currently,
    only meant for LineProfiler) """
    global profile
    global profile_type
    if profile is not None and profile_type == proftype:
        pass  ## ... nothing to generate.
    ## Otherwise - make one.
    elif proftype == 'lp':
        import line_profiler
        profile = line_profiler.LineProfiler()
    elif proftype == 'dummy':
        profile = DummyProfiler()
    else:
        raise Exception("Unknown `proftype`.")
    if add_builtin:  # add/replace/whatever
        from six.moves import builtins
        builtins.__dict__['profile'] = profile
    return profile


def _wrap_class_stuff(the_class, wrapf):
    # for i_name in dir(the_class):
    #     i_val = getattr(the_class, i_name)
    #     if not callable(i_val):
    #         continue
    # # Note: this, still, executes the class properties; hopefully, that
    # #   won't be a problem (they are damn rare after all)
    for i_name, i_val in inspect.getmembers(the_class, predicate=inspect.ismethod):
        try:
            if getattr(i_val, '__prof_wrapped__', False):
                continue  # do not wrap wrapped wrapstuff.
            # XXX: do the sourcefilename check too?
            print("    Method wrapping: %s" % (i_name,))
            wrapped_val = wrapf(i_val)
            setattr(wrapped_val, '__prof_wrapped__', True)
            setattr(the_class, i_name, wrapped_val)
        except Exception as e:
            print("     ... Failed (%r). %r" % (i_name, e))


def _wrap_module_stuff(module, wrapf):
    """ Wrap each function and method in the module with the specified
    function (e.g. LineProfiler) """
    # This should not fail:
    # (Note: there's also `inspect.getfile; but it sometimes returns ...py and sometimes ...pyc)
    if not inspect.ismodule(module) and isinstance(module, object):
        # NOTE: only known to happen with twisted.internet.reactor;
        # along with other problematic twistedness.
        module = type(module)
    module_filename = inspect.getsourcefile(module)
    # ...
    for i_name in dir(module):
        try:
            i_val = getattr(module, i_name)
            if getattr(i_val, '__prof_wrapped__', False):
                continue  # do not wrap wrapped wrapstuff.
            try:
                i_filename = inspect.getsourcefile(i_val)
            except Exception as e:
                i_filename = None
            if i_filename is not None and i_filename != module_filename:
                ## Skip stuff that we know isn't from that module
                continue
            elif i_filename is None:
                ## ... and skip, too, all the built-ins, non-(module/class/function/...)
                continue
            if inspect.isclass(i_val):
                print("  Class wrapping: %s" % (i_name,))
                _wrap_class_stuff(i_val, wrapf=wrapf)
            elif callable(i_val):
                print("  Wrapping: %s" % (i_name,))
                wrapped_val = wrapf(i_val)
                setattr(wrapped_val, '__prof_wrapped__', True)
                setattr(module, i_name, wrapped_val)
        except Exception as e:
            print("  ... Failed (%r). %r" % (i_name, e))


# TODO: make it possible to specify down to particular objects to wrap.
def wrap_packages(packages, wrapf=None, verbose=True):
    """ Wraps all the currently imported modules within any package of
    the `packages` (e.g. `['module1', 'package2', 'package3.module1']`) """
    # Line-profiler: package-wrap.
    # NOTE: this would be more reliable if done on the import hook; but
    #   this is more simple and should be sufficient here.
    if wrapf is None:
        wrapf = get_prof()
    for pkg_name, pkg in sys.modules.items():
        if pkg is None:
            continue
        for pkg_to_wrap in packages:
            if pkg_name.startswith(pkg_to_wrap):
                if verbose:
                    print("Module-wrapping: %s" % (pkg_name,))
                try:
                    _wrap_module_stuff(pkg, wrapf)
                except Exception as exc:
                    print(" ... Failed.", exc)
                break  # make sure not to wrap it many times.
    if verbose:
        print("Wrapping done.")


## TODO?: put into the main prof module
def stgrab(sig, frame):
    """ function that is supposed to be addd as a signal handler
    (e.g. on USR2) and prints the stack trace when called """
    ofra = inspect.getouterframes(frame)
    d = dict(_frame=frame)
    d.update(frame.f_globals)
    d.update(frame.f_locals)
    trace_data = [(v[1], v[2], v[3], ''.join(v[4] or [])) for v in reversed(ofra)]
    trace_formatted = ''.join(traceback.format_list(trace_data))
    trace_last_src = ''.join(ofra[0][4] or [])
    if (stgrab.check_polling
            and any((v in trace_last_src) for v in stgrab.poll_codes)):
        print(" ... Polling ...")  # don't spam that specific traceback
        return
    print(
        " ------- %s\n" % (stgrab.header_str,) +
        # "Framedata: %s\n" % (name, d) +
        "Traceback:\n%s" % (trace_formatted,) +
        "")


## Funny place to put that:
stgrab.header_str = "Stack trace in process:"
stgrab.check_polling = True
## Source code pieces of the known lines that do polling.
## MAYBEDO: add other known polling lines
stgrab.poll_codes = ['   l = self._poller.poll(timeout']
