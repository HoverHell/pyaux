# coding: utf8

import time
import logging
from logging import handlers
from .base import to_bytes


__all__ = (
    'TaggedSysLogHandlerBase',
    'TaggedSysLogHandler',
)


class TaggedSysLogHandlerBase(handlers.SysLogHandler):
    """
    A version of SysLogHandler that adds a tag to the logged line
    so that it can be sorted by the syslog daemon into files.

    Generally equivalent to using a formatter but semantically more
    similar to FileHandler's `filename` parameter.

    Example rsyslog config:
    In `/etc/rsyslog.d/01-dynamic-app-logging.conf`:

        # WARN: global settings.
        $MaxMessageSize 2049k
        $EscapeControlCharactersOnReceive off  # In case your logs aren't quite text.
        $RepeatedMsgReduction off
        $SystemLogRateLimitInterval 0
        $SystemLogRateLimitBurst 0
        # File permissions:
        $umask 0000
        $FileOwner syslog
        $DirOwner syslog
        # Makes it possible to set a group on the logging directory to give
        # write access to it.
        $FileCreateMode 0664
        $DirCreateMode 2775
        $CreateDirs on

        $template LogFormatPlain,"%msg:2:$%\n"
        # Make it possible to specify the target filename in the syslog tag.
        # NOTE: The root directory creation has to be done outside syslog, as
        # syslog normally doesn't have access to `mkdir /var/log/something`.
        # NOTE: the '.log' is appended automatically.
        $template LogDynFileAUTO,"/var/log/%syslogtag:R,ERE,1,DFLT:file__([a-zA-Z0-9_/.-]*)--end%.log"
        :syslogtag, regex, "file__[a-zA-Z0-9_/.-]*" ?LogDynFileAUTO;LogFormatPlain

        # NOTE: ampersand-tilde tells rsyslog to drop the lines that passed the
        # last filter line; i.e. kind-of 'propagate=False'
        & ~

    """

    def __init__(self, *args, **kwargs):
        syslog_tag = kwargs.pop('syslog_tag')
        syslog_tag = to_bytes(syslog_tag)
        self.syslog_tag = syslog_tag
        super(TaggedSysLogHandler, self).__init__(*args, **kwargs)

    def format(self, *args, **kwargs):
        res = super(TaggedSysLogHandler, self).format(*args, **kwargs)
        assert isinstance(res, bytes)
        return self.syslog_tag + " " + res


class TaggedSysLogHandler(TaggedSysLogHandlerBase):
    """
    An addition to TaggedSysLogHandlerBase that sets the SO_SNDBUF to a large
    value to allow large log lines.
    """

    _sndbuf_size = 5 * 2**20  # 5 MiB

    def __init__(self, *args, **kwargs):
        self._sbdbuf_size = kwargs.pop('sbdbuf_size', self._sndbuf_size)
        super(TaggedSysLogHandler, self).__init__(*args, **kwargs)
        self.configure_socket(self.socket)

    def configure_socket(self, sock):
        import socket
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, self._sndbuf_size)
