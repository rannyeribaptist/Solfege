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
import os
from solfege.soundcard import solfege_c_midi
from solfege.soundcard.soundcardexceptions import SyscallException, SeqNoSynthsException

class AbstractSynth:
    NUM_CHANNELS = 16
    def __init__(self, device, devnum, verbose_init):
        self.m_type_major = "OSS"
        self.m_device = device
        self.m_devnum = devnum
        self.open_device()
        if verbose_init:
            self.print_soundcard_info()
    def open_device(self):
        # the app will crash if I rmmod awe_awe
        solfege_c_midi.cvar.seqfd = os.open(self.m_device, os.O_WRONLY, 0)
        if not solfege_c_midi.sndctl_seq_reset():
            # we cannot use self.close() because that function will try
            # to call sndctl_seq_reset()
            os.close(solfege_c_midi.cvar.seqfd)
            solfege_c_midi.cvar.seqfd = -1
            raise SyscallException("While trying to open the device %s\nioctl(seqfd, SNDCTL_SEQ_RESET) failed" % self.m_device, solfege_c_midi.cvar.errno)
        i = solfege_c_midi.sndctl_seq_nrsynths()
        if i == -1:
            self.close()
            raise SyscallException("While trying to open the device %s\nioctl(seqfd, SNDCTL_SEQ_NRSYNTHS, &n) failed" % self.m_device, solfege_c_midi.cvar.errno)
        if self.m_devnum >= i:
            if i == 0:
                self.close()
                raise SeqNoSynthsException(self.m_device)
            else:
                self.m_devnum = i - 1
        self.m_num_voices = solfege_c_midi.get_synth_nr_voices(self.m_devnum)
        if self.m_num_voices == -1:
            self.close()
            raise SyscallException("While trying to open the device %s\nioctl(seqfd, SNDCTL_SYNTH_INFO, &si) failed" % self.m_device, solfege_c_midi.cvar.errno)
    def print_soundcard_info(self):
        print "Devicefile:", self.m_device
        print "The following sound devices has been found:"
        assert solfege_c_midi.cvar.seqfd
        nrsynths = solfege_c_midi.sndctl_seq_nrsynths()
        for x in range(nrsynths):
            print "%i: %s" % (x, solfege_c_midi.get_synth_name(x))
        print "--- using %s ---" % solfege_c_midi.get_synth_name(self.m_devnum)
    def close(self):
        if solfege_c_midi.cvar.seqfd != -1:
            solfege_c_midi.sndctl_seq_reset()
            os.close(solfege_c_midi.cvar.seqfd)
            solfege_c_midi.cvar.seqfd = -1
    def stop(self):
        solfege_c_midi.sndctl_seq_reset()

