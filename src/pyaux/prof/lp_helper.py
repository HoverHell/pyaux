"""
Various methods and helpers for code profiling (especially LineProfiler).

Example usage of this all:

    prof.wrap_packages(['mypackage.somemodule'])
    try:
        run_it_all()
    finally:
        prof.profile.dump_stats('some_file.prof')

`python -m line_profiler some_file.prof`

Bang you head into the output.

It is also possible to use `get_prof()` before all other imports and add
`@profile` wrapper specifically to the target functions, instead of
using the `wrap_packages`; it is also possible to use `kernprof.py`
instead of `get_prof` and this whole module.
"""

from __future__ import annotations

import inspect
import signal
import sys
import traceback
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Collection

__all__ = (
    "get_prof",
    "stgrab",
    "wrap_packages",
)


class DummyProfiler:
    """Dummy LineProfiler-like wrapper"""

    def __call__(self, fn, *ar, **kwa):
        return fn  # do nothing as a wrapper

    def __enter__(self):
        return self  # do nothing as a context

    # Do nothing for other LineProfiler-like functions
    __exit__ = enable = disable = dump_stats = print_stats = lambda self, *ar, **kwa: None


profile: Any = None
profile_type = None


def get_prof(proftype="lp", *, add_builtin_key: str = "profile"):
    """
    Initialize the global and buitin profiler *wrapper* (currently,
    only meant for LineProfiler)
    """
    global profile  # noqa: PLW0603
    global profile_type  # noqa: PLW0603

    if profile is not None and profile_type == proftype:
        pass  # ... nothing to generate.
    # Otherwise - make one.
    elif proftype == "lp":
        import line_profiler

        profile = line_profiler.LineProfiler()
    elif proftype == "dummy":
        profile = DummyProfiler()
    else:
        raise Exception("Unknown `proftype`.")

    if add_builtin_key:  # add/replace/whatever
        setattr(__builtins__, add_builtin_key, profile)

    profile_type = proftype
    return profile


MARKER_ATTR = "__prof_wrapped__"


def _wrap_class_stuff(the_class, wrapf, marker_attr: str = MARKER_ATTR):
    # for i_name in dir(the_class):
    #     i_val = getattr(the_class, i_name)
    #     if not callable(i_val):
    #         continue
    # # Note: this, still, executes the class properties; hopefully, that
    # #   won't be a problem (they are damn rare after all)
    for i_name, i_val in inspect.getmembers(the_class, predicate=inspect.ismethod):
        try:
            if getattr(i_val, "__prof_wrapped__", False):
                continue  # do not wrap wrapped wrapstuff.
            # To consider: do the sourcefilename check too?
            sys.stderr.write(f"    Method wrapping: {i_name}\n")
            wrapped_val = wrapf(i_val)
            setattr(wrapped_val, marker_attr, True)
            setattr(the_class, i_name, wrapped_val)
        except Exception as exc:
            sys.stderr.write(f"     ... Failed ({i_name!r}). {exc!r}\n")


def _wrap_module_stuff(module, wrapf, *, marker_attr: str = MARKER_ATTR):
    """
    Wrap each function and method in the module with the specified
    function (e.g. LineProfiler)
    """
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
            if getattr(i_val, "__prof_wrapped__", False):
                continue  # do not wrap wrapped wrapstuff.
            try:
                i_filename = inspect.getsourcefile(i_val)
            except Exception:
                i_filename = None
            if i_filename is not None and i_filename != module_filename:
                # Skip stuff that we know isn't from that module
                continue
            if i_filename is None:
                # ... and skip, too, all the built-ins, non-(module/class/function/...)
                continue
            if inspect.isclass(i_val):
                sys.stderr.write(f"  Class wrapping: {i_name}\n")
                _wrap_class_stuff(i_val, wrapf=wrapf)
            elif callable(i_val):
                sys.stderr.write(f"  Wrapping: {i_name}\n")
                wrapped_val = wrapf(i_val)
                setattr(wrapped_val, marker_attr, True)
                setattr(module, i_name, wrapped_val)
        except Exception as exc:
            sys.stderr.write(f"  ... Failed ({i_name!r}). {exc!r}\n")


# TODO: make it possible to specify down to particular objects to wrap.
def wrap_packages(packages, wrapf=None, *, verbose=True):
    """
    Wraps all the currently imported modules within any package of
    the `packages` (e.g. `['module1', 'package2', 'package3.module1']`)
    """
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
                    sys.stderr.write(f"Module-wrapping: {pkg_name}\n")
                try:
                    _wrap_module_stuff(pkg, wrapf)
                except Exception as exc:
                    sys.stderr.write(f" ... Failed: {exc!r}.\n")
                break  # make sure not to wrap it many times.
    if verbose:
        sys.stderr.write("Wrapping done.\n")


class StackGrab:
    header: str = "Stack trace in process:"
    check_polling: bool = True
    # Source code pieces of the known lines that do polling.
    # Add other known polling lines as needed.
    poll_codes: Collection[str] = ("   l = self._poller.poll(timeout",)

    def install(self, sig: int = signal.SIGUSR2) -> None:
        signal.signal(sig, self)

    def __call__(self, sig: Any, frame: Any) -> None:
        """
        function that is supposed to be added as a signal handler (e.g. on USR2),
        prints the stack trace when called.
        """
        outer_frames = inspect.getouterframes(frame)
        data = dict(_frame=frame)
        data.update(frame.f_globals)
        data.update(frame.f_locals)
        trace_data = [
            traceback.FrameSummary(frame[1], frame[2], frame[3], line="".join(frame[4] or []))
            for frame in reversed(outer_frames)
        ]
        trace_formatted = "".join(traceback.format_list(trace_data))
        trace_last_code = "".join(outer_frames[0][4] or [])
        if self.check_polling and any((code_text in trace_last_code) for code_text in self.poll_codes):
            sys.stderr.write(" ... Polling ...\n")  # don't spam that specific traceback
            return
        sys.stderr.write(f" ------- {self.header}\nTraceback:\n{trace_formatted}\n")


stgrab = StackGrab  # compat alias
