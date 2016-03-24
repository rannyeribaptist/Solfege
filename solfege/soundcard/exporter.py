# GNU Solfege - free ear training software
# Copyright (C) 2007, 2008, 2011 Tom Cato Amundsen
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
from solfege.mpd.track import MidiEventStream

class MidiExporter(object):
    def __init__(self):
        self.m_filename = None
        self.m_stream_list = []
    def play_track(self, *tracks):
        self.play_midieventstream(MidiEventStream(*tracks))
    def play_midieventstream(self, stream):
        self.m_stream_list.append(stream)
    def start_export(self, filename):
        """
        Call this method if you want to write the next call to play_track
        to write the music to a WAV file instead of playing it.
        """
        assert self.m_filename is None
        self.m_filename = filename
        self.m_stream_list = []
    def end_export(self):
        if self.m_stream_list:
            self.m_stream_list[0].create_midifile(self.m_filename, self.m_stream_list[1:])
            self.m_filename = None
            del self.m_stream_list

