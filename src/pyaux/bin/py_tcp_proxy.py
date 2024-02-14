#!/usr/bin/env python

# This is a simple port-forward / proxy, written using only the default python
# library. If you want to make a suggestion or fix something you can contact-me
# at voorloop_at_gmail.com
# Distributed over IDC(I Don't Care) license

from __future__ import annotations

import datetime
import logging
import os
import select
import socket
import ssl
import sys
import time
import unicodedata
from typing import Any

DATEFMT = "%Y-%m-%d %H:%M:%S.%f"
LOGFMT = "[%(asctime)s] %(message)s"
MSGFMT = "{meta:15s} {dir} {data}"  # noqa: FS003
LOGGER = logging.getLogger(__name__)
SPLITLINES = False
MAXLENGTH = 16384
TAddress = Any


def _out(message: str) -> None:
    LOGGER.info(message)
    sys.stderr.flush()


def _addr_repr(meta: TAddress) -> str:
    if isinstance(meta, (list, tuple)):
        return ":".join(str(item) for item in meta)
    return repr(meta)


def need_repr(string: Any) -> bool:
    """Figure out whether the `string` is safe to print or needs some
    repr()ing"""
    if isinstance(string, bytes):
        try:
            string = string.decode("utf-8")
        except UnicodeDecodeError:
            return True

    if any(unicodedata.category(ch)[0] == "C" for ch in string):
        return True

    if "'''" in string or '"""' in string:  # Okay, make it python-ier
        return True

    return False


class Forward:
    def __init__(self) -> None:
        self.forwardsck: socket.socket | None = None

    def start(
        self, host: str, port: int, ip6: bool = False, ssl_connect: bool = False
    ) -> socket.socket | None:
        self.forwardsck = socket.socket(
            socket.AF_INET6 if ip6 else socket.AF_INET, socket.SOCK_STREAM
        )
        if ssl_connect:
            self.forwardsck = ssl.wrap_socket(self.forwardsck)
        try:
            self.forwardsck.connect((host, port))
            return self.forwardsck
        except Exception as exc:
            _out(repr(exc))
            logging.exception("Forward error: %r", exc)
            return None


