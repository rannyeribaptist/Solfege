# GNU Solfege - free ear training software
# Copyright (C) 2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2011 Tom Cato Amundsen
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
import tempfile

from solfege.soundcard.synth_common import SynthCommon
from solfege.mpd.track import MidiEventStream
from solfege import soundcard

def ms_win_kill(pid):
    import win32api
    handle = win32api.OpenProcess(1, 0, pid)
    return (0 != win32api.TerminateProcess(handle, 0))

class MidiFileSynth(SynthCommon):
    NUM_CHANNELS = 16
    def __init__(self, verbose_init):
        SynthCommon.__init__(self)
        self.m_type_major = "Midifile"
        self.m_tmpfilename = tempfile.mkstemp(".mid")[1]
        self.error_report_cb = None
        if verbose_init:
            print "Solfege will use an external midiplayer program."
            print "tmpfile:", self.m_tmpfilename
    def close(self):
        try:
            if os.path.exists(self.m_tmpfilename):
                os.remove(self.m_tmpfilename)
        except OSError:
            pass
            # We ignore this error because it seems to be easiest right now.
            # FIXME
    def play_track(self, *tracks):
        self.play_midieventstream(MidiEventStream(*tracks))
    def play_midieventstream(self, midieventstream):
        midieventstream.create_midifile(self.m_tmpfilename)
        soundcard.play_mediafile('midi', self.m_tmpfilename)
    def stop(self):
        self.play_midieventstream(MidiEventStream())

