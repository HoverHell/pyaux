#!/usr/bin/env python
""" lzcat """

import pylzma


def unlzma(fi, fo, fi_close=True, fo_close=True, bufs=65535):
    """ Decompress `fi` into `fo` (`file` or filename) """
    if isinstance(fi, str):
        fi, fi_n = open(fi, 'rb'), fi
        #fi_close = True
    if isinstance(fo, str):
        fo, fo_n = open(fo, 'wb'), fo
        #fo_close = True
    #fi.seek(0)
    s = pylzma.decompressobj()
    while True:
        tmp = fi.read(bufs)
        if not tmp:
            break
        fo.write(s.decompress(tmp))
    fo.write(s.flush())
    if fo_close:
        fo.close()
    if fi_close:
        fi.close()
    return fi, fo


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        fi_a = sys.argv[1]
    else:
        fi_a = sys.stdin
    if len(sys.argv) == 3:
        fo_a = sys.argv[2]
    else:
        fo_a = sys.stdout
    if len(sys.argv) > 3:
        print "Basic usage: %s <from_file> [<to_file>]" % (sys.argv[0],)

    if fi_a == '-':
        fi_a = sys.stdin
    if fo_a == '-':
        fo_a = sys.stdout
    unlzma(fi_a, fo_a)
