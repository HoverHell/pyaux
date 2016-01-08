#!/usr/bin/env python
# coding: utf8

# XXXX/TODO: use the module from pyauxm

from __future__ import print_function, unicode_literals, absolute_import, division

import os
import random
import sys
import twisted.python.log as twisted_log
from . import exc_log


class ExcLogObserver(object):
    """ A Twisted Log Observer that uses advanced logging for exceptions """
    # See twisted.python.log.PythonLoggingObserver for information on what is what

    def emit(self, eventDict):
        if not eventDict.get('isError'):
            return  # not for us
        # Obtain the info:
        vf = eventDict.get('failure')
        if vf is not None:
            e_t, e_v, e_tb = vf.type, vf.value, vf.getTracebackObject()
        else:
            e_t, e_v, e_tb = sys.exc_info()
        # sys.excepthook(e_t, e_v, e_tb)  # default-hook
        exc_log.advanced_info_safe(e_t, e_v, e_tb)  # exc_log

    def start(self):
        twisted_log.addObserver(self.emit)

    def stop(self):
        twisted_log.removeObserver(self.emit)


# A singleton instance for convenience
exc_log_observer = ExcLogObserver()


def del_twisted_default_log():
    """ Remove the default log Observer from twisted handler """
    try:
        twisted_log.defaultObserver.stop()
    except ValueError:  # probably removed already
        pass


def make_manhole_telnet(
        socket="./manhole.sock", socket_kwa=None, ns1=None, ns2=None,
        auto_ns=True, verbose=False, run=True, run_reactor=False):
    """ Creates a manhole telnet server over unix socket and returns a
    callable that adds it to the reactor (or runs it if `run`, which
    is default). It needs a running Twisted reactor to work (which is
    started and blocks if `run_reactor`).

    NOTE: authentication is not supported: use either socket file
        permissions or use SSH manhole `make_manhole` instead.

    :param socket_kwa: additional arguments for `reactor.listenUNIX`.
    :param ns1: will be available (if set) under `ns1` in the shell,
    :param ns2: dict whose contents will be available in the namespace itself.
    :param auto_ns: use full namespace (and also `self.__dict__` if
        present) of the caller.
    """
    # ... though I don't even completely know how to add auth in here anyway >.>
    from twisted.internet import reactor
    from twisted.conch import telnet, manhole
    from twisted.conch.insults import insults
    from twisted.internet import protocol
    from twisted.internet import error

    # Namespace stuff
    ns_b = {}
    if auto_ns:
        ns_b.update(sys._getframe(1).f_globals)
        caller_locals = sys._getframe(1).f_locals
        selfdict = getattr(caller_locals.get('self'), '__dict__', None)
        if isinstance(selfdict, dict):
            ns_b.update(selfdict)
        ns_b.update(caller_locals)

    def createShellServer():
        if verbose:
            print('Creating telnet server instance')
        # Namespace stuff
        ns = ns_b
        if ns1 is not None:
            ns['ns1'] = ns1
        if ns2 is not None:
            ns.update(ns2)

        factory = protocol.ServerFactory()

        class TT_LogFix(telnet.TelnetTransport):
            """ A semi-hax-fix protocol that silents out
            ConnectionDone errors """

            def connectionLost(self, reason):
                if (reason.check(error.ConnectionDone) or
                        reason.check(error.ConnectionLost)):
                    return
                return telnet.TelnetTransport.connectionLost(self, reason)

        # This does:
        # f.protocol = lambda: ProtoA(ProtoB, ProtoC, ProtoD, ProtoD_args)
        # (A instantiates B(...) who instantiates C(...) who instantiates D(ProtoD_args))
        factory.protocol = lambda: (
            TT_LogFix(  # telnet.TelnetTransport(
                telnet.TelnetBootstrapProtocol,
                insults.ServerProtocol,  # NOTE: need better terminal (likely)
                manhole.ColoredManhole,
                ns))
        if verbose:
            print('Listening on %r' % (socket,))

        lport = reactor.listenUNIX(  # pylint: disable=E1101
            socket, factory, **(socket_kwa or {}))
        return lport

    def run_manhole(run_reactor=run_reactor):
        """ RTFS """
        reactor.callWhenRunning(  # pylint: disable=E1101
            createShellServer)
        if run_reactor:
            return reactor.run()  # pylint: disable=E1101
        else:
            return reactor.run  # pylint: disable=E1101

    if run:
        return run_manhole()
    else:
        return run_manhole


