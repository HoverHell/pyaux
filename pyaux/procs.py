# coding: utf8
"""
Additional utils for working with subprocesses.
"""

from __future__ import print_function, unicode_literals, absolute_import, division

import datetime
import subprocess

from .base import monotonic_now


def _out_cb_default_common(tag, line, timestamp=None, encoding='utf-8', errors='replace'):
    # timestamp_dt = datetime.datetime.fromtimestamp(timestamp)
    # # Less precise, more convenient.
    timestamp_dt = datetime.datetime.now()
    line = line.decode(encoding, errors=errors)
    if line.endswith('\n'):
        line = line[:-1]
    else:  # disambiguate
        line += '\\'
    print(
        timestamp_dt.strftime('%H:%M:%S'),
        tag,
        line)


def stdout_cb_default(line, timestamp=None, **kwargs):
    return _out_cb_default_common('O:', line, timestamp=timestamp)


def stderr_cb_default(line, timestamp=None, **kwargs):
    return _out_cb_default_common('E:', line, timestamp=timestamp)


class ProcessTimeoutError(Exception):
    """ ... """


class NonzeroExit(Exception):
    """ ... """


def set_fd_nonblocking(fdesc):
    import fcntl
    from os import O_NONBLOCK
    flags = fcntl.fcntl(fdesc, fcntl.F_GETFL)
    fcntl.fcntl(fdesc, fcntl.F_SETFL, flags | O_NONBLOCK)
    return fdesc


def poll_fds(
        fdmapping,
        log=lambda msg, *args: None,
        nonblocking=False,
        inner_timeout=1.0,
        total_timeout=None):
    """
    Given a `name -> fd` mapping, polls all the FDs until they are done
    and callbacks with (name, timestamp, data) tuples.

    If `nonblocking` is enabled it will try to read the data as it
    comes; otherwise it will read the data in lines (which can be less
    precise but more useful).

    Note that for precise timestamps in the result you need to minimize the
    output processing time.
    """
    import select

    start_time = monotonic_now()
    end_time = None
    if total_timeout:
        end_time = start_time + total_timeout

    # NOTE: also used to keep the current ones (removes fds as they
    # are done).
    fdrev = {fd: name for name, fd in fdmapping.items()}

    if nonblocking:
        for fdesc in fdrev:
            set_fd_nonblocking(fdesc)

    while True:
        if not fdrev:
            break
        fdlist = list(fdrev)
        timeout = inner_timeout
        if end_time:
            timeout = min(end_time - monotonic_now(), timeout)
            if timeout < 0.00001:
                raise ProcessTimeoutError(total_timeout)

        ready_fds, _, _ = select.select(fdlist, (), (), timeout)
        for fdesc in ready_fds:
            tag = fdrev[fdesc]
            timestamp = monotonic_now()
            if nonblocking:
                try:
                    data = fdesc.read()
                except OSError:
                    data = None
            else:
                data = fdesc.readline()
            if not data:
                log("fd is empty: %r / %r", tag, fdesc)
                fdrev.pop(fdesc)
                continue
            log("output (%r, %r, %r)", tag, timestamp, data)
            yield tag, timestamp, data


def run_cmd(*args, **kwargs):

    timeout = kwargs.pop('timeout', 600)
    stdout_cb = kwargs.pop('stdout_cb', stdout_cb_default)
    stderr_cb = kwargs.pop('stderr_cb', stderr_cb_default)
    nonblocking = kwargs.pop('nonblocking', False)

    tag_to_cb = dict(stdout=stdout_cb, stderr=stderr_cb)

    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)

    tag_to_fd = dict(stdout=proc.stdout, stderr=proc.stderr)
    outputs = poll_fds(tag_to_fd, nonblocking=nonblocking, total_timeout=timeout)
    for tag, timestamp, data in outputs:
        tag_to_cb[tag](data, timestamp=timestamp, proc=proc, outputs=outputs)

    ret = proc.poll()
    # Might or might not be required for the pipes to get closed:
    proc.communicate()
    if ret:
        raise NonzeroExit(ret)

    # ...


def main():
    """ A simple form of 'annotate-output' """
    # cmd = ('ping', '-c', '4', '-i', '0.2', '1.1.1.1')
    # cmd = ('sh', '-c', 'date -Ins; printf "zxcv"; sleep 5; printf "qwer\n"; date -Ins')
    import sys
    cmd = sys.argv[1:]
    run_cmd(*cmd, nonblocking=True)


if __name__ == '__main__':
    # python -m pyaux.procs ping -c 4 -i 0.2 1.1.1.1
    main()
