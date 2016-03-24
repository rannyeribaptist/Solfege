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
"""
Only utility functions and classes that are private to the mpd module
should go into this file.
"""

import re
from solfege.mpd.musicalpitch import MusicalPitch

def int_to_octave_notename(i):
    return MusicalPitch.new_from_int(i).get_octave_notename()

def int_to_user_octave_notename(i):
    return MusicalPitch.new_from_int(i).get_user_octave_notename()

def notename_to_int(n):
    return MusicalPitch.new_from_notename(n).semitone_pitch()


def key_to_accidentals(key):
    i = ['aeses', 'eeses', 'beses', 'fes', 'ces', 'ges', 'des', 'aes',
         'ees', 'bes', 'f', 'c', 'g', 'd', 'a', 'e', 'b', 'fis', 'cis',
         'gis', 'dis', 'ais', 'eis', 'bis'].index(key[0])-11
    if key[1] == 'minor':
        i = i - 3
    if i > 0:
        r = ['fis', 'cis', 'gis', 'dis', 'ais', 'eis',
             'bis', 'fis', 'cis', 'gis', 'dis'][:i]
        m = 'is'
    elif i < 0:
        r = ['bes', 'ees', 'aes', 'des', 'ges', 'ces',
             'fes', 'bes', 'ees', 'aes', 'des'][:-i]
        m = 'es'
    else:
        r = []
    retval = []
    for a in r:
        if a not in retval:
            retval.append(a)
        else:
            del retval[retval.index(a)]
            retval.append(a+m)
    return retval


def find_possible_first_note(music):
    """
    Return a tuple of 2 integer locating what we believe is the first
    pitch (but do not include the duration).

    Return the location of the text we don't understand if we are not able
    to parse the music.
    """
    i = 0
    # FIXME regexes are modified copies from the mpd Lexer. Try to reuse
    # code in the future.
    re_white = re.compile(r"\s+")
    re_clef = re.compile(r"\\clef\s+(\w*)", re.UNICODE)
    re_clef_quoted = re.compile(r"\\clef\s+\"([A-Za-z1-9]+[_^1-9]*)\"", re.UNICODE)
    re_time = re.compile(r"\\time\s+(\d+)\s*/\s*(\d+)", re.UNICODE)
    re_times = re.compile(r"\\times\s+(\d+)\s*/\s*(\d+)\s*{", re.UNICODE)
    re_key = re.compile(r"\\key\s+([a-z]+)\s*\\(major|minor)", re.UNICODE)
    re_note = re.compile("(?P<beamstart>(\[\s*)?)(?P<chordstart>(\<\s*)?)(?P<pitchname>[a-zA-Z]+[',]*)(\d+\.*)?")
    i = 0
    re_list = re_white, re_clef_quoted, re_clef, re_key, re_times, re_time, re_note
    while 1:
        for r in re_list:
            m = r.match(music[i:])
            if m:
                if r != re_note:
                    i += m.end()
                    break
                elif r == re_note:
                    assert m
                    i += len(m.group("beamstart"))
                    i += len(m.group("chordstart"))
                    return i, i + len(m.group('pitchname'))
            elif r == re_list[-1]:
                return i, i+1