def make_manhole(
        port=2000, auth_data=None,
        auth_keys_files='~/.ssh/authorized_keys_manhole', ns1=None,
        ns2=None, auto_ns=True, verbose=False, run=True,
        run_reactor=False):
    """ Creates a manhole SSH server and returns a callable that adds
    it to the reactor (or runs it if `run`, which is default). It
    needs a running Twisted reactor to work (which is started and
    blocks if `run_reactor`).

    :param port: TCP port if int or unix socket if str.

    To connect to a unix socket, use
    `ssh -o ProxyCommand='/bin/nc.openbsd -U %h' filename ...`

    :param auth_data: list or dict of (username, password);
        if password is None, it will be auto-generated and printed.
    :param auth_keys_files: list of filenames with
        'authorized_keys'-like files ('~' is expanded, relative path
        are relative to the __main__).
    :param ns1: will be available (if set) under `ns1` in the shell,
    :param ns2: dict whose contents will be available in the namespace itself.
    :param auto_ns: use full namespace (and also `self.__dict__` if
        present) of the caller.
    """
    ## Everything is cramped in this one function for simplicity. Uncramp
    ##  and put into a separate module if needs be.
    from twisted.internet import reactor
    from twisted.cred import portal, checkers
    from twisted.conch import manhole, manhole_ssh
    from twisted.conch.checkers import SSHPublicKeyDatabase
    from twisted.python.filepath import FilePath

    if isinstance(port, (bytes, str)):
        use_unix_sock = True
    elif isinstance(port, int):
        use_unix_sock = False
    else:
        raise Exception("`port` is of unknown type")

    ns_b = {}
    if auto_ns:
        ns_b.update(sys._getframe(1).f_globals)
        caller_locals = sys._getframe(1).f_locals
        selfdict = getattr(caller_locals.get('self'), '__dict__', None)
        if isinstance(selfdict, dict):
            ns_b.update(selfdict)
        ns_b.update(caller_locals)

    class AuthorizedKeysChecker(SSHPublicKeyDatabase):
        def __init__(self, authorized_keys_files):
            # # Twisted... old-style classes.
            # super(AuthorizedKeysChecker, self).__init__()
            # # And no __init__ at all anyway.
            # SSHPublicKeyDatabase.__init__(self)
            if not isinstance(authorized_keys_files, (list, tuple)):
                authorized_keys_files = [authorized_keys_files]

            # The horror? Relative path in params are relative to the __main__
            basebasepath = os.path.dirname(os.path.abspath(
                sys.modules['__main__'].__file__))

            def process_filepath(path):
                # `path.startswith('/'):` but crossplatform
                if os.path.isabs(path):
                    return path  # already absolute
                elif path.startswith('~'):
                    return os.path.expanduser(path)
                else:  # Expand relative otherwise.
                    return os.path.join(basebasepath, path)

            self.authorized_keys_files = [
                FilePath(process_filepath(v)) for v in authorized_keys_files]

        def getAuthorizedKeysFiles(self, credentials):
            # # This function is overridden from parent
            # return [FilePath(v) for v in self.authorized_keys_files]
            return self.authorized_keys_files

    def createShellServer():
        if verbose:
            print('Creating shell server instance')
        z_auth_data = dict(auth_data or {})
        for k, v in z_auth_data.items():
            if v is None:
                rndpwd = "%x" % random.getrandbits(128)
                z_auth_data[k] = rndpwd
                print("Manhole password for %r: %r" % (k, rndpwd))

        # Namespace stuff
        ns = ns_b
        if ns1 is not None:
            ns['ns1'] = ns1
        if ns2 is not None:
            ns.update(ns2)

        mhrealm = manhole_ssh.TerminalRealm()
        mhrealm.chainedProtocolFactory.protocolFactory = (
            lambda v: manhole.Manhole(ns))
        mhportal = portal.Portal(mhrealm)
        mhportal.registerChecker(
            checkers.InMemoryUsernamePasswordDatabaseDontUse(**z_auth_data))
        mhportal.registerChecker(AuthorizedKeysChecker(auth_keys_files))
        ## pubkeys from parameters... not very needed.
        #mhportal.registerChecker(PubKeysChecker(zauthorizedKeys))
        mhfactory = manhole_ssh.ConchFactory(mhportal)
        if verbose:
            print('Listening on %r' % (port,))
        if use_unix_sock:
            lport = reactor.listenUNIX(  # pylint: disable=E1101
                port, mhfactory)
        else:
            lport = reactor.listenTCP(  # pylint: disable=E1101
                port, mhfactory)
        return lport

    def run_manhole(run_reactor=run_reactor):
        """ RTFS """
        if verbose:
            print('Registering Manhole server with the reactor')
        reactor.callWhenRunning(  # pylint: disable=E1101
            createShellServer)
        if run_reactor:
            if verbose:
                print('Running Twisted Reactor')
            return reactor.run()  # pylint: disable=E1101
        else:
            return reactor.run  # pylint: disable=E1101

    if run:
        return run_manhole()
    else:
        return run_manhole
