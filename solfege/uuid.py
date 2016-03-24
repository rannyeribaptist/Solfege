# uuid.py -- pure python implementation of uuidgen
#
# Copyright (C) 2005 Denys Duchier
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
###
################################################################################
###
### The code below follows, as closely as I could manage, Theodore
### Tso's C code of libuuid's file gen_uuid.c distributed with
### package e2fsprogs
###
### enabling "psyco" considerably improves the performance of this code
###
### public API:
###
###	uuid.generate()
###	uuid.generate_random()
###	uuid.generate_time()
###
###	uuid.linux_generate()
###
###	uuid.py_generate()
###	uuid.py_generate_random()
###	uuid.py_generate_time()
###
###	uuid.set_method(USE_MAC|USE_SHA|USE_RANDOM)
###
### these functions return a new uuid string on each invocation.
###
################################################################################

from __future__ import absolute_import
"""\
This module provides functions to generate universally unique identifiers
(UUID).  It is provides an implementation in pure python that follows closely
Theodore's Tso's libuuid C code distributed with the e2fsprogs package.  It is
also able to use the system's libuuid if available.

The following functions use the system's libuuid if available, or the Linux
/proc/sys/kernel/random/uuid interface if available, else default back to the
pure python implementation:

generate() -- generate a uuid using the best available method
generate_random() -- generate a uuid using a random number generator
generate_time() -- generate a uuid based on time and hardware address

Pure python implementation:

py_generate() -- like generate() but in pure python
py_generate_random() -- like generate_random() but in pure python
py_generate_time() -- like generate_time but in pure python

a uuid is a string that looks like fa485e1d-3b1d-413b-aac0-72aaf2830ec0,
i.e. follows the printf format %08x-%04x-%04x-%04x-%012x.

Note: py_generate_time is much faster than py_generate_random but of much
lesser quality

Hint: enabling psyco considerably improves the performance of the pure
python implementation.
"""

__all__ = ["generate","generate_random","generate_time",
           "py_generate","py_generate_random","py_generate_time",
           "set_method","USE_MAC","USE_RANDOM","USE_SHA"]

import os
import datetime
from time import mktime as _mktime
from random import randint as _randint
from struct import pack as _pack
from struct import unpack as _unpack
from sys import maxint as _maxint

_now = datetime.datetime.now

def _gettimeofday():
    d=_now()
    return int(_mktime(d.timetuple())),d.microsecond

_random_reader = None
_random_init = False

if hasattr(os,"urandom"):
    try:
        os.urandom(8)
        _random_reader = os.urandom
        _random_init = True
    except:
        pass

def _get_random_reader():
    global _random_reader, _random_init
    if not _random_init:
        try:
            import random
            try:
                _random_reader = open("/dev/urandom","rb").read
            except:
                _random_reader = os.fdopen(os.open("/dev/random",os.O_RDONLY|os.O_NONBLOCK),"rb").read
            sec,usec = _gettimeofday()
            random.seed((os.getpid() << 16) ^ os.getuid() ^ sec ^ usec)
        except:
            pass
        _random_init = True
    sec,usec = _gettimeofday()
    i = (sec ^ usec) & 0x1F
    while i>0:
        _randint(0,_maxint)
        i -= 1
    return _random_reader

_fmt_16 = ">16B"
_fmt_6 = ">6B"
_fmt_2 = ">2B"

def _randomize_byte(b):
    return b ^ ((_randint(0,_maxint) >> 7) & 0xFF)

def _get_random_bytes(n):
    reader = _get_random_reader()
    buf = ''
    if reader:
        loose_counter = 0
        while len(buf) != n:
            buf += reader(n)
            if loose_counter > 10:
                break
            loose_counter += 1
    d = n-len(buf)
    if d>0:
        buf += '\0'*d
    if n==16:
        fmt = _fmt_16
    elif n==6:
        fmt = _fmt_6
    elif n==2:
        fmt = _fmt_2
    else:
        fmt = ">%sB" % n
    return _pack(fmt,*tuple(map(_randomize_byte,_unpack(fmt,buf))))

def _uuid_unpack(buf):
    return _unpack(">IHHH6s",buf)

def _uuid_unpack_fully(buf):
    return _unpack(">IHHHBBBBBB",buf)

