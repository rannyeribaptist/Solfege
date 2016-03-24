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

import math
import random
import re

from solfege import cfg
from solfege import mpd
from solfege import soundcard

from solfege.mpd.const import DEFAULT_VELOCITY

def mangle_email(email):
    email = email.replace("@", " ,, ")
    email = email.replace(".", " ,, ")
    return email


def int_to_intervalname(i, shortname=None, updown=None):
    if shortname:
        n = mpd.interval.short_name[abs(i)]
    else:
        n = mpd.Interval.new_from_int(abs(i)).get_name()
    if updown:
        if i > 0:
            n = "%s%s" % (n, u"\u2191")
        elif i < 0:
            n = "%s%s" % (n, u"\u2193")
    return n


class NoPossibleIntervals(Exception):
    pass


def random_interval(tonika, lowest, highest, irange):
    """
    tonika   MusicalPitch
    lowest   int with the MIDI integer value of the lowest tone
    highest  int with the MIDI interger value of the higest tone
    irange   list of integer values representing the intervals to choose from

    Return an int representing the interval.
    Return None if it is not possible to create an interval.
    """
    tonika = tonika.semitone_pitch()
    lowest = mpd.notename_to_int(lowest)
    highest = mpd.notename_to_int(highest)
    assert lowest <= highest
    assert isinstance(irange, list)
    v = []
    for i in irange:
        if lowest <= tonika + i <= highest:
            v.append(i)
    if not v:
        return None
    return random.choice(v)


def random_tonika_and_interval(lowest, highest, irange):
    """
    Return a tuple (tonika, interval) of types (MusicalPitch, int).

    lowest   notename string
    highest  notename string
    irange   list of integers representing intervals. 1 is minor
             second up, -2 is major second down

    Raise NoPossibleIntervals if we cannot create an interval within the
    given range of tones.
    """
    assert isinstance(lowest, basestring)
    assert isinstance(highest, basestring)
    lowest = mpd.notename_to_int(lowest)
    highest = mpd.notename_to_int(highest)
    assert lowest <= highest
    assert isinstance(irange, list)
    # first we find out what is the largest interval we can have
    i = highest - lowest
    # then filter irange to only use intervals that fit within that range
    v = [x for x in irange if abs(x) <= i]
    if not v:
        raise NoPossibleIntervals(_("No random interval can be selected within the allowed range of tones."))
    interval = random.choice(v)
    # then, using that interval, make a list of possible tonikas
    tl = []
    for t in range(lowest, highest + 1):
        if lowest <= t + interval <= highest:
            tl.append(t)
    tonika = mpd.MusicalPitch.new_from_int(random.choice(tl))
    return tonika, interval


def random_interval_in_key(first, lowest, highest, irange, tonic, keytype):
    """
    Return an int representing the interval.
    Return None if it is not possible to create an interval.
    Arguments:
        first   The MusicalPitch of the first tone
        lowest
        highest integer representing the MIDI pitch of the tone
        tonic   MusicalPitch, the key the tones should be taken from
        keytype "major", "natural-minor" or "harmonic-minor"
    """
    assert isinstance(lowest, basestring)
    assert isinstance(highest, basestring)
    lowest = mpd.notename_to_int(lowest)
    highest = mpd.notename_to_int(highest)
    assert isinstance(first, mpd.MusicalPitch)
    tones = pitches_in_key(tonic, keytype, lowest, highest)
    intervals = []
    for i in irange:
        if (first + i).semitone_pitch() in tones:
            intervals.append(i)
    if intervals:
        return random.choice(intervals)


