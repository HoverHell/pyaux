""" Set the exception handler to additionaly log the exception before
processing it further (e.g. to e-mail it to admins).

Logs local variables at each traceback level when possible

Replaces sys.excepthook on `init()`.
Can be included in 'sitecustomize.py'
"""
# # Extracts from django.views.debug
# # (should not require django)
# from django.template.filters import force_escape
from __future__ import annotations

import logging
import re
import reprlib
import sys
import traceback

from pyaux.base import to_text

_log = logging.getLogger("unhandled_exception_handler")

_lrepr_params = dict(
    maxlevel=8,
    maxtuple=64,
    maxlist=64,
    maxarray=48,
    maxdict=64,
    maxset=64,
    maxfrozenset=64,
    maxdeque=64,
    maxstring=80,
    maxlong=128,
    maxother=32,
)


def make_lrepr():
    lrepr = reprlib.Repr()
    for key, val in _lrepr_params.items():
        setattr(lrepr, key, val)
    return lrepr


# # The singleton:
LREPR = make_lrepr()


def lrepr_call(value):
    return LREPR.repr(value)


def info(exc_type, exc_value, tb):
    _log.exception("")
    # call the default hook
    sys.__excepthook__(exc_type, exc_value, tb)


def _var_repr(v, ll=356):
    try:
        # # not exactly optimized in case of huge datalists
        # r = pformat(v)
        # # not exactly... pretty
        r = lrepr_call(v)
        # # XXX: combine those two somehow?
        # # (also, make it print last value of `list`/`deque`/... always, too)
    except Exception as exc:
        return f"<un`repr()`able variable: {exc!r}>"
    # if len(r) > ll:  # handled by the lrepr, somewhat; `ll` is ignored
    #     return r[:ll-4] + '... '
    return r


def _get_lines_from_file(filename, lineno, context_lines, loader=None, module_name=None):
    """
    Returns context_lines before and after lineno from file.
    Returns (pre_context_lineno, pre_context, context_line, post_context).
    """
    source = None
    if loader is not None and hasattr(loader, "get_source"):
        source = loader.get_source(module_name)
        if source is not None:
            source = source.splitlines()
    if source is None:
        try:
            f = open(filename)
            try:
                source = f.readlines()
            finally:
                f.close()
        except OSError:
            pass
    if source is None:
        return None, [], None, []

    encoding = "ascii"
    for line in source[:2]:
        # File coding may be specified. Match pattern from PEP-263
        # (http://www.python.org/dev/peps/pep-0263/)
        match = re.search(r"coding[:=]\s*([-\w.]+)", line)
        if match:
            encoding = match.group(1)
            break
    source = [to_text(sline, encoding=encoding, errors="replace") for sline in source]

    lower_bound = max(0, lineno - context_lines)
    upper_bound = lineno + context_lines

    pre_context = [line.strip("\n") for line in source[lower_bound:lineno]]
    context_line = source[lineno].strip("\n")
    post_context = [line.strip("\n") for line in source[lineno + 1 : upper_bound]]

    return lower_bound, pre_context, context_line, post_context


def get_traceback_frame_variables(tb_frame):
    return tb_frame.f_locals.items()


def get_traceback_frames(tb):
    frames = []
    while tb is not None:
        # Support for __traceback_hide__ which is used by a few libraries
        # to hide internal frames.
        if tb.tb_frame.f_locals.get("__traceback_hide__"):
            tb = tb.tb_next
            continue
        filename = tb.tb_frame.f_code.co_filename
        function = tb.tb_frame.f_code.co_name
        lineno = tb.tb_lineno - 1
        loader = tb.tb_frame.f_globals.get("__loader__")
        module_name = tb.tb_frame.f_globals.get("__name__") or ""
        (
            pre_context_lineno,
            pre_context,
            context_line,
            post_context,
        ) = _get_lines_from_file(filename, lineno, 7, loader, module_name)
        if pre_context_lineno is not None:
            frames.append(
                {
                    "tb": tb,
                    # 'type': module_name.startswith('django.') and 'django' or 'user',
                    "filename": filename,
                    "function": function,
                    "lineno": lineno + 1,
                    "vars": get_traceback_frame_variables(tb.tb_frame),
                    "id": id(tb),
                    "pre_context": pre_context,
                    "context_line": context_line,
                    "post_context": post_context,
                    "pre_context_lineno": pre_context_lineno + 1,
                }
            )
        tb = tb.tb_next

    return frames


