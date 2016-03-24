# GNU Solfege - free ear training software
# Copyright (C) 2000, 2001, 2002, 2003, 2004, 2007, 2008, 2011  Tom Cato Amundsen
# Copyright (C) 2001 Joe Lee
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
import logging
from solfege.soundcard.synth_common import SynthCommon
from solfege.soundcard import winmidi
from solfege.mpd.track import MidiEventStream

class WinSynth(SynthCommon):
    NUM_CHANNELS = 16
    def __init__(self, devnum, verbose_init):
        SynthCommon.__init__(self)
        try:
            self.__driver = winmidi.Winmidi(devnum)
        except RuntimeError, e:
            if not winmidi.output_devices():
                e.args = e.args + (_("No MIDI output devices available."),)
                raise
            devnum = 0
            logging.error("WinSynth.__init__: No MIDI output devices available on %i. Retrying with devNum 0", devnum)
            self.__driver = winmidi.Winmidi(devnum)
        self.m_type_major = "win32" #FIXME
        self.m_devnum = devnum
        if verbose_init:
            logging.debug("Solfege will use Windows multimedia output.")
    def close(self):
        self.__driver = None
    def stop(self):
        # dummy function
        pass
    def play_track(self, *tracks):
        self.play_midieventstream(MidiEventStream(*tracks))
    def play_midieventstream(self, midieventstream):
        if self.__driver is None:
            raise RuntimeError, "Attempted to use synth after closing."
        self.__driver.reset(self.m_devnum)
        # bigger magic plays slower
        magic = 1440000
        self.__driver.set_tempo(int(magic * 4 / 60))
        v = []
        notelen = 0
        for e in midieventstream:
            if e[0] == midieventstream.TEMPO:
                self.__driver.set_tempo(int(magic * e[2] / e[1]))
            elif e[0] == midieventstream.NOTELEN_TIME:
                notelen = e[1]
            elif e[0] == midieventstream.NOTE_ON:
                self.__driver.note_on(int(1000 * notelen), e[1], e[2], e[3])
                notelen = 0
            elif e[0] == midieventstream.NOTE_OFF:
                self.__driver.note_off(int(1000 * notelen), e[1], e[2], e[3])
                notelen = 0
            elif e[0] == midieventstream.SET_PATCH:
                self.__driver.program_change(e[1], e[2])
                # Give the synth a little time to process the program change
                self.__driver.note_off(100, 0, 0, 0)
            elif e[0] == midieventstream.BENDER:
                logging.debug("ugh todo: seq_bender for play_with_drvmidi")
                #m.seq_bender(DEV, e[1], e[2])
            else:
                pass
        self.__driver.play()