def random_tonic_and_interval_in_key(lowest, highest, irange, tonic, keytype):
    """
    Find a random interval that belongs to a key specified by the
    arguments tonic and keytype.
    Return a tuple (MusicalPitch, int) where the musical pitch is the
    lowest tone and the integer is the size of the interval.
    Arguments:
        lowest  the name of the lowest possible tone, as a unicode string
        highest the name of the highest possible tone, as a unicode string
        tonika  MusicalPitch, the key the tones should be taken from
        keytype "major", "natural-minor" or "harmonic-minor"

    It is not possible to make this function truly random, since it
    is possible that some of the keys in irange does not exist in a
    given keytype. There are no minor seconds in a whole tone scale.

    I descided that it is better to be less random than giving the user
    lots of error messages and complaining about bad configuration.
    """
    lowest = mpd.notename_to_int(lowest)
    highest = mpd.notename_to_int(highest)
    # We allow str because it simplifies writing the tests
    if isinstance(tonic, str):
        tonic = mpd.MusicalPitch.new_from_notename(tonic)

    # Make a list of all MIDI pitches that belong to the key that
    # are with the range of tones we can use
    all_tones = pitches_in_key(tonic, keytype, lowest, highest)

    # Then make a list of which of teh intervals in irange that
    # can be played with the available tones
    possible_intervals = []
    for i in irange:
        for tone in all_tones:
            if tone + i in all_tones:
                possible_intervals.append(i)
                break

    if not possible_intervals:
        raise NoPossibleIntervals(_("None of the selected intervals can be created in the selected key."))

    interval = random.choice(possible_intervals)
    solutions = []
    for tone in all_tones:
        if (tone + interval in all_tones
            and lowest <= tone <= highest
            and lowest <= tone + interval <= highest):
                solutions.append(tone)
    return (mpd.MusicalPitch.new_from_int(random.choice(solutions)), interval)

key_data = {
    'major': {'name': _('Major'),
              'pitches': (0, 2, 4, 5, 7, 9, 11)},
    'natural-minor': {'name': _('Natural Minor'),
                      'pitches': (0, 2, 3, 5, 7, 8, 10)},
    'harmonic-minor': {'name': _('Harmonic Minor'),
                       'pitches': (0, 2, 3, 5, 7, 8, 10)},
    'whole-tone': {'name': _('Whole Tone'),
                   'pitches': (0, 2, 4, 6, 8, 10)},
}

def pitches_in_key(tonic, keytype, lowest, highest):
    """
    Return a set of the pitches (int values corresponding to
    the MIDI spec and MusicalPitch.semitone_pitch())
    """
    tones = set()
    p = tonic.pitch_class()
    for octave in range(-1, 12):
        for t in key_data[keytype]['pitches']:
            if lowest <= p + octave * 12 + t <= highest:
                tones.add(p + octave * 12 + t)
    return tones


def un_escape_url_string(s):
    r = re.compile("(%([0-9A-F][0-9A-F]))")
    m = r.search(s)
    def f(m):
        return chr(eval("0x%s" % m.groups()[1]))
    return r.sub(f, s)

def _str_to_dict(s):
    D = {}
    if s:
        V = s.split(";")
        for e in V:
            n, v = e.split("=")
            D[n.strip()] = v.strip()
    for k in D:
        D[k] = un_escape_url_string(D[k])
    return D

def freq_to_notename_cent(freq):
    e = 440.0
    if e > freq:
        while e > freq:
            e = e / 2
    else:
        while e < freq/2:
            e = e * 2
    d = freq / e
    v = 12 * math.log(d) / math.log(2)
    i = int(v)
    cent = (v-i) * 100
    n = ('a', 'ais', 'b', 'c', 'cis', 'd', 'dis', 'e', 'f', 'fis', 'g', 'gis')
    if cent > 50:
        return n[(i+1) % 12], cent-100
    return n[int(v)], (v-int(v)) * 100

def compare_version_strings(A, B):
    """
    Works with version strings like 1, 1.0, 1.1.3, 1.4.3.2
    Returns:
        -1 if A < B
         0 if A == B
         1 if A > B
    """
    if A == B == "":
        return 0
    elif A == "":
        return -1
    elif B == "":
        return 1
    av = map(lambda s: int(s), A.split("."))
    bv = map(lambda s: int(s), B.split("."))
    x = 0
    while len(av) > x < len(bv):
        if av[x] > bv[x]:
            return 1
        elif av[x] < bv[x]:
            return -1
        x = x + 1
    if len(av) > len(bv):
        return 1
    elif len(av) < len(bv):
        return -1
    return 0


def string_get_line_at(s, idx):
    """
    Return the whole line, excluding new-line characters, that
    the character at idx is part of. It the char at idx is a new-line
    character, then we consider this char the last character of the line.
    """
    start = idx
    while start > 0 and s[start -1] != "\n":
        start -= 1
    end = idx
    if s[end] != "\n":
        while end < len(s) -1 and s[end + 1] != "\n":
            end += 1
    return s[start:end+1].strip("\n")

