# coding: utf8
""" A reimplementation of ZeroMQ logging handler. Based on
python-zeromq-log.

General idea:
* ZMQHandler is initialized with zmq socket (or with an uri using
 ZMQHandler.to) and added as a handler to some logger.
* When a record is emitted, it is pickled (NOTE: user-set formatter is
 not supposed to be used) and sent over the socket, as a multipart
 message, together with the `channel`.
* Logging server simply unpickles and handles the record with its
 configured logging.

Required Twisted and TxZMQ.

Note: there is also zmq.log.handlers.PUBHandler, but it converts the
whole message to string before sending rather than doing the final
combining at the receiver's side.
"""

from __future__ import print_function, unicode_literals, absolute_import, division

import warnings
# import traceback
try:
    import cPickle as pickle
except ImportError:
    import pickle
import logging
import zmq
# import zmq.log.handlers as zmqlog
import txzmq
from twisted.internet import reactor


class ZMQFormatter(logging.Formatter):
    _pickle_protocol = -1  # NOTE.
    def makePickle(self, record):
        """ Pickle the record. Code copy from
        logging.handlers.SocketHandler. Does not prepend size.  Possibly
        modifies the record. """
        ei = record.exc_info
        if ei:
            # just to get traceback text into record.exc_text ...
            #dummy = self.format(record)  # infiniterecursion!
            dummy = logging.Formatter.format(self, record)
            record.exc_info = None  # to avoid Unpickleable error
        # See issue #14436: If msg or args are objects, they may not be
        # available on the receiving end. So we convert the msg % args
        # to a string, save it as msg and zap the args.
        d = dict(record.__dict__)  # NOTE: might be preferable to remove this later.
        d['msg'] = record.getMessage()
        d['args'] = None
        s = pickle.dumps(d, self._pickle_protocol)
        if ei:
            record.exc_info = ei  # for next handler
        #slen = struct.pack(">L", len(s))
        #return slen + s
        return s
    def format(self, record):
        """ Format: pickles the record """
        #data = record.__dict__.copy()  # will be preferable to avoid copying
        #data = record
        #if data.get('traceback'):
        #    data['traceback'] = self.formatException(data['traceback'])
        #data['time'] = data['time'].isoformat()  # hopefully unnecessary
        #return pickle.dumps(data)
        return self.makePickle(record)
class ZMQHandler(logging.Handler):
    @classmethod
    def to(cls, uri, *ar, **kwa):
        context = zmq.Context.instance()
        #context = zmq.Context()  # separate thread, maybe
        publisher = context.socket(zmq.PUSH)
        # NOTE: do not wait indefinitely for message sending. Might be a
        #  bad idea though.
        publisher.setsockopt(zmq.LINGER, 7000)
        #publisher.setsockopt(zmq.SNDHWM, 500)
        # ...
        publisher.connect(uri)
        return cls(publisher, *ar, **kwa)
    def __init__(self, zmq_client, name='', channel='log',
                 level=logging.NOTSET):
        super(ZMQHandler, self).__init__(level)
        self.zmq_client = zmq_client
        self.channel = channel
        self.formatter = ZMQFormatter()
    def emit(self, record):
        try:
            msg = self.format(record)
            self.send(msg)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)
    def setFormatter(self, fmt):
        warnings.warn("ZMQHandler's formatter is not supposed to be set.")
    def send(self, data):
        #try:
        self.zmq_client.send_multipart([self.channel, data], zmq.NOBLOCK)
        ## Handler by handleError anyway.
        #except zmq.ZMQError as e:
        #    print("ZMQHandler error")
        #    traceback.print_stack()


class TxLogServer(object):
    """ TxZMQ-based LogServer for the ZMQHandler.  Uses only PULL_BIND
    socket; copy and modify for other cases. """
    def __init__(self, uri, factory=None, run=False):
        self._socket = self._init_zmq(uri, factory=factory)
        self.log_protocol = LogProtocol()
        if run:
            self.run()
    def run(self, verbose=True):
        if verbose:
            print("TxLogServer: Starting.")
        return reactor.run()  # pylint: disable=E1101

    def _init_zmq(self, uri, factory=None):
        socket = txzmq.ZmqPullConnection(
            factory or txzmq.ZmqFactory(),
            txzmq.ZmqEndpoint('bind', uri))
        socket.onPull = self.on_message
        return socket
    def on_message(self, message):
        ## Exception handling is not used here as this is normally
        ##   called from Twisted.
        ## Expecting a multipart message with (topic, recordpickle)
        self.log_protocol.handle_msg(message[0], message[1])