def _exc_safe_repr(exc_type, exc_value):
    """Mildly paranoid extraction of repr of exception"""
    # NOTE: returns a terminating newline. Strip if a problem.
    return "".join(traceback.format_exception_only(exc_type, exc_value))
    # return (
    #  getattr(exc_type, '__module__', '<unknown module>'),
    #  getattr(exc_type, '__name__', '<unnamed exception!?>'),
    #  getattr(exc_value, 'message', '<no message!?>'),
    #  )


def render_exc_repr(exc_type, exc_value):
    """A still paranoid but more detailed exception representator"""
    res = ""
    try:
        res += "Error:  %s" % _exc_safe_repr(exc_type, exc_value)
        try:
            res += f"  (repr: '''{exc_value!r}''')\n"
        except Exception as e:
            try:
                res += f"  (Failure to repr: {e!r})\n"
            except Exception as e2:
                res += "  (Failure to repr totally: ({}) ({})\n".format(
                    _exc_safe_repr(type(e), e).strip(),
                    _exc_safe_repr(type(e2), e2).strip(),
                )
    except Exception as e3:
        try:
            res += ("Error: Some faulty exception of type %r, failing " "on repr with %s") % (
                exc_type,
                _exc_safe_repr(type(e3), e3),
            )
        except Exception:
            res += "Error: Some very faulty exception"
    return res


def render_frames_data(frames, exc_type=None, exc_value=None):
    # A crappy way to do that compared to templates, but w/e really
    res = ""
    if exc_type or exc_value:
        # Also convenient:
        res += _exc_safe_repr(exc_type, exc_value)
    if frames:
        res += "Traceback details:\n"
        for frame in frames:
            res += (
                f"---- File {frame['filename']}, line {frame['lineno']}, in"
                f" {frame['function']}:\n  > {frame['context_line']}\n"
            )
            if frame["vars"]:
                res += "  Local vars:"
                for var in sorted(frame["vars"], key=lambda v: v[0]):
                    # Note: 13 spaces to visually separate the
                    #   variables at the same time taking less vertical
                    #   space than printing each from a new line (and
                    #   then adding spaces anyway).
                    res += " " * 13
                    res += f"{var[0]}: {var[1]};"
                res += "\n"
    if exc_type or exc_value:
        res += render_exc_repr(exc_type, exc_value)
    return res


def advanced_info(exc_type, exc_value, tb):
    # reporter = ExceptionReporter(None, exc_type, exc_value, tb)
    frames = get_traceback_frames(tb)
    for idx, frame in enumerate(frames):
        if "vars" in frame:
            frame["vars"] = [
                (
                    key,
                    # force_escape(pprint(v))
                    _var_repr(val),
                )
                for key, val in frame["vars"]
            ]
        frames[idx] = frame  # XX: does this even do something?

    text = render_frames_data(frames, exc_type, exc_value)
    # _log.exception(text)
    _log.error(text)
    # print(text)
    sys.__excepthook__(exc_type, exc_value, tb)


def advanced_info_safe(exc_type, exc_value, tb):
    """A paranoid wrapper around handlers; not normally necessary as Python
    handles unhandled exceptions in unhandled exception handlers properly
    """
    try:
        advanced_info(exc_type, exc_value, tb)
    except Exception as e:
        try:
            info(exc_type, exc_value, tb)
        except Exception:
            sys.stderr.write("Everything is failing! Running the default excepthook.\n")
            sys.__excepthook__(exc_type, exc_value, tb)
        raise e


def init():
    # sys.excepthook = info
    sys.excepthook = advanced_info
    # sys.excepthook = advanced_info_safe