def _uuid_pack(low,mid,hi,seq,node):
    return _pack(">IHHH6s",low,mid,hi,seq,node)

def _uuid_unparse(uu):
    low,mid,hi,seq,b5,b4,b3,b2,b1,b0 = _uuid_unpack_fully(uu)
    return "%08x-%04x-%04x-%02x%02x-%02x%02x%02x%02x%02x%02x" % (low,mid,hi,seq>>8,seq&0xFF,b5,b4,b3,b2,b1,b0)

def _uuid_generate_random():
    buf = _get_random_bytes(16)
    low,mid,hi_and_version,seq,node = _uuid_unpack(buf)
    seq = (seq & 0x3FFF) | 0x8000
    hi_and_version = (hi_and_version & 0x0FFF) | 0x4000
    return _uuid_pack(low,mid,hi_and_version,seq,node)

def _backtick(pgm):
    try:
        i,o = os.popen4(pgm)
        i.close()
        return o.read()
    except:
        return ""

def _decode_hex(s):
    return int(s,16)

def _get_mac_address():
    import re
    r = re.compile("HWaddr (..:..:..:..:..:..)")
    m = r.search(_backtick("/sbin/ifconfig"))
    if m:
        s = m.group(1)
        return map(_decode_hex,s.split(":"))
    m = r.search(_backtick("ifconfig"))
    if m:
        s = m.group(1)
        return map(_decode_hex,s.split(":"))
    r = re.compile("Physical Address.*: (..:..:..:..:..:..)")
    m = r.search(_backtick("ipconfig /all"))
    if m:
        s = m.group(1)
        return map(_decode_hex,s.split(":"))
    return None

def _get_6bytes(mac=None):
    try:
        import sha,getpass,socket,time
        buf = sha.new()
        if mac:
            buf.update("%c%c%c%c%c%c " % tuple(mac))
        buf.update(getpass.getuser())
        buf.update("@%s" % socket.gethostname())
        buf.update(" %s" % os.getpid())
        buf.update(" %s" % time.strftime("%Y-%m-%d %H:%M:%S %Z"))
        return map(ord,buf.digest()[0:6])
    except:
        return None

USE_MAC    = 0
USE_RANDOM = 1
USE_SHA    = 2

_common_suffix_method = USE_MAC
_static_time_buf = None

def _set_common_suffix():
    global _static_time_buf
    if _common_suffix_method == USE_RANDOM:
        _static_time_buf = _get_random_bytes(6)
        # I don't know how to set the multicast bit
        # so I am leaving that out
    else:
        suf = _get_mac_address()
        if _common_suffix_method == USE_SHA:
            suf = _get_6bytes(suf)
        if suf:
            _static_time_buf = _pack(_fmt_6,*suf)
        else:
            _static_time_buf = _get_random_bytes(6)
            # I don't know how to set the multicast bit
            # so I am leaving that out

def set_method(meth):
    """Set the method to be used to generate the common suffix of uuids
    when py_generate_time is invoked.  The argument can be one of the
    following constrants:

    USE_MAC -- use the mac address is it can be determined, else try USE_SHA
    USE_SHA -- create a digest of mac address, user info and time, else try USE_RANDOM
    USE_RANDOM -- generate a random number
    """
    global _common_suffix_method
    if _common_suffix_method == meth:
        return
    _common_suffix_method = meth
    _set_common_suffix()

def _uuid_generate_time():
    global _static_time_buf
    if not _static_time_buf:
        _set_common_suffix()
    mid,low,seq = _get_clock()
    seq = seq | 0x8000
    hi = (mid >> 16) | 0x1000
    return _uuid_pack(low,mid,hi,seq,_static_time_buf)

_static_last_sec = 0
_static_last_msec = 0
_static_adjustment = 0
_MAX_ADJUSTMENT = 10
_static_clock_seq = 0

