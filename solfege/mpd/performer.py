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

import operator

from solfege.mpd.rat import Rat
from solfege.mpd.track import Track, PercussionTrack
from solfege.mpd import const
from solfege.mpd import elems

START_NOTE = 'start-note'
STOP_NOTE  = 'stop-note'

class MidiPerformer(object):
    def __init__(self, score):
        self.m_score = score
    def get_all_tpos_keys(self):
        t = set()
        for staff in self.m_score.m_staffs:
            [t.add(timepos) for timepos in staff.get_timeposes()]
        return sorted(t)
    def get_tracks(self, start=None, end=None):
        """
        Return a list of Track and/or PercussionTrack objects needed to play
        the music in self.m_score. If START or END is set, you only part of
        the music will be included in the tracks.
        """
        if start is None and end is not None:
            return self.get_tracks_of(
                [i for i in self.get_all_tpos_keys() if i < end])
        elif start is not None and end is None:
            return self.get_tracks_of(
                [i for i in self.get_all_tpos_keys() if i >= start])
        elif start is None and end is None:
            return self.get_tracks_of(self.get_all_tpos_keys())
        else:
            assert start is not None and end is not None
            return self.get_tracks_of(
                [i for i in self.get_all_tpos_keys() if start <= i < end])
    def get_event_dict(self, voice, kv):
        """
        Return a dict that tell us where every note in the voice starts
        and stops. The key is a Rat, and the values are a list of tuples.
        Each tuple has thee elements
        (id, 'start|stop-note', midiint)
        """
        ################
        D = {}
        i = 2
        for idx, timepos in enumerate(kv):
            if timepos in voice.m_tdict:
                if not isinstance(voice.m_tdict[timepos]['elem'][0], elems.Note):
                    continue
                for n in sorted(voice.m_tdict[timepos]['elem'],
                        key=operator.attrgetter('m_musicalpitch')):
                    if timepos not in D:
                        D[timepos] = []
                    stop_pos = timepos + n.m_duration.get_rat_value()
                    if stop_pos not in D:
                        D[stop_pos] = []
                    if n.m_tieinfo in ('end', 'go'):
                        for idx, row in enumerate(D[timepos]):
                            if row[2] == int(n.m_musicalpitch):
                                del D[timepos][idx]
                                if not D[timepos]:
                                    del D[timepos]
                                break
                        D[stop_pos].append((i, STOP_NOTE, n.m_musicalpitch.semitone_pitch()))
                    else:
                        D[timepos].append((i, START_NOTE, n.m_musicalpitch.semitone_pitch()))
                        D[stop_pos].append((i, STOP_NOTE, n.m_musicalpitch.semitone_pitch()))
                    i = i + 1
        return D
    def generate_track_for_voice(self, voice, kv, tracktype):
        D = self.get_event_dict(voice, kv)
        keys = D.keys()
        keys.sort()
        prev_time = Rat(0)
        ms = tracktype()
        for k in keys:
            delta = None
            if k != Rat(0, 1):
                delta = k-prev_time
            prev_time = k
            for e in D[k]:
                if e[1] == START_NOTE:
                    if delta:
                        ms.notelen_time(delta)
                    ms.start_note(e[2], const.DEFAULT_VELOCITY)
                elif e[1] == STOP_NOTE:
                    if delta:
                        ms.notelen_time(delta)
                    ms.stop_note(e[2], const.DEFAULT_VELOCITY)
                delta = None
        return ms
    def get_tracks_of(self, kv):
        """
        Create and return a list of Tracks
        """
        tracks = []
        for staff in self.m_score.m_staffs:
            for voice in staff.m_voices:
                tracks.append(
                    self.generate_track_for_voice(voice, kv,
                        PercussionTrack if staff.__class__ == elems.RhythmStaff else Track))
        return tracks

def score_to_tracks(score, start=None, end=None):
    return MidiPerformer(score).get_tracks(start, end)

