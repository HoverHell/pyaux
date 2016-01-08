#!/usr/bin/env python
# coding: utf8

# This is a simple port-forward / proxy, written using only the default python
# library. If you want to make a suggestion or fix something you can contact-me
# at voorloop_at_gmail.com
# Distributed over IDC(I Don't Care) license

import socket
import select
import time
import sys
import datetime
import logging
import unicodedata

_datefmt = '%Y-%m-%d %H:%M:%S.%f'
_logfmt = "[%(asctime)s] %(message)s"
_msgfmt = "%(meta)15s %(dir)s %(data)s"
_log = logging.getLogger(__name__)
_splitlines = False
_maxlength = 16384


def _out(s):
    _log.info(s)
    sys.stderr.flush()


def _aout(msg):
    _out(msg)


def _addr_repr(meta):
    if isinstance(meta, (list, tuple)):
        return ':'.join(str(v) for v in meta)
    return repr(meta)


def need_repr(string):
    """ Figure out whether the `string` is safe to print or needs some
    repr()ing """
    if isinstance(string, bytes):
        try:
            string = string.decode('utf-8')
        except UnicodeDecodeError:
            return True

    if any(unicodedata.category(ch)[0] == "C" for ch in string):
        return True

    if "'''" in string or '"""' in string:  ## Okay, make it python-ier
        return True

    return False


class Forward(object):
    def __init__(self):
        self.forwardsck = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def start(self, host, port):
        try:
            self.forwardsck.connect((host, port))
            return self.forwardsck
        except Exception as exc:
            _out(repr(exc))
            return False

class TheServer(object):

    _last_data = None

    def __init__(self, host, port, fwdhost, fwdport, buffer_size=4096, delay=0.0001):
        self.input_list = []
        self.channel = {}
        self.meta = {}
        self.forwardscks = set()

        self.fwdparams = (fwdhost, fwdport)
        self.buffer_size = buffer_size
        self.delay = delay

        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((host, port))
        self.server.listen(200)

    def main_loop(self):
        self.input_list.append(self.server)
        _log.debug("Starting the eventloop")
        while 1:
            time.sleep(self.delay)  ## XXXXX: should not be needed, really.
            ss = select.select
            inputready, outputready, exceptready = ss(self.input_list, [], [])
            for sck in inputready:
                if sck == self.server:
                    self.on_accept()
                    break

                try:
                    data = sck.recv(self.buffer_size)
                except Exception as exc:
                    _log.exception("...")
                    continue

                self._last_data = data
                if len(data) == 0:
                    self.on_close(sck)
                else:
                    self.on_recv(sck, data)

    def on_accept(self):
        forward = Forward().start(*self.fwdparams)
        clientsock, clientaddr = self.server.accept()
        if forward:
            _out("%s has connected" % (_addr_repr(clientaddr),))
            self.input_list.append(clientsock)
            self.input_list.append(forward)
            self.forwardscks.add(forward)
            self.channel[clientsock] = forward
            self.channel[forward] = clientsock
            self.meta[clientsock] = clientaddr
            self.meta[forward] = clientaddr
        else:
            _out((
                "Can't establish connection with remote server; "
                "Closing connection with client side %r") % (_addr_repr(clientaddr),))
            clientsock.close()

    def on_close(self, sck):
        meta = self.meta.pop(sck, None)
        _out("%s has disconnected" % _addr_repr(meta))
        #remove objects from input_list
        self.input_list.remove(sck)
        self.input_list.remove(self.channel[sck])
        out = self.channel[sck]
        # close the connection with client
        self.channel[out].close()  # equivalent to do sck.close()
        # close the connection with remote server
        self.channel[sck].close()
        # delete both objects from channel dict
        del self.channel[out]
        del self.channel[sck]

    def on_recv(self, sck, data):
        # here we can parse and/or modify the data before send forward
        _dir = " <<" if sck in self.forwardscks else ">> "
        meta = self.meta.get(sck, '?')
        if meta != '?':
            meta = _addr_repr(meta)

        if _splitlines:
            ## per-line annotation of msg
            lines_are_unfinished = (not data or data[-1] != '\n')
            #lines = data.splitlines()
            lines = data.split('\n')
            if lines_are_unfinished and lines[-1] == '':
                lines = lines[:-1]
            for idx, line in enumerate(lines):

                ## NOTE: length is limited by the bytes length, not the unicode or repr length
                too_long = False
                if len(line) > _maxlength:
                    too_long = True
                    line = line[:_maxlength]

                if need_repr(line):
                    if too_long:
                        msg_data = repr(line) + '…'
                    else:
                        msg_data = repr(line + '\n')  ## ... after putting the newline back
                else:
                    msg_data = " " + line  ## Unambiguate with the space

                if idx == len(lines) - 1:
                    if lines_are_unfinished:
                        ## TODO?: color for unambiguity
                        # msg_data = msg_data + '\\'
                        ## Actually, too non-nice, and "virtual empty string
                        ##   at the end" is unambiguously printed anyway
                        pass

                msg = _msgfmt % dict(dir=_dir, meta=meta, data=msg_data)
                _out(msg)

        else:

            ## NOTE: length is limited by the base bytes length, not the repr length
            if len(data) > _maxlength:
                msg_data = repr(data[:_maxlength]) + '…'
            else:
                msg_data = repr(data)

            msg = _msgfmt % dict(dir=_dir, meta=meta, data=msg_data)
            _out(msg)

        self.channel[sck].send(data)


def main():
    # TODO: argparse
    bind_addr, bind_port, fwd_addr, fwd_port = sys.argv[1], int(sys.argv[2]), sys.argv[3], int(sys.argv[4])

    # ###
    # logging config
    # ###
    try:
        from pyaux import runlib
        runlib.init_logging(level=1)
    except Exception as _exc:
        pass

    # Make a nicer datetime:

    class DTSFormatter(logging.Formatter, object):

        converter = datetime.datetime.fromtimestamp

        def formatTime(self, record, datefmt=None):
            def _proc(ct):
                if _datefmt:
                    return ct.strftime(_datefmt)
                return "%s.%03d" % (ct.strftime("%Y-%m-%dT%H:%M:%S"), record.msecs)

            res = _proc(self.converter(record.created))
            return res

    logging.basicConfig(level=1)
    logging.root.handlers[0].setFormatter(DTSFormatter(_logfmt))
    server = TheServer(bind_addr, bind_port, fwd_addr, fwd_port)
    try:
        server.main_loop()
    except KeyboardInterrupt:
        print("Ctrl C - Stopping server")
        sys.exit(1)


if __name__ == '__main__':
    main()
