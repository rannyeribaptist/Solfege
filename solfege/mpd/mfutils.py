# GNU Solfege - free ear training software
# Copyright (C) 2000, 2001, 2002, 2003, 2004, 2007, 2008, 2011  Tom Cato Amundsen
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

from __future__ import absolute_import
def mf_delta(i):
    assert isinstance(i, int) and i >= 0
    vect = []
    v = []
    not_first = 0
    while 1:
        bits = i & 0x7f
        i = i >> 7
        v.insert(0, bits+not_first*0x80)
        not_first = 1
        if i == 0: # hvis det ikke er flere bit'er igjen
            break
    vect = vect + v
    return vect

def mf_int16(i):
    assert isinstance(i, int) and 0 <= i < 2**16
    return [i >> 8 & 0xff, i  & 0xff]

def mf_int24(i):
    assert isinstance(i, int) and 0 <= i < 2**24
    return [i >> 16 & 0xff, i >> 8 & 0xff, i  & 0xff]

def mf_int32(i):
    assert isinstance(i, int) and 0 <= i < 2L**32
    return [i >> 24 & 0xff, i >> 16 & 0xff, i >> 8 & 0xff, i  & 0xff]

def write_int16(f, i):
    assert isinstance(i, int) and 0 <= i < 2**16
    f.write(chr(i >> 8 & 0xff))
    f.write(chr(i  & 0xff))

def write_int32(f, i):
    assert isinstance(i, int) and 0 <= i < 2L**32
    f.write(chr(i >> 24 & 0xff))
    f.write(chr(i >> 16 & 0xff))
    f.write(chr(i >> 8 & 0xff))
    f.write(chr(i  & 0xff))

MIDI_NOTE_OFF = 0x80
MIDI_NOTE_ON = 0x90
MIDI_CONTROLLER_CHANGE = 0xb0
MIDI_PROGRAM_CHANGE = 0xc0

MIDI_CONTROLLER_VOLUME = 0x07

def mf_tempo(n):
    """
    n -- number of quarter tones per minute.
    """
    #    now          Code to set tempo
    v = mf_delta(0) + [0xff, 0x51, 0x03] + mf_int24(int(500000*120/n))
    return v

def mf_timesig(numerator, denuminator):
    d = {0:1, 2:1, 4:2, 8:3, 16:4, 32:5, 64:6}[denuminator]
    return mf_delta(0) + [0xff, 0x58, 0x04,
                          numerator, d,   # 4/4      2=4-del 3=8-del 4=16-del
                          0x10, #0x18
                          0x08]

def mf_program_change(chan, prg):
    assert 0 <= chan < 16
    return mf_delta(0) + [chan+MIDI_PROGRAM_CHANGE, prg]

def mf_volume_change(chan, volume):
    assert 0 <= chan < 16
    assert 0 <= volume < 256
    return mf_delta(0) + [chan + MIDI_CONTROLLER_CHANGE, MIDI_CONTROLLER_VOLUME, volume]

def mf_note_on(delta, chan, note, vel):
    assert 0 <= chan < 16
    return mf_delta(delta) + [chan+MIDI_NOTE_ON, note, vel]
def mf_note_off(delta, chan, note, vel):
    assert 0 <= chan < 16
    return mf_delta(delta) + [chan+MIDI_NOTE_OFF, note, vel]
def mf_end_of_track():
    return [0x0, 0xff, 0x2f, 0x00]

def write_vect(f, v):
    for c in v:
        assert isinstance(c, int) and 0 <= c < 256
        f.write(chr(c))

class MThd:
    PPQN = 96
    def __init__(self, f):
        v = []
        # MIDI file format:
        # 0: the file contains one single track containing midi data on
        #    possibly all 16 midi channels
        # 1: the file contains one or more simultaneous (ie, all start
        #    from an assumed time of 0) tracks, perhaps each on a single
        #    midi channel.
        # 2: the file contains one or more sequentially independant
        #    single-track patterns.
        # We will use format 1.
        v = v + mf_int16(1)
        # How many tracks are stored in the file.
        v = v + mf_int16(1)
        # Wow many Pulses (i.e. clocks) Per Quarter Note resolution
        # the time-stamps are based upon.
        v = v + mf_int16(MThd.PPQN)
        f.write("MThd")
        write_int32(f, len(v)) #chunk len
        write_vect(f, v)