def new_track():
    t1 = mpd.Track()
    t1.set_bpm(cfg.get_int('config/default_bpm'))
    t1.set_volume(cfg.get_int('config/preferred_instrument_volume'))
    t1.set_patch(cfg.get_int('config/preferred_instrument'))
    return t1

def new_percussion_track():
    t1 = mpd.PercussionTrack()
    t1.set_bpm(cfg.get_int('config/default_bpm'))
    t1.set_volume(cfg.get_int('config/preferred_instrument_volume'))
    return t1

def new_2_tracks():
    if cfg.get_bool('config/override_default_instrument'):
        instr_low = cfg.get_int('config/lowest_instrument')
        instr_low_volume = cfg.get_int('config/lowest_instrument_volume')
        instr_high = cfg.get_int('config/highest_instrument')
        instr_high_volume = cfg.get_int('config/highest_instrument_volume')
    else:
        instr_low = instr_high = cfg.get_int('config/preferred_instrument')
        instr_low_volume = instr_high_volume = cfg.get_int('config/preferred_instrument_volume')
    t1 = mpd.Track()
    t1.set_bpm(cfg.get_int('config/default_bpm'))
    t1.set_patch(instr_low)
    t1.set_volume(instr_low_volume)
    t2 = mpd.Track()
    t2.set_patch(instr_high)
    t2.set_volume(instr_high_volume)
    return t1, t2

def new_3_tracks():
    if cfg.get_bool('config/override_default_instrument'):
        instr_low = cfg.get_int('config/lowest_instrument')
        instr_low_volume = cfg.get_int('config/lowest_instrument_volume')
        instr_middle = cfg.get_int('config/middle_instrument')
        instr_middle_volume = cfg.get_int('config/middle_instrument_volume')
        instr_high = cfg.get_int('config/highest_instrument')
        instr_high_volume = cfg.get_int('config/highest_instrument_volume')
    else:
        instr_low = instr_middle = instr_high = cfg.get_int('config/preferred_instrument')
        instr_low_volume = instr_middle_volume = instr_high_volume = cfg.get_int('config/preferred_instrument_volume')
    t1 = mpd.Track()
    t1.set_bpm(cfg.get_int('config/default_bpm'))
    t1.set_patch(instr_low)
    t1.set_volume(instr_low_volume)
    t2 = mpd.Track()
    t2.set_patch(instr_middle)
    t2.set_volume(instr_middle_volume)
    t3 = mpd.Track()
    t3.set_patch(instr_high)
    t3.set_volume(instr_high_volume)
    return t1, t2, t3

def play_note(notelen, pitch):
    t = new_track()
    t.note(notelen, pitch, DEFAULT_VELOCITY)
    soundcard.synth.play_track(t)

def play_perc(notelen, pitch):
    t = new_percussion_track()
    t.note(notelen, pitch)
    soundcard.synth.play_track(t)

def play_music(music, tempo, patch, volume, start=None, end=None):
    if type(tempo) == type(0):
        bpm = tempo
        nl = 4
    else:
        bpm, nl = tempo
    score = mpd.parser.parse_to_score_object(music)
    tracklist = mpd.score_to_tracks(score, start, end)
    tracklist[0].prepend_bpm(bpm, nl)
    [track.prepend_patch(patch) for track in tracklist]
    [track.prepend_volume(volume) for track in tracklist]
    soundcard.synth.play_track(*tracklist)

def play_music3(music, tempo, instrument, start=None, end=None):
    """
    Either a tuple (patch, velocity) or a tuple of 6:
    (patch1, velocity1, p2, v2, p3, v3)
    """
    if len(instrument) == 2:
        instrument = instrument * 3
    tracklist = mpd.music_to_tracklist(music, start, end)
    tracklist[0].prepend_patch(instrument[4])
    tracklist[0].prepend_volume(instrument[5])
    a, b = tempo
    # FIXME the bpm api is wrong. We set the tempo to one track, and it works for all.
    tracklist[0].prepend_bpm(a, b)
    for track in tracklist[:-1][1:]:
        track.prepend_patch(instrument[2])
        track.prepend_volume(instrument[3])
    tracklist[-1].prepend_patch(instrument[0])
    tracklist[-1].prepend_volume(instrument[1])
    soundcard.synth.play_track(*tracklist)

