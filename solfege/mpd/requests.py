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
from solfege.mpd.duration import Duration
from solfege.mpd.rat import Rat
from solfege.mpd.musicalpitch import MusicalPitch

class ItHasDuration:
    """
    Base class from RestRequest and MusicalRequest.
    """
    def __init__(self, duration, dots):
        """duration: integer 1 for 1/1 note 4 for 1/4 etc
        """
        if duration:
            self.m_duration = Duration(duration, dots, Rat(1, 1))
        else:
            self.m_duration = None


class RestRequest(ItHasDuration):
    def __init__(self, duration, dots):
        ItHasDuration.__init__(self, duration, dots)
    def __str__(self):
        return "(RestRequest:%s)" % self.m_duration

class SkipRequest(ItHasDuration):
    def __init__(self, duration, dots):
        ItHasDuration.__init__(self, duration, dots)
    def __str__(self):
        return "(SkipRequest:%s)" % self.m_duration


class MusicRequest(ItHasDuration):
    def __init__(self, notename, duration, dots):
        ItHasDuration.__init__(self, duration, dots)
        self.m_pitch = MusicalPitch.new_from_notename(notename)
    def __str__(self):
        return "(Music:%s, %s)" % (self.m_pitch.get_octave_notename(), self.m_duration)
    def transpose(self, P):
        self.m_pitch.transpose_by_musicalpitch(P)