def _get_clock():
    global _static_last_sec,_static_last_msec,_static_adjustment,_static_clock_seq
    sec,msec = _gettimeofday()
    try_again = True
    while try_again:
        try_again = False
        if _static_last_sec==0 and _static_last_msec==0:
            _static_clock_seq = _unpack(">H",_get_random_bytes(2))[0] & 0x1FFF
            _static_last_sec = sec - 1
            _static_last_msec = msec
        if sec < _static_last_sec or ((sec == _static_last_sec) and (msec < _static_last_msec)):
            _static_clock_seq = (_static_clock_seq+1) & 0x1FFF
            _static_adjustment = 0
            _static_last_sec = sec
            _static_last_msec = msec
        elif sec == _static_last_sec and msec == _static_last_msec:
            if _static_adjustment >= _MAX_ADJUSTMENT:
                try_again = True
            else:
                _static_adjustment += 1
        else:
            _static_adjustment = 0
            _static_last_sec = sec
            _static_last_msec = msec
    clock_reg = msec*10 + _static_adjustment
    clock_reg = (clock_reg + sec*10000000) & 0xFFFFFFFFFFFFFFFFL
    clock_reg = (clock_reg + (((0x01B21DD2L) << 32) + 0x13814000L)) & 0xFFFFFFFFFFFFFFFFL
    return (clock_reg >> 32),(clock_reg & 0xFFFFFFFFL),_static_clock_seq

def _uuid_generate():
    if _get_random_reader():
        return _uuid_generate_random()
    else:
        return _uuid_generate_time()

def py_generate():
    """Generate a UUID using the best available method.

    uses py_generate_random if a high-quality source of randomness
    is available, else py_generate_time
    """
    return _uuid_unparse(_uuid_generate())

def py_generate_time():
    """Generate a UUID by mixing time and MAC address.
    """
    return _uuid_unparse(_uuid_generate_time())

def py_generate_random():
    """Generate a UUID using a high-quality source of randomness.
    """
    return _uuid_unparse(_uuid_generate_random())

################################################################################
### Here is an interface to libuuid, just in case it happens to be available ###
################################################################################

_libuuid = None

try:
    import dl
    _libuuid = dl.open("libuuid.so")
except:
    pass

# I am being a bad boy: libuuid functions, when invoked, are passed strings
# which they modify.  This is supposed to be a no-no as documented in the dl
# module.  However, I create these strings anew each time using struct.pack,
# they are never uniquified nor hashed, and they are thrown away as soon as
# possible.  I think this is actually safe.  If I am wrong, please let me know.

def libuuid_generate():
    """Generate a UUID with libuuid using the best available method.
    This will raise an exception if libuuid is not available.
    """
    buf = _pack(">16s","")
    out = _pack(">37s","")
    _libuuid.call("uuid_generate",buf)
    _libuuid.call("uuid_unparse",buf,out)
    return _unpack(">36sB",out)[0]

def libuuid_generate_random():
    """Generate a UUID with libuuid using a high-quality source of randomness.
    This will raise an exception if libuuid is not available.
    """
    buf = _pack(">16s","")
    out = _pack(">37s","")
    _libuuid.call("uuid_generate_random",buf)
    _libuuid.call("uuid_unparse",buf,out)
    return _unpack(">36sB",out)[0]

def libuuid_generate_time():
    """Generate a UUID with libuuid by mixing time and MAC address.
    This will raise an exception if libuuid is not available.
    """
    buf = _pack(">16s","")
    out = _pack(">37s","")
    _libuuid.call("uuid_generate_time",buf)
    _libuuid.call("uuid_unparse",buf,out)
    return _unpack(">36sB",out)[0]

def linux_generate():
    """Generate a UUID by reading from /proc/sys/kernel/random/uuid.
    This will raise an exception if we are not on Linux
    """
    f = open('/proc/sys/kernel/random/uuid')
    s = f.readline().strip()
    f.close()
    return s

generate = None
generate_random = None
generate_time = None

if _libuuid:
    generate = libuuid_generate
    generate_random = libuuid_generate_random
    generate_time = libuuid_generate_time
else:
    try:
        if linux_generate():
            generate = linux_generate
            generate_random = linux_generate
            generate_time = linux_generate
    except:
        pass
    if not generate:
        generate = py_generate
        generate_random = py_generate_random
        generate_time = py_generate_time

if __name__ == '__main__':
    import getopt,sys
    gen = generate
    opts,args = getopt.getopt(sys.argv[1:],"rth",["help"])
    for o,v in opts:
        if o == "-t":
            gen = generate_time
        elif o == "-r":
            gen = generate_random
        else:
            print "usage: uuid.py [-r|-t]"
            print "generate a random-based UUID (-r, default), or a time-based one (-t)"
            sys.exit(0)
    print gen()
