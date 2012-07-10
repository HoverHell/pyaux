# coding: utf8
""" Set the exception handler to additionaly log the exception before
processing it further (e.g. to e-mail it to admins).

Requres `django` module (but does not require django environment)

Prints local variables at each traceback level when possible

Replaces sys.excepthook on import.
Code snippet, to be included in 'sitecustomize.py'
  (or imported from somewhere)
"""


import sys
import logging
_log = logging.getLogger("Unhandled Exception")


def info(exc_type, exc_value, tb):
    _log.exception('')
    # call the default hook
    sys.__excepthook__(exc_type, exc_value, tb)


## Extracts from django.views.debug
## (should not require django settings configured)
from django.template.defaultfilters import pprint  #, force_escape
import re
from lib.auxiliary import edi
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
        except (OSError, IOError):
            pass
    if source is None:
        return None, [], None, []

    encoding = 'ascii'
    for line in source[:2]:
        # File coding may be specified. Match pattern from PEP-263
        # (http://www.python.org/dev/peps/pep-0263/)
        match = re.search(r'coding[:=]\s*([-\w.]+)', line)
        if match:
            encoding = match.group(1)
            break
    source = [unicode(sline, encoding, 'replace') for sline in source]

    lower_bound = max(0, lineno - context_lines)
    upper_bound = lineno + context_lines

    pre_context = [line.strip('\n') for line in source[lower_bound:lineno]]
    context_line = source[lineno].strip('\n')
    post_context = [line.strip('\n') for line in source[lineno+1:upper_bound]]

    return lower_bound, pre_context, context_line, post_context


def get_traceback_frame_variables(tb_frame):
    return tb_frame.f_locals.items()


def get_traceback_frames(tb):
    frames = []
    while tb is not None:
        # Support for __traceback_hide__ which is used by a few libraries
        # to hide internal frames.
        if tb.tb_frame.f_locals.get('__traceback_hide__'):
            tb = tb.tb_next
            continue
        filename = tb.tb_frame.f_code.co_filename
        function = tb.tb_frame.f_code.co_name
        lineno = tb.tb_lineno - 1
        loader = tb.tb_frame.f_globals.get('__loader__')
        module_name = tb.tb_frame.f_globals.get('__name__') or ''
        pre_context_lineno, pre_context, context_line, post_context = _get_lines_from_file(filename, lineno, 7, loader, module_name)
        if pre_context_lineno is not None:
            frames.append({
                'tb': tb,
                #'type': module_name.startswith('django.') and 'django' or 'user',
                'filename': filename,
                'function': function,
                'lineno': lineno + 1,
                'vars': get_traceback_frame_variables(tb.tb_frame),
                'id': id(tb),
                'pre_context': pre_context,
                'context_line': context_line,
                'post_context': post_context,
                'pre_context_lineno': pre_context_lineno + 1,
            })
        tb = tb.tb_next

    return frames


def render_frames_data(frames):
    ## A crappy way to do that compared to templates, but w/e really
    res = ""
    if frames:
        res += "Traceback details:\n"
        for frame in frames:
            #res += ("%(frame['filename'])s:%(frame['lineno'])d:"
            #  " %(frame['function'])r -> %(frame['context_line'])s\n") % edi()
            res += ("---- File %(frame['filename'])s, line %(frame['lineno'])d, in"
              " %(frame['function'])r:\n  > %(frame['context_line'])s\n") % edi()
            # if frame.pre_context: frame.id; for i, line in enumerate(frame.pre_context): frame.pre_context_lineno + i, line
            #if frame.context_line:
            #    res += "  %(frame.lineno): %(frame.context_line)s" % edi()
            #if frame.post_context: for i, line in enumerate(frame.post_context): frame.lineno + 1 + i, line
            if frame['vars']:
                res += "  Local vars:"
                for var in sorted(frame['vars'], key=lambda v: v[0]):
                    res += "  %(var[0])s: %(var[1])s;" % edi()
                res += "\n"
    return res


def advanced_info(exc_type, exc_value, tb):
    #reporter = ExceptionReporter(None, exc_type, exc_value, tb)
    frames = get_traceback_frames(tb)
    for i, frame in enumerate(frames):
        if 'vars' in frame:
            frame['vars'] = [(k,
              #force_escape(pprint(v))
              pprint(v)
              ) for k, v in frame['vars']]
        frames[i] = frame  # XX: does this even do something?

    text = render_frames_data(frames)
    #_log.exception(text)
    _log.error(text)
    #print text
    sys.__excepthook__(exc_type, exc_value, tb)


def advanced_info_safe(exc_type, exc_value, tb):
    """ A paranoid wrapper around handlers; not normally necessary as Python
    handles unhandled exceptions in unhandled exception handlers properly
    """
    try:
        advanced_info(exc_type, exc_value, tb)
    except Exception, e:
        try:
            info(exc_type, exc_value, tb)
        except:
            print "Everything is failing! Running the default excepthook."
            sys.__excepthook__(exc_type, exc_value, tb)
        raise e


#sys.excepthook = info
sys.excepthook = advanced_info  #advanced_info_safe