class TxLogServerSub(TxLogServer):
    """ SUB_BIND version """
    def _init_zmq(self, uri, factory=None):
        _zf = factory or txzmq.ZmqFactory()
        _ze = txzmq.ZmqEndpoint('bind', uri)
        socket = txzmq.ZmqSubConnection(_zf, _ze)
        socket.subscribe('')
        socket.gotMessage = self.on_message
        return socket
    def on_message(self, message, tag):
        self.log_protocol.handle_msg(tag, message)
class LogProtocol(object):
    """ Actual data handler for the LogServer """
    def __init__(self):
        self._log = logging.getLogger("logsrv")
        self._log.setLevel(0)
    def handle_msg(self, channel, record_pickle):
        record_data = pickle.loads(record_pickle)
        self.handle(channel, record_data)
    def handle(self, channel, record_data):
        record = logging.makeLogRecord(record_data)
        ## handle `channel`:
        record.name = '{%s} %s' % (channel, record.name)
        # print(record.__dict__)  # dbg
        self._log.handle(record)

# # Sample record data:
# # Normal:
# {'relativeCreated': 925.4779815673828, 'process': 901, 'module': 'tst_zmqlog2', 'funcName': '<module>', 'filename': 'tst_zmqlog2.py', 'levelno': 30, 'processName': 'MainProcess', 'lineno': 12, 'msg': "tst, warn: <open file '/dev/null', mode 'r' at 0x2c5de40>", 'args': None, 'exc_text': None, 'name': 'wut', 'thread': 140164311705344, 'created': 1359000458.195124, 'threadName': 'MainThread', 'msecs': 195.12391090393066, 'pathname': './tst_zmqlog2.py', 'exc_info': None, 'levelname': 'WARNING'}
# # Traceback:
# {'relativeCreated': 925.713062286377, 'process': 901, 'module': 'tst_zmqlog2', 'funcName': '<module>', 'message': 'more tst', 'filename': 'tst_zmqlog2.py', 'levelno': 40, 'processName': 'MainProcess', 'lineno': 18, 'msg': 'more tst', 'args': None, 'exc_text': 'Traceback (most recent call last):\n  File "./tst_zmqlog2.py", line 16, in <module>\n    b = 1/0\nZeroDivisionError: integer division or modulo by zero', 'name': 'wut', 'thread': 140164311705344, 'created': 1359000458.195359, 'threadName': 'MainThread', 'msecs': 195.3589916229248, 'pathname': './tst_zmqlog2.py', 'exc_info': None, 'levelname': 'ERROR'}


def test1():
    import pyaux
    pyaux.runlib.init_logging()
    root_logger = logging.getLogger()
    zh = ZMQHandler.to('ipc://var/log.ipc', channel='the_name')
    root_logger.addHandler(zh)
    root_logger.warn("tst: %r", open('/dev/null'))

    try:
        b = 1/0
    except Exception as e:
        root_logger.exception("more tst")


def test2():
    ## NOTE: Suggested way for configuring the logging is django-style
    ##   settings module with `init_logging(process_name)` function.
    #import settings
    #settings.init_logging("tst_log2")
    import pyaux
    pyaux.runlib.init_logging()
    ## ...
    log = logging.getLogger("wut")

    #time.sleep(0.5)  # connect race condition :(
    #log.debug("tst, dbg: %r", open('/dev/null'))
    #log.info("tst, info: %r", open('/dev/null'))
    log.warn("tst, warn: %r", open('/dev/null'))
    #log.error("tst, err: %r", open('/dev/null'))

    try:
        b = 1/0
    except Exception as e:
        log.exception("more tst")

    print("DONE.")


if __name__ == '__main__':
    import sys
    target = 'test1'
    if len(sys.argv) > 1:
        target = sys.argv[-1]
    ## ...
    if target == 'test1':
        test1()
    elif target == 'test2':
        test2()
