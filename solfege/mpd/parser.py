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
r"""
REMEMBER: down is positive, up is negative.

All voices begin at the beginning of the staff. It is
not possible to split a voice in two like in Lilypond.

The parser will not handle fis and f in the same octave on one stem.

Rules:
 * It can be different timesignatures in different staffs.
 * \key has to come before \time

The parser does not care if you have correct number of notes in a bar.
To get bar lines you have to insert a '|'
"""

import logging

from solfege.mpd.duration import Duration
from solfege.mpd.lexer import Lexer
from solfege.mpd.musicalpitch import MusicalPitch, InvalidNotenameException
from solfege.mpd.rat import Rat
from solfege.mpd import const
from solfege.mpd import _exceptions
from solfege.mpd import elems

class ParseError(_exceptions.MpdException):
    def __init__(self, msg, lexer):
        _exceptions.MpdException.__init__(self, msg)
        self.m_lineno, self.m_linepos1, self.m_linepos2 = lexer.get_error_location()

def musicalpitch_relative(first, second):
    """
    think:  \relative c'{ first second }
    Tritone handling is the same as GNU Lilypond

    I placed here instead of in MusicalPitch since it is only used
    once in parse_to_score_object and I don't think anyone need this
    in MusicalPitch.
    """
    assert isinstance(first, MusicalPitch)
    assert isinstance(second, MusicalPitch)
    n1 = second.clone()
    n1.m_octave_i = first.m_octave_i
    n2 = n1.clone()
    if n1 < first:
        n2.m_octave_i += 1
    else:
        n1.m_octave_i -= 1
    if n2.steps() - first.steps() < first.steps() - n1.steps():
        # we go  up
        n2.m_octave_i += second.m_octave_i
        return n2
    else:
        # we go down
        n1.m_octave_i += second.m_octave_i
        return n1


class TimeSignature:
    def __init__(self, num, den):
        self.m_num = num
        self.m_den = den


