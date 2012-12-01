#!/usr/bin/env python
# coding: utf8

import twisted.python.log as twisted_log
from . import exc_log


class ExcLogObserver(object):
    """ A Twisted Log Observer that uses advanced logging for exceptions """
    ## See twisted.python.log.PythonLoggingObserver for information on what is what
    def emit(self, eventDict):
        if not eventDict['isError']:
            return  # not for us
        #e_t, e_v, e_tb = sys.exc_info()
        ## More correct:
        vf = eventDict['failure']
        e_t, e_v, e_tb = vf.type, vf.value, vf.getTracebackObject()
        #sys.excepthook(e_t, e_v, e_tb)
        exc_log.advanced_info_safe(e_t, e_v, e_tb)
    def start(self):
        twisted_log.addObserver(self.emit)
    def stop(self):
        twisted_log.removeObserver(self.emit)


## A singleton instance for convenience
exc_log_observer = ExcLogObserver()


def del_twisted_default_log():
    """ Remove the default log Observer from twisted handler """
    try:
        twisted_log.defaultObserver.stop()
    except ValueError:  # probably removed already
        pass
