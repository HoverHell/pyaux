""" Various (un)necessary stuff for runscripts """

import os
import sys
import random
import time
import warnings
import logging


__all__ = [
  'init_logging',
  'sigeventer',
]


def _make_short_levelnames(shortnum=True):
    """ Return a dict (levelnum -> levelname) with short names for logging.
    `shortnum`: also shorten all 'Level #' names to 'L##'.
    """
    _names = dict([
      (logging.DEBUG, 'DBG'),
      (logging.INFO, 'INFO'),  # d'uh
      (logging.WARN, 'WARN'),
      (logging.ERROR, 'ERR'),
      (logging.CRITICAL, 'CRIT'),
      ])
    if shortnum:
        for i in xrange(1, 100):
            _names.setdefault(i, "L%02d" % (i,))
    return _names


class LoggingStreamHandlerTD(logging.StreamHandler):
    """ A logging.StreamHandler variery that adds time-difference with the previous log line to the data """

    def __init__(self, *ar, **kwa):
        logging.StreamHandler.__init__(self, *ar, **kwa)
        self.last_ts = time.time()

    def emit(self, record):
        now = time.time()
        prev = self.last_ts
        record.time_diff = (now - prev)
        self.last_ts = now
        return logging.StreamHandler.emit(self, record)


BASIC_LOG_FORMAT = '%(asctime)s: %(levelname)-13s: %(name)s: %(message)s'
BASIC_LOG_FORMAT_TD = '%(asctime)s(+%(time_diff)5.3fs): %(levelname)-13s: %(name)s: %(message)s'

def init_logging(*ar, **kwa):
    """ Simple shorthand for neat and customizable logging init """
    _td = kwa.pop('_td', False)

    colored = kwa.pop('colored', True)
    if colored:
        from . import use_colorer
        use_colorer()
    short_levelnames = kwa.pop('short_levelnames', True)
    if short_levelnames:
        _names = _make_short_levelnames()
        for lvl, name in _names.iteritems():
            logging.addLevelName(lvl, str(name))
    kwa.setdefault('level', logging.DEBUG)
    logformat = BASIC_LOG_FORMAT if not _td else BASIC_LOG_FORMAT_TD
    kwa.setdefault('format', logformat)

    if _td:
        ## can't give it a custom handler class
        # logging.basicConfig(*ar, **kwa)
        hdlr = LoggingStreamHandlerTD(kwa.get('stream'))
        fmt = logging.Formatter(kwa.get('format'), kwa.get('datefmt'))
        hdlr.setFormatter(fmt)
        logging.root.addHandler(hdlr)
        logging.root.setLevel(kwa.get('level', logging.INFO))
    else:
        logging.basicConfig(*ar, **kwa)


import signal
import atexit
import traceback
def argless_wrap(fn):
    """ Wrap function to re-try calling it if calling it with arguments
    failed """
    def argless_internal(*ar, **kwa):
        try:
            return fn(*ar, **kwa)
        except TypeError as e:
            try:
                return fn()
            except TypeError as e2:
                #raise e  # - traceback-inconvenient
                raise  # - error-inconvenient
    return argless_internal
## convenience wrappers:
def _sysexit_wrap(n=None, f=None):
    return sys.exit()
def _atexit_wrap(n=None, f=None):
    return atexit._run_exitfuncs()
class ListSigHandler(list):
    def __init__(self, try_argless, ignore_exc, verbose):
        self.try_argless = try_argless
        self.ignore_exc = ignore_exc
        self.verbose = verbose
    def __call__(self, n, f):
        for func in reversed(self):
            try:
                if self.verbose:
                    print "ListSigHandler: running %r" % (func,)
                if self.try_argless:
                    func = argless_wrap(func)
                func(n, f)
            except Exception, e:
                if self.ignore_exc:
                    if self.verbose:
                        traceback.print_exc()
                    else:
                        ## Still print something
                        print "Exception ignored: %r" % (e,)
                else:
                    raise
def sigeventer(add_defaults=True, add_previous=True, do_sysexit=True,
  try_argless=True, ignore_exc=True, verbose=False):
    """
    Puts one list-based handler for SIGINT and SIGTERM that can be
      `append`ed to.
    NOTE: arguments are ignored if it was called previously.
    `add_defaults`: add the `atexit` handler.
    `add_previous`: add the previously-set handlers (NOTE: will mix
      sigterm/sigint handlers if different).
    `try_argless`: re-call handled function without parameters if they raise
      TypeError.
    `do_sysexit`: do `sys.exit()` at the end of handler.
    `ignore_exc`: ...
    Use `signal.getsignal(signal.SIGINT).append(some_func)` to add a handler.
    Handlers are called in reverse order (first in, last out).
    """
    ## Check if already done something like this:
    curhandler_int = signal.getsignal(signal.SIGINT)
    curhandler_term = signal.getsignal(signal.SIGTERM)
    if isinstance(curhandler_int, list) and isinstance(curhandler_term, list):
        # probaby us already; just return
        assert curhandler_int is curhandler_term, "unexpected: different list-based term/int handlers"
        return curhandler_term
    the_handler = ListSigHandler(try_argless=try_argless, ignore_exc=ignore_exc, verbose=verbose)
    signal.signal(signal.SIGINT, the_handler)
    signal.signal(signal.SIGTERM, the_handler)
    ## Useful since this all will only be done once.
    if do_sysexit:
        the_handler.append(_sysexit_wrap)
    if add_previous:
        ## Note that signal.SIG_DFL will be basically ignored.
        if callable(curhandler_term):
            the_handler.append(curhandler_term)
        if (callable(curhandler_int)
          and curhandler_int != curhandler_term):
            ## (Note that same previous handler still can be called
            ##   twice)
            the_handler.append(curhandler_int)
    if add_defaults:
        the_handler.append(_atexit_wrap)
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
    from twisted.internet import error

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
        class TT_LogFix(telnet.TelnetTransport):
            """ A semi-hax-fix protocol that filters out ConnectionDone errors """
            def connectionLost(self, reason):
                if (reason.check(error.ConnectionDone)
                  or reason.check(error.ConnectionLost)):
                    return
                return telnet.TelnetTransport.connectionLost(self, reason)

        factory.protocol = lambda: (
          TT_LogFix(  #telnet.TelnetTransport(
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
