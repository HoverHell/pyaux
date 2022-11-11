#!/usr/bin/env python
"""
Module that adds coloring to the `logging` on `init()`.
src: http://stackoverflow.com/questions/384076/how-can-i-color-python-logging-output/1336640#1336640

TODO: make a handler/formatter with this instead.
"""
from __future__ import annotations

import logging

MS_FOREGROUND_BLUE = 0x0001  # text color contains blue.
MS_FOREGROUND_GREEN = 0x0002  # text color contains green.
MS_FOREGROUND_RED = 0x0004  # text color contains red.
MS_FOREGROUND_INTENSITY = 0x0008  # text color is intensified.
MS_FOREGROUND_WHITE = MS_FOREGROUND_BLUE | MS_FOREGROUND_GREEN | MS_FOREGROUND_RED
# winbase.h
MS_STD_INPUT_HANDLE = -10
MS_STD_OUTPUT_HANDLE = -11
MS_STD_ERROR_HANDLE = -12

# wincon.h
MS_FOREGROUND_BLACK = 0x0000
MS_FOREGROUND_CYAN = 0x0003
MS_FOREGROUND_MAGENTA = 0x0005
MS_FOREGROUND_YELLOW = 0x0006
MS_FOREGROUND_GREY = 0x0007
MS_FOREGROUND_INTENSITY = 0x0008  # foreground color is intensified.

MS_BACKGROUND_BLACK = 0x0000
MS_BACKGROUND_BLUE = 0x0010
MS_BACKGROUND_GREEN = 0x0020
MS_BACKGROUND_CYAN = 0x0030
MS_BACKGROUND_RED = 0x0040
MS_BACKGROUND_MAGENTA = 0x0050
MS_BACKGROUND_YELLOW = 0x0060
MS_BACKGROUND_GREY = 0x0070
MS_BACKGROUND_INTENSITY = 0x0080  # background color is intensified.


def add_coloring_to_emit_windows(fn):
    # add methods we need to the class
    def _set_color(self, code):
        import ctypes

        # Constants from the Windows API
        self.STD_OUTPUT_HANDLE = -11
        hdl = ctypes.windll.kernel32.GetStdHandle(self.STD_OUTPUT_HANDLE)
        ctypes.windll.kernel32.SetConsoleTextAttribute(hdl, code)

    setattr(logging.StreamHandler, "_set_color", _set_color)

    def new(*args):
        levelno = args[1].levelno
        if levelno >= 50:
            color = (
                MS_BACKGROUND_YELLOW
                | MS_FOREGROUND_RED
                | MS_FOREGROUND_INTENSITY
                | MS_BACKGROUND_INTENSITY
            )
        elif levelno >= 40:
            color = MS_FOREGROUND_RED | MS_FOREGROUND_INTENSITY
        elif levelno >= 30:
            color = MS_FOREGROUND_YELLOW | MS_FOREGROUND_INTENSITY
        elif levelno >= 20:
            color = MS_FOREGROUND_GREEN
        elif levelno >= 10:
            color = MS_FOREGROUND_MAGENTA
        else:
            color = MS_FOREGROUND_WHITE
        args[0]._set_color(color)

        ret = fn(*args)
        args[0]._set_color(MS_FOREGROUND_WHITE)
        # print "after"
        return ret

    return new


def add_coloring_to_emit_ansi(fn):

    # add methods we need to the class
    def new(*args):
        record = args[1]
        levelno = record.levelno
        nocolor = "\x1b[0m"
        if levelno >= 50:
            color = "\x1b[31m"  # red
        elif levelno >= 40:
            color = "\x1b[31m"  # red
        elif levelno >= 30:
            color = "\x1b[33m"  # yellow
        elif levelno >= 20:
            color = "\x1b[32m"  # green
        elif levelno == 11:  # (useful for tmp-debug-messages)
            color = "\x1b[36m"  # cyan
        elif levelno >= 10:
            color = "\x1b[35m"  # pink
        else:
            color = nocolor  # normal
        record.msg = f"{color}{record.msg}{nocolor}"
        record.levelname = f"{color}{record.levelname}{nocolor}"
        # TODO?: color msg.name with hashfunc-color of `name` or `module`?
        return fn(*args)

    return new


def init():
    """Monkey-patch to add color support to logging.StreamHandler"""
    import platform

    if platform.system() == "Windows":
        # Windows does not support ANSI escapes and we are using API calls
        # to set the console color
        logging.StreamHandler.emit = add_coloring_to_emit_windows(logging.StreamHandler.emit)
    else:
        # all non-Windows platforms are supporting ANSI escapes so we use them
        logging.StreamHandler.emit = add_coloring_to_emit_ansi(logging.StreamHandler.emit)
        # log = logging.getLogger()
        # log.addFilter(log_filter())
        # //hdlr = logging.StreamHandler()
        # //hdlr.setFormatter(formatter())


def test():
    """Provide a simple test-demonstration"""
    logging.basicConfig(level=logging.DEBUG)
    logging.debug("debug")
    logging.warning("a warning")
    logging.error("some error")
    logging.info("some info")


if __name__ == "__main__":
    test()