class TheServer:
    _last_data = None

    def __init__(
        self,
        host: str,
        port: int,
        fwdhost: str,
        fwdport: int,
        buffer_size: int = 4096,
        delay: float = 0.0001,
        ip6_listen: bool = False,
        ip6_connect: bool = False,
        ssl_connect: bool = False,
    ) -> None:
        self.input_list: list[socket.socket] = []  # selectables
        self.channel: dict[socket.socket, socket.socket] = {}
        self.meta: dict[socket.socket, TAddress] = {}
        self.forwardscks: set[socket.socket] = set()

        self.fwdparams = (fwdhost, fwdport, ip6_connect, ssl_connect)
        self.buffer_size = buffer_size
        self.delay = delay

        self.server = socket.socket(
            socket.AF_INET6 if ip6_listen else socket.AF_INET, socket.SOCK_STREAM
        )
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((host, port))
        self.server.listen(200)

    def main_loop(self) -> None:
        self.input_list.append(self.server)
        LOGGER.debug("Starting the eventloop")
        while 1:
            time.sleep(self.delay)  # XXXXX: should not be needed, really.
            inputready, outputready, exceptready = select.select(self.input_list, [], [])
            for sck in inputready:
                if sck == self.server:
                    self.on_accept()
                    break

                try:
                    data = sck.recv(self.buffer_size)
                except Exception:
                    LOGGER.exception("...")
                    continue

                self._last_data = data
                if len(data) == 0:
                    self.on_close(sck)
                else:
                    self.on_recv(sck, data)

    def on_accept(self) -> None:
        forward = Forward().start(*self.fwdparams)
        clientsock, clientaddr = self.server.accept()
        if forward is not None:
            _out(f"{_addr_repr(clientaddr)} has connected")
            self.input_list.append(clientsock)
            self.input_list.append(forward)
            self.forwardscks.add(forward)
            self.channel[clientsock] = forward
            self.channel[forward] = clientsock
            self.meta[clientsock] = clientaddr
            self.meta[forward] = clientaddr
        else:
            _out(
                (
                    "Can't establish connection with remote server; "
                    "Closing connection with client side %r"
                )
                % (_addr_repr(clientaddr),)
            )
            clientsock.close()

    def on_close(self, sck: socket.socket) -> None:
        meta = self.meta.pop(sck, None)
        _out(f"{_addr_repr(meta)} has disconnected")
        # remove objects from input_list
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

    def on_recv(self, sck: socket.socket, data: bytes) -> None:
        # here we can parse and/or modify the data before send forward
        _dir = " <<" if sck in self.forwardscks else ">> "
        meta = self.meta.get(sck, "?")
        if meta != "?":
            meta = _addr_repr(meta)

        if SPLITLINES:
            # per-line annotation of msg
            lines_are_unfinished = not data or data[-1:] != "\n"
            # lines = data.splitlines()
            lines = data.split(b"\n")
            if lines_are_unfinished and lines[-1] == b"":
                lines = lines[:-1]
            for idx, line in enumerate(lines):
                # NOTE: length is limited by the bytes length, not the unicode or repr length
                too_long = False
                if len(line) > MAXLENGTH:
                    too_long = True
                    line = line[:MAXLENGTH]

                if need_repr(line):
                    if too_long:
                        msg_data = repr(line) + "…"
                    else:
                        msg_data = repr(line + b"\n")  # ... after putting the newline back
                else:
                    msg_data = " " + line.decode("utf-8")  # Unambiguate with the space

                if idx == len(lines) - 1:
                    if lines_are_unfinished:
                        # # TODO?: color for unambiguity
                        # msg_data = msg_data + '\\'
                        # # Actually, too non-nice, and "virtual empty string
                        # #   at the end" is unambiguously printed anyway
                        pass

        else:
            # NOTE: length is limited by the base bytes length, not the repr length
            if len(data) > MAXLENGTH:
                msg_data = repr(data[:MAXLENGTH]) + "…"
            else:
                msg_data = repr(data)

        msg = MSGFMT.format(dir=_dir, meta=meta, data=msg_data)
        _out(msg)

        self.channel[sck].send(data)


class DTSFormatter(logging.Formatter):
    def formatTime(
        self,
        record: logging.LogRecord,
        datefmt: str | None = DATEFMT,
    ) -> str:
        dt_val = datetime.datetime.fromtimestamp(record.created)
        if datefmt:
            return dt_val.strftime(datefmt)
        dt_s = dt_val.strftime("%Y-%m-%dT%H:%M:%S")
        return f"{dt_s}.{record.msecs:03d}"


def main() -> None:
    # TODO: argparse
    bind_addr, bind_port, fwd_addr, fwd_port = (
        sys.argv[1],
        int(sys.argv[2]),
        sys.argv[3],
        int(sys.argv[4]),
    )
    ip6_listen = bool(os.environ.get("IP6_LISTEN"))
    ip6_connect = bool(os.environ.get("IP6_CONNECT"))
    ssl_connect = bool(os.environ.get("SSL_CONNECT"))

    # ###
    # logging config
    # ###
    try:
        from pyaux import runlib

        runlib.init_logging(level=1)
    except Exception:
        pass

    # Make a nicer datetime:

    logging.basicConfig(level=1)
    logging.root.handlers[0].setFormatter(DTSFormatter(LOGFMT))
    server = TheServer(
        bind_addr,
        bind_port,
        fwd_addr,
        fwd_port,
        ip6_listen=ip6_listen,
        ip6_connect=ip6_connect,
        ssl_connect=ssl_connect,
    )
    try:
        server.main_loop()
    except KeyboardInterrupt:
        sys.stderr.write("Ctrl-C - Stopping server\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