def parse_to_score_object(music):
    lexer = Lexer(music)
    relative_mode = None
    relto = None
    transpose_pitch = None
    TOPLEVEL = 1#'toplevel'
    NOTES = 2#'notes'
    START_OF_CHORD = 3#'start-of-chord'
    CHORD = 4#'chord'
    context = TOPLEVEL
    score = elems.Score()
    chord_duration = None
    cur_duration = Duration(4, 0)
    tie_is_in_the_air = 0
    beam = None
    # None when not parsing notes in a tuplet. Item 0 is the ration and 1.. is the notes
    times = None
    cur_staff = None
    # This variable is set to the duration of the pickup bar from we parse
    # \partial nn until the bar has been created.
    partial = None
    for toc, toc_data in lexer:
        try:
            if toc_data.m_duration:
                cur_duration = toc_data.m_duration.clone()
        except AttributeError:
            pass
        if toc == Lexer.STAFF:
            assert context == TOPLEVEL
            cur_staff = score.add_staff(elems.Staff)
            cur_voice = cur_staff.m_voices[-1]
            stem_dir = const.BOTH
            tuplet_dir = const.BOTH
            relative_mode = None
            timepos = Rat(0)
            last_pos = timepos
        elif toc == Lexer.RHYTHMSTAFF:
            assert context == TOPLEVEL
            cur_staff = score.add_staff(elems.RhythmStaff)
            cur_voice = cur_staff.m_voices[-1]
            stem_dir = const.BOTH
            tuplet_dir = const.BOTH
            relative_mode = None
            timepos = Rat(0)
            last_pos = timepos
        elif toc == Lexer.VOICE:
            if not cur_staff:
                raise ParseError("Don't use \\addvoice before \\staff", lexer)
            relative_mode = None
            timepos = Rat(0)
            cur_voice = cur_staff.add_voice()
        elif toc == Lexer.RELATIVE:
            assert not relative_mode
            relative_mode = 1
            relto = toc_data
        elif toc == Lexer.TRANSPOSE:
            transpose_pitch = toc_data
        elif toc == Lexer.PARTIAL:
            partial = toc_data
        elif toc == Lexer.TIME:
            if not cur_staff:
                raise ParseError(u"\\time can not be used before \\staff", lexer)
            # FIXME
            # Also now, we only allow the first voice to change time signatures
            if cur_staff.m_voices.index(cur_voice) != 0:
                raise ParseError(u"only timesig in first voice", lexer)
            # FIXME: we are stricter with time signatures that both solfege 3.16
            # and LilyPond
            if not cur_voice.is_bar_full():
                raise ParseError(u"timesig change only when bar is full!", lexer)
            if partial:
                score.add_partial_bar(partial, toc_data)
                partial = None
            else:
                score.add_bar(toc_data)
        elif toc == Lexer.KEY:
            p = MusicalPitch.new_from_notename(toc_data[0])
            if transpose_pitch:
                p.transpose_by_musicalpitch(transpose_pitch)
            k = (p.get_notename(), toc_data[1])
            if not cur_staff:
                raise ParseError(u"\\key can not be used before \\staff", lexer)
            cur_staff.set_key_signature(k, timepos)
        elif toc == Lexer.TIMES:
            if not times:
                times = [toc_data]
            else:
                raise ParseError(r"\times nn/nn does not nest", lexer)
        elif toc == Lexer.CLEF:
            try:
                cur_staff.set_clef(toc_data, timepos)
            except elems.UnknownClefException, e:
                e.m_lineno, e.m_linepos1, e.m_linepos2 = lexer.get_error_location()
                raise
        elif toc == '|':
            if timepos != score.get_bar_at(last_pos).end():
                logging.warning("Bar check failed at %s", timepos)
        elif toc == '{':
            if (context == TOPLEVEL):
                context = NOTES
                #if not cur_staff.m_coldict[Rat(0, 1)].m_keysignature:
                # FIXME dont understand
                if transpose_pitch:
                    k = (transpose_pitch.get_notename(), 'major')
                else:
                    k = ('c', 'major')
                cur_voice.set_key_signature(k)
            else:
                raise ParseError("Token '{' not allowed here.", lexer)
        elif toc == '<':
            if context == NOTES:
                context = START_OF_CHORD
            else:
                raise ParseError("Token '<' not allowed here.", lexer)
        elif toc == '>':
            if context == CHORD:
                if tie_is_in_the_air:
                    # The 3.16-parser only handles ties between whole chords, not
                    # single tones of a chord.
                    if tie_is_in_the_air:
                        for last_note in cur_voice.m_tdict[last_pos]['elem']:
                            for cur_note in cur_voice.m_tdict[timepos]['elem']:
                                if last_note.m_musicalpitch.get_octave_notename() == cur_note.m_musicalpitch.get_octave_notename():
                                    cur_voice.tie([last_note, cur_note])
                    tie_is_in_the_air = 0
                last_pos = timepos
                timepos = timepos + chord_duration.get_rat_value()
                chord_duration = None
                relto = relto_backup;
                relto_backup = None
                context = NOTES
            else:
                raise ParseError("Token '>' not allowed here.", lexer)
        elif toc == '}':
            if context == NOTES:
                if times:
                    cur_voice.tuplet(times[0], tuplet_dir, times[1:])
                    times = None
                    cur_duration.m_tuplet = Rat(1, 1)
                else:
                    context = TOPLEVEL
            else:
                raise ParseError("Token '}' not allowed here.", lexer)
        elif toc == '[':
            beam = []
        elif toc == ']':
            cur_voice.beam(beam)
            beam = None
        elif toc == '~':
            tie_is_in_the_air = 1
        elif toc == Lexer.NOTE and (context in [NOTES, CHORD, START_OF_CHORD]):
            # FIXME check if toc_data.m_duration will ever be undefined.
            # If not we can do this:   if not toc_data.m_duration:
            if not getattr(toc_data, 'm_duration', None):
                toc_data.m_duration = cur_duration.clone()
            if times:
                toc_data.m_duration.m_tuplet = times[0].clone()
            if relative_mode:
                toc_data.m_pitch = musicalpitch_relative(
                                          relto, toc_data.m_pitch)
                relto = toc_data.m_pitch.clone()
            if transpose_pitch:
                toc_data.transpose(transpose_pitch)
            if partial:
                score.add_partial_bar(partial, None)
                partial = None
            if context == NOTES:
                note = elems.Note(toc_data.m_pitch, toc_data.m_duration)
                try:
                    cur_voice.append(note, stem_dir)
                except elems.Voice.BarFullException, e:
                    raise ParseError(unicode(e), lexer)
                if beam is not None:
                    beam.append(note)
                if times is not None:
                    times.append(note)
                # The 3.16-parser only handles ties between whole chords, not
                # single tones of a chord.
                if tie_is_in_the_air:
                    for note in cur_voice.m_tdict[last_pos]['elem']:
                        if [n for n in cur_voice.m_tdict[timepos]['elem'] if n.m_musicalpitch.get_octave_notename() == note.m_musicalpitch.get_octave_notename()]:
                            cur_voice.tie([note, n])
                    tie_is_in_the_air = 0
                last_pos = timepos
                timepos = timepos + toc_data.m_duration.get_rat_value()
            elif context == START_OF_CHORD:
                cur_voice.append(elems.Note(toc_data.m_pitch, toc_data.m_duration), stem_dir)
                relto_backup = relto
                chord_duration = toc_data.m_duration
                context = CHORD
            elif context == CHORD:
                cur_voice.add_to(timepos, elems.Note(toc_data.m_pitch, toc_data.m_duration))
        elif toc == Lexer.SKIP and context == NOTES:
            if toc_data.m_duration:
                cur_duration = toc_data.m_duration.clone()
            else:
                toc_data.m_duration = cur_duration.clone()
            skip = elems.Skip(toc_data.m_duration)
            cur_voice.append(skip)
            last_pos = timepos
            timepos = timepos + toc_data.m_duration.get_rat_value()
        elif toc == Lexer.REST and context == NOTES:
            if toc_data.m_duration:
                cur_duration = toc_data.m_duration.clone()
            else:
                toc_data.m_duration = cur_duration.clone()
            rest = elems.Rest(toc_data.m_duration)
            cur_voice.append(rest)
            last_pos = timepos
            timepos += toc_data.m_duration.get_rat_value()
        elif toc == Lexer.STEMDIR:
            stem_dir = toc_data
        elif toc == Lexer.TUPLETDIR:
            tuplet_dir = toc_data
        else:
            raise ParseError(toc, lexer)
    return score




def validate_only_notenames(s):
    """
    Return (None, None, None) if the string s is only notenames
    (pitch and duration). No ties or other tokens are allowed.
    """
    lex = Lexer(s)
    try:
        for toc, toc_data in lex:
            if not toc:
                break
            if toc != lex.NOTE:
                return lex.get_error_location()
    except InvalidNotenameException:
        return lex.get_error_location()
    return None, None, None
