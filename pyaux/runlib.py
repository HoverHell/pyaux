""" Various (un)necessary stuff for runscripts """

import os
import sys
import random
import warnings


__all__ = [
  'init_logging',
  'sigeventer',
]


def init_logging(*ar, **kwa):
    """ Simple shorthand for neat and customizable logging init """
    import logging
    colored = kwa.pop('colored', True)
    if colored:
        from . import use_colorer
        use_colorer()
    kwa.setdefault('level', logging.DEBUG)
    kwa.setdefault('format',
      '%(asctime)s | %(levelname)-16s | %(name)s | %(message)s')
    logging.basicConfig(*ar, **kwa)


def sigeventer(add_defaults=True, do_sysexit=True, try_argless=True,
  ignore_exc=True, verbose=False):
    """
    Puts list-based handler for SIGINT and SIGTERM that can be appended to.
    `add_defaults`: add the `atexit` handler.
    `try_argless`: re-call handled function without parameters if they raise
      TypeError.
    `do_sysexit`: do `sys.exit()` at the end of handler.
    `ignore_exc`: ...
    Use `signal.getsignal(signal.SIGINT).append(some_func)` to add a handler.
    Handlers are called in reverse order (first in, last out).
    """
    import signal
    import atexit
    import traceback
    ## Check if already done something like this:
    ## TODO: make a more elaborate handling of currently set sighandlers.
    curhandler = signal.getsignal(signal.SIGINT)
    if isinstance(curhandler, list):
        return curhandler
    class ListHandler(list):
        def __call__(self, n, f):
            for func in reversed(self):
                try:
                    if verbose:
                        print "ListSigHandler: running %r" % (func,)
                    try:
                        func(n, f)
                    except TypeError, ee:
                        if try_argless:
                            try:
                                func()
                            except TypeError:
                                raise ee
                        else:
                            raise
                except Exception, e:
                    if ignore_exc:
                        if verbose:
                            traceback.print_exc()
                        else:
                            ## Still print something
                            print "Exception ignored: %r" % (e,)
                    else:
                        raise
            if do_sysexit:
                sys.exit()
    the_handler = ListHandler()
    signal.signal(signal.SIGINT, the_handler)
    signal.signal(signal.SIGTERM, the_handler)
    if add_defaults:
        the_handler.append(lambda n, f: atexit._run_exitfuncs())
    return the_handler


## XXX: move this to twisted_aux?
def make_manhole_telnet(socket="./manhole.sock", socket_kwa=None,
  ns1=None, ns2=None, auto_ns=True,
  verbose=False, run=True, run_reactor=False):
    """ Creates a manhole telnet server over unix socket and returns a
      callable that adds it to the reactor (or runs it if `run`, which
      is default). It needs a running Twisted reactor to work (which is
      started and blocks if `run_reactor`).
    NOTE: authentication is not supported: use either socket file
      permissions or use SSH manhole `make_manhole` instead.
    `socket_kwa` are additional arguments for `reactor.listenUNIX`.
    `ns1` will be available (if set) under `ns1`,
    `ns2` contents will be available in the namespace itself.
    `auto_ns`: use full namespace (and also `self.__dict__` if present) of
      the caller.
    """
    ## ... though I don't even completely know how to add auth in here anyway >.>
    from twisted.internet import reactor
    from twisted.conch import telnet, manhole
    from twisted.conch.insults import insults
    from twisted.internet import protocol

    ## Namespace stuff
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
            print 'Creating telnet server instance'
        ### Namespace stuff
        ns = ns_b
        if ns1 != None:
            ns['ns1'] = ns1
        if ns2 != None:
            ns.update(ns2)

        factory = protocol.ServerFactory()
        ### This does:
        ### f.protocol = lambda: ProtoA(ProtoB, ProtoC, ProtoD, ProtoD_args)
        ##  (A instantiates B(...) who instantiates C(...) who instantiates D(ProtoD_args))
        factory.protocol = lambda: (
          telnet.TelnetTransport(
            telnet.TelnetBootstrapProtocol,
            insults.ServerProtocol,  # NOTE: need better terminal (likely)
            manhole.ColoredManhole,
            ns))
        if verbose:
            print 'Listening on %r' % (socket,)
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


def make_manhole(port=2000, auth_data=None,
  auth_keys_files='~/.ssh/authorized_keys_manhole', ns1=None, ns2=None,
  auto_ns=True, verbose=False, run=True, run_reactor=False):
    """ Creates a manhole SSH server and returns a callable that adds
      it to the reactor (or runs it if `run`, which is default). It needs
      a running Twisted reactor to work (which is started and blocks if
      `run_reactor`).
    Port is TCP port if int or unix socket if str.
    To connect to a unix socket, use
      `ssh -o ProxyCommand='/bin/nc.openbsd -U %h' filename ...`
    `auth_data` is list or dict of (username, password);
      password will be auto-generated and printed if set to `None`.
    `auth_keys_files` is list of filenames with 'authorized_keys'-like files
      ('~' is expanded, relative path are relative to the __main__).
    `ns1` will be available (if set) under `ns1`,
    `ns2` contents will be available in the namespace itself.
    `auto_ns`: use full namespace (and also `self.__dict__` if present) of
      the caller.
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
            ## Twisted... old-style classes.
            #super(AuthorizedKeysChecker, self).__init__()
            ## And no __init__ at all anyway.
            #SSHPublicKeyDatabase.__init__(self)
            if not isinstance(authorized_keys_files, (list, tuple)):
                authorized_keys_files = [authorized_keys_files]
            ## The horror? Relative path in params are relative to the __main__
            basebasepath = os.path.dirname(os.path.abspath(
              sys.modules['__main__'].__file__))
            def process_filepath(path):
                if os.path.isabs(path):  # `path.startswith('/'):` - non-crossplatform
                    return path  # already absolute
                elif path.startswith('~'):
                    return os.path.expanduser(path)
                else:  ## Expand relative otherwise.
                    return os.path.join(basebasepath, path)
            self.authorized_keys_files = [
              FilePath(process_filepath(v)) for v in authorized_keys_files]
        def getAuthorizedKeysFiles(self, credentials):
            ## This function is overridden from parent
            #return [FilePath(v) for v in self.authorized_keys_files]
            return self.authorized_keys_files
    def createShellServer():
        if verbose:
            print 'Creating shell server instance'
        z_auth_data = dict(auth_data or {})
        for k, v in z_auth_data.iteritems():
            if v == None:
                rndpwd = "%x" % random.getrandbits(128)
                z_auth_data[k] = rndpwd
                print "Manhole password for %r: %r" % (k, rndpwd)
        ## Namespace stuff
        ns = ns_b
        if ns1 != None:
            ns['ns1'] = ns1
        if ns2 != None:
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
            print 'Listening on %r' % (port,)
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
            print 'Registering Manhole server with the reactor'
        reactor.callWhenRunning(  # pylint: disable=E1101
          createShellServer)
        if run_reactor:
            if verbose:
                print 'Running Twisted Reactor'
            return reactor.run()  # pylint: disable=E1101
        else:
            return reactor.run  # pylint: disable=E1101
    if run:
        return run_manhole()
    else:
        return run_manhole
