#!/usr/bin/env python

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from __future__ import print_function, unicode_literals, absolute_import, division

import os
import math
import struct
import sys
from six.moves import cPickle as pickle


__author__ = "Pedro Larroy"
__version__ = "0.1"
__date__ = "2011-07-29"
__maintainer__ = "Pedro Larroy http://pedro.larroy.com"


def numcores():
    return int(os.popen('grep core\ id /proc/cpuinfo  | wc -l').read()[:-1])


def forkfun(accumulator, function, sequence):
    # IPC stuff
    structformat = 'L'
    structlen = struct.calcsize(structformat)

    def sendmessage(myend, message):
        """ Send a pickled message across a pipe """
        outobj = pickle.dumps(message)
        return os.write(myend, struct.pack(structformat, len(outobj)) + outobj)

    def recvmessage(myend):
        """ Receive a pickled message from a pipe """
        buf = os.read(myend, structlen)
        if not buf:
            raise EOFError('EOF on pipe from parent, pid: {0}'.format(os.getpid()))

        length = struct.unpack(structformat, buf)[0]
        return pickle.loads(os.read(myend, length))

    try:
        maxchildren = function.parallel_maxchildren
    except AttributeError:
        maxchildren = numcores()

    assert function
    assert accumulator

    finished = 0

    # Spawn the worker children.  Don't create more than the number of
    # values we'll be processing.
    fromchild, toparent = os.pipe()
    children = []

    sequence_iter = sequence.__iter__()
    sequence_idx = 0

    for childnum in range(min(maxchildren, len(sequence))):
        fromparent, tochild = os.pipe()
        pid = os.fork()
        # Parent?
        if pid:
            os.close(fromparent)
            # Do some housekeeping and give the child its first assignment
            children.append({'pid': pid, 'tochild': tochild})
            cnt = sendmessage(tochild, (sequence_idx, sequence_iter.next()))
            if not cnt:
                raise EOFError('EOF on pipe to child {0}'.format(childnum))
            sequence_idx += 1

        # Child?
        else:
            os.close(tochild)

            # Keep processing values until the parent kills you
            while True:
                try:
                    message = recvmessage(fromparent)
                    if message is None:
                        sys.exit()
                    index, value = message
                    if not sendmessage(toparent, (childnum, index, function(value))):
                        sys.stderr.write('Child {0}: pipe eof\n'.format(childnum))

                except Exception as excvalue:
                    sys.stderr.write('Exception: {0}\n'.format(excvalue))

                    # # For debugging where the exception took place, enable this:
                    # raise

                    if not sendmessage(toparent, (childnum, index, excvalue)):
                        sys.stderr.write('Child {0}: pipe eof\n'.format(childnum))
                    sys.exit()

    # Keep accepting values back from the children until they've
    # all come back
    while finished < len(sequence):
        returnchild, returnindex, value = recvmessage(fromchild)
        if isinstance(value, Exception):
            raise value

        # If there are still values left to process, hand one
        # back out to the child that just finished
        if sequence_idx < len(sequence):
            sendmessage(children[returnchild]['tochild'],
                        (sequence_idx, sequence_iter.next()))
            sequence_idx += 1

        accumulator(value)
        finished += 1

    for child in children:
        sendmessage(child['tochild'], None)

    for child in children:
        os.wait()


def parallelizable(maxchildren=None, perproc=None):
    """ Mark a function as eligible for parallelized execution.  The
    function will run across a number of processes equal to
    maxchildren, perproc times the number of processors installed on
    the system, or the number of times the function needs to be run to
    process all data passed to it - whichever is least. """
    if not maxchildren:
        try:
            maxchildren = numcores()
        except ValueError:
            maxchildren = 2

    if perproc is not None:
        processors = 4  # hand-waving
        maxchildren = min(maxchildren, perproc * processors)

    def decorate(func):
        """Set the parallel_maxchildren attribute to the value
        appropriate for this function"""
        setattr(func, 'parallel_maxchildren', maxchildren)
        return func

    return decorate


if __name__ == '__main__':

    def f(x):
        y = x ** 3
        z = math.sqrt(y)
        return z
        # x = math.acos(z)

    def acc(x):
        print(x)
        pass

    forkfun(acc, f, range(100000))


# if __name__ == '__main__':
#     import doctest
#     doctest.testmod()
#
#     @parallelizable(10, perproc=4)
#     def timestwo(x, y):
#         return (x + y) * 2
#     print map(timestwo, [1, 2, 3, 4], [7, 8, 9, 10])
#
#     #@parallelizable(10)
#     @parallelizable()
#     def busybeaver(x):
#         for i in range(10000000):
#             x = x + i
#         return x
#     print map(busybeaver, range(27))
