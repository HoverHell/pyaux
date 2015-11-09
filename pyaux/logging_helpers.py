# coding: utf8

import time
import logging
from logging import handlers


__all__ = (
    'LoggingHandlerTDMixin',
    'LoggingStreamHandlerTD',
    'TaggedSysLogHandler',
)


class LoggingHandlerTDMixin(object):
    """ A logging handler mixin that adds 'time_diff' to the record
    (time since the last message from that handler).

    It is recommended to add it as the first mixin (for timing
    precision). """

    def __init__(self, *ar, **kwa):
        super(LoggingHandlerTDMixin, self).__init__(*ar, **kwa)
        self.last_ts = time.time()

    def emit(self, record):
        now = time.time()
        prev = self.last_ts
        record.time_diff = (now - prev)
        self.last_ts = now
        return super(LoggingHandlerTDMixin, self).emit(record)


class LoggingStreamHandlerTD(LoggingHandlerTDMixin, logging.StreamHandler):
    """ StreamHandler-based LoggingStreamHandlerTDMixin """


class TaggedSysLogHandler(handlers.SysLogHandler):
    """ A version of SysLogHandler that adds a tag to the logged line
    so that it can be sorted by the syslog daemon into files.

    Generally equivalent to using a formatter but semantically more
    similar to FileHandler's `filename` parameter.

    Example rsyslog config:
    In `/etc/rsyslog.d/01-message-size.conf`:
    # WARN: global setting.
    $MaxMessageSize 256k

    In `/etc/rsyslog.d/11-some-app.conf`:
    # WARN: global setting.
    $EscapeControlCharactersOnReceive off
    $FileCreateMode 0644
    $template PlainFormat,"%msg:2:$%\n"
    # # tag -> file mappings.
    :syslogtag, isequal, "some_log:" /var/log/some_app/some_log.log;PlainFormat
    # NOTE: ampersand-tilde tells rsyslog to drop the lines that passed the last filter line; i.e. kind-of 'propagate=False'
    & ~

    :syslogtag, isequal, "some_other_log:" /var/log/some_app/some_other_log.log;PlainFormat
    & ~

    # Return the setting back, supposedly.
    $FileCreateMode 0640
    """

    def __init__(self, *args, **kwargs):
        self.syslog_tag = kwargs.pop('syslog_tag', 'unknown:')
        super(TaggedSysLogHandler, self).__init__(*args, **kwargs)

    def format(self, *args, **kwargs):
        res = super(TaggedSysLogHandler, self).format(*args, **kwargs)
        return self.syslog_tag + " " + res
