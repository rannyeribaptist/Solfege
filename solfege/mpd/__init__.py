# GNU Solfege - free ear training software
# Copyright (C) 2000, 2001, 2002, 2003, 2004, 2006, 2007, 2008, 2011  Tom Cato Amundsen
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
"""
FIXME update.
In addition to the names in this file, only this is public in
the mpd module:

  Classes:
	MusicalPitch
	MusicDisplayer
"""


LOWEST_NOTENAME = "c,,,,"
HIGHEST_NOTENAME = "g''''''"

from solfege.mpd.duration import Duration
from solfege.mpd.musicalpitch import MusicalPitch, InvalidNotenameException
from solfege.mpd.interval import Interval
from solfege.mpd.mpdutils import notename_to_int, int_to_octave_notename, int_to_user_octave_notename
from solfege.mpd.parser import parse_to_score_object
from solfege.mpd.rat import Rat
from solfege.mpd.track import Track, PercussionTrack
from solfege.mpd._exceptions import MpdException
from solfege.mpd.performer import score_to_tracks
try:
    # solfege.app_running is set in solfege/startup.py, but will be
    # unset if run from some of the build scripts. This way we can
    # build without having a X display.
    import solfege
    if solfege.app_running:
        from solfege.mpd.rhythmwidget import RhythmWidget, RhythmWidgetController
        from solfege.mpd.musicdisplayer import MusicDisplayer
except AttributeError:
    pass
finally:
    del solfege

def music_to_tracklist(music, start=None, end=None):
    """
    return a list of tracks, where track[0] use only channel 0,
    track[1] only use channel 1 etc.
    """
    return score_to_tracks(parse_to_score_object(music), start, end)

def music_to_track(music, start=None, end=None):
    tracklist = score_to_tracks(parse_to_score_object(music), start, end)
    track = tracklist[0]
    for x in range(1, len(tracklist)):
        track.merge_with(tracklist[x])
    return track


##################
# midi functions #
##################

def transpose_notename(n, t):
    assert isinstance(n, basestring)
    assert isinstance(t, int)
    # 1 2 sekund
    # 3 4 ters
    # 5 6 kvart
    # 7   kvint
    # 8 9 sekst
    # 10 11 septim
    return int_to_octave_notename(notename_to_int(n) + t)

def compare_notenames(n1, n2):
    return notename_to_int(n1) - notename_to_int(n2)

def select_clef(s):
    """
    argument s is a string with notenames like this: " c e g c' f' g''"
    """
    lowest = HIGHEST_NOTENAME
    highest = LOWEST_NOTENAME
    for n in s.split():
        if compare_notenames(n, lowest) < 0:
            lowest = n
        if compare_notenames(n, highest) > 1:
            highest = n
    if compare_notenames(highest, "c'") < 0:
        return "bass"
    if compare_notenames(lowest, "c'") >= 0:
        return "violin"
    if compare_notenames(highest, "c'") >= compare_notenames("c'", lowest):
        return "violin"
    else:
        return "bass"

