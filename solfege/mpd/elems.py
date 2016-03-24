# vim:set fileencoding=utf-8:
# GNU Solfege - free ear training software
# Copyright (C) 2010, 2011  Tom Cato Amundsen
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

#FIXME: voice1_lowest_ylinepos and stempos in the original parser.py
# give some alignment we need to implement here too.

# FIXME: I think the StemEngraver should take care of shifting of
# noteheads. So I think it should be given the created NoteHeadEngravers
# and then shift the notes.

import copy
import re
import weakref

from solfege.mpd import _exceptions
from solfege.mpd import const
from solfege.mpd.rat import Rat
from solfege.mpd.duration import Duration
from solfege.mpd.musicalpitch import MusicalPitch

#FIXME duplicate of code in Lexer
re_melodic = re.compile(r"""(?x)
                             ((?P<notename>[a-zA-Z]+)
                             (?P<octave>[',]*))
                             (?P<len>[\d]*)
                             (?P<dots>\.*)""", re.UNICODE)

class UnknownClefException(_exceptions.MpdException):
    def __init__(self, clef):
        _exceptions.MpdException.__init__(self)
        self.m_clef = clef
    def __str__(self):
        return "'%s' is not a valid clef. Maybe a bug in your lessonfile?" % self.m_clef

class Clef(object):
    # Use these constants to access the data in clefdata.
    SYM = 0
    # Which staff line should the clef be on lines 1 to 5. 1 is the lowest line
    LINE = 1
    # On which position in the staff is the middle C. 0 is the middle line
    # in the staff. Positive values are up, negative are down.
    POS = 2
    clefdata = {
            'treble': ('G', 2, -6),
            'violin': ('G', 2, -6),
                 'G': ('G', 2, -6),
                'G2': ('G', 2, -6),
            'french': ('G', 1, -8),
            #
            'subbass': ('F', 5, 8),
               'bass': ('F', 4, 6),
                  'F': ('F', 4, 6),
        'varbaritone': ('F', 3, 4),
        #
           'baritone': ('C', 5, 4),
              'tenor': ('C', 4, 2),
               'alto': ('C', 3, 0),
                  'C': ('C', 3, 0),
       'mezzosoprano': ('C', 2, -2),
            'soprano': ('C', 1, -4),
    }
    octaviation_re = re.compile("(?P<name>[A-Za-z1-9]+)(?P<oct>([_^])(8|15))?$")
    def __init__(self, clefname):
        m = self.octaviation_re.match(clefname)
        if not m:
            raise UnknownClefException(clefname)
        if m.group('name') not in self.clefdata:
            raise UnknownClefException(clefname)
        try:
            self.m_octaviation = {'_8': -7, '_15': -14, '^8': 7, '^15': 14,
                             None: 0}[m.group('oct')]
        except KeyError:
            raise UnknownClefException(clefname)
        self.m_name = m.group('name')
    def get_symbol(self):
        return self.clefdata[self.m_name][self.SYM]
    def get_stafflinepos(self):
        return self.clefdata[self.m_name][self.LINE]
    def steps_to_ylinepos(self, steps):
        return 7-self.clefdata[self.m_name][self.POS] - steps + self.m_octaviation
    def an_to_ylinepos(self, an):
        def notename_to_ylinepos(n):
            n = MusicalPitch.new_from_notename(n)
            return self.steps_to_ylinepos(n.steps())
        if an[-2:] == 'es':
            l = 3
            h = -3
        else:
            l = 1
            h = -5
        i = notename_to_ylinepos(an)
        while i > l:
            an = an + "'"
            i =  notename_to_ylinepos(an)
        while i < h:
            an = an + ","
            i = notename_to_ylinepos(an)
        return i

class TimeSignature(object):
    """
    A TimeSignature is not the same as a Rat, because a Rat 4/4 can be
    simplified to 1/1, but time signatures should not. Also a time signature
    will probably know about preferred beaming. 4/4 vs 6/8 for example.
    """
    __hash__ = None
    def __init__(self, a, b):
        self.m_num = a
        self.m_den = b
    def as_rat(self):
        return Rat(self.m_num, self.m_den)
    def __eq__(self, other):
        return self.m_num == other.m_num and self.m_den == other.m_den
    def __ne__(self, other):
        return not self.__eq__(other)
    def __repr__(self):
        return "<TimeSignature %s/%s>" % (self.m_num, self.m_den)

class HasParent(object):
    def __init__(self, parent):
        self.set_parent(parent)
    def set_parent(self, parent):
        if parent:
            self.w_parent = weakref.ref(parent)
            w = self.w_parent
            # FIXME loop instead of ifelse, since the hierarcy might
            # get deeper.
            # FIXME should we allow for the try: clause??
            try:
                if isinstance(w(), Score):
                    self.w_score = w
                elif type(w().w_parent()) == Score:
                    self.w_score = w().w_parent
                else:
                    assert isinstance(w().w_parent().w_parent(), Score)
                    self.w_score = w().w_parent().w_parent
            except AttributeError:
                pass


class MusicElement(object):
    def __init__(self, duration):
        assert isinstance(duration, Duration)
        self.m_duration = duration
    def __repr__(self):
        return unicode(self.__class__)[:-2].replace("<class '", '<') + u" %s at %s>" % (self.m_duration.as_mpd_string(), hex(id(self)))

class Note(MusicElement):
    __hash__ = None
    class Exception(Exception):
        pass
    def __deepcopy__(self, memo):
        n = Note(self.m_musicalpitch.clone(), self.m_duration.clone())
        n.m_tieinfo = self.m_tieinfo
        return n
    def __eq__(self, other):
        assert isinstance(other, Note)
        return (self.m_musicalpitch == other.m_musicalpitch and
                self.m_duration == other.m_duration)
    def __init__(self, musicalpitch, duration):
        MusicElement.__init__(self, duration)
        assert isinstance(musicalpitch, MusicalPitch)
        self.m_musicalpitch = musicalpitch
        self.m_tieinfo = None
    @staticmethod
    def new_from_string(string):
        s = string.strip()
        m = re_melodic.match(s)
        if m.end() < len(s) - 1:
            # FIXME: raise ValueError like rest
            raise Note.Exception("characters left in string", string)
        return Note(
            MusicalPitch.new_from_notename("%s%s" % (m.group('notename'),
                                                     m.group('octave'))),
            Duration.new_from_string("%s%s" % (m.group('len'), m.group('dots')))
        )
    def __repr__(self):
        return unicode(self.__class__)[:-2].replace("<class '", '<') + u" %s%s at %s>" % (self.m_musicalpitch.get_octave_notename(), self.m_duration.as_mpd_string(), hex(id(self)))

class Rest(MusicElement):
    def __init__(self, duration):
        MusicElement.__init__(self, duration)
    def __deepcopy__(self, memo):
        return Rest(self.m_duration.clone())
    @staticmethod
    def new_from_string(string):
        return Rest(Duration.new_from_string(string))

class Skip(MusicElement):
    def __init__(self, duration):
        MusicElement.__init__(self, duration)
    def __deepcopy__(self, memo):
        return Skip(self.m_duration.clone())
    @staticmethod
    def new_from_string(string):
        return Skip(Duration.new_from_string(string))

class Stem(list):
    """
    Every note belongs to a stem, even whole-notes.
    """
    class NotEqualLengthException(Exception):
        """
        Every notehead on a stem must have the same duration.
        """
        pass
    def __init__(self, parent, elemlist, stemdir):
        assert isinstance(elemlist, list)
        assert stemdir in (const.UP, const.DOWN, const.BOTH)
        if [x for x in elemlist if x.m_duration != elemlist[0].m_duration]:
            raise self.NotEqualLengthException()
        list.__init__(self, elemlist)
        self.w_parent = weakref.ref(parent)
        for note in self:
            note.w_parent = weakref.ref(self)
        self.m_stemdir = stemdir
        self.m_beaminfo = None
        self.m_tupletinfo = None
    def __repr__(self):
        return "<Stem %s %s>" % (str(list(self)), self.m_stemdir)


class Voice(HasParent):
    class CannotAddException(Exception):
        pass
    class NoChordsInRhythmStaffException(Exception):
        pass
    class NotUnisonException(Exception):
        pass
    class BarFullException(Exception):
        """
        Exception raised if we try to add a note or rest that is longer than
        the available time in the bar. FIXME: maybe name better, like
        NotEnoughtTimeException or similar.
        """
        def __unicode__(self):
            return u"There is not enough space left in the bar"
    class NoteDontBelongHere(Exception):
        """
        raised if we try to beam notes that does not belong to this voice.
        """
        pass
    def __init__(self, parent):
        HasParent.__init__(self, parent)
        # The timelen of the Voice
        self.m_length = Rat(0, 1)
        self.m_tdict = {}
    def copy(self, parent):
        """
        Return a copy of this Voice object. We make a copy of the dict and
        the m_length variable, but the dict revers to the same object.
        """
        ret = Voice(parent)
        ret.m_length = Rat(self.m_length.m_num, self.m_length.m_den)
        ret.m_tdict = self.m_tdict.copy()
        return ret
    def append(self, elem, stemdir=const.BOTH):
        """
        elem - either a MusicElement or a list of MusicElements

        Rests or Skips cannot be put in a list.

        If elem is a list of MusicElements (that is notes...), then all
        the notes will belong to the same stem when typeset.

        Create a new bar if the current bar is full.
        Raise Voice.BarFullException if the last bar is not full, but there
        is not enought room for the element in the bar.

        Also call parent so that the whole hierarcy knows about this timepos.
        """
        # Verify that if elem is a list, then there should be only Notes in it.
        if isinstance(elem, list):
            if [e for e in elem if not isinstance(e, Note)]:
                raise self.CannotAddException(elem)
        else:
            # Anyway, we want it to be a list, even at len 1 for simplicity
            elem = [elem]
        if isinstance(self.w_parent(), RhythmStaff) and len(elem) > 1:
            raise Voice.NoChordsInRhythmStaffException()
        try:
            bar = self.w_score().get_bar_at(self.m_length)
        except IndexError:
            # IndexError means that self.m_length is after the last bar, this means
            # that the current bar is full.
            bar = self.w_score().add_bar(None)
        if (self.m_length + elem[0].m_duration.get_rat_value() <= bar.end()):
            if isinstance(elem[0], Note):
                # We don't have to set w_parent for the Stem and the notes
                # here, because the Stem constructor does it.
                self.set_elem(Stem(self, elem, stemdir), self.m_length)
            else: # rest or skip
                self.set_elem(elem, self.m_length)
                elem[0].w_parent = weakref.ref(self)
            self.m_length += elem[0].m_duration.get_rat_value()
        else:
            raise self.BarFullException()
    def add_to(self, timepos, note):
        """
        Add note to an existing stem at timepos.
        """
        assert timepos in self.m_tdict
        assert self.m_tdict[timepos]['elem'][0].m_duration == note.m_duration
        note.w_parent = weakref.ref(self.m_tdict[timepos]['elem'])
        assert isinstance(note.w_parent(), Stem)
        self.m_tdict[timepos]['elem'].append(note)
    def set_elem(self, elem, timepos):
        """
        Elem is a one item list containing a Skip or Rest, or Stem (that
        is indeed a list too) containing Notes.
        """
        assert isinstance(elem, list)
        if timepos not in self.m_tdict:
            self.m_tdict[timepos] = {}
        self.m_tdict[timepos]['elem'] = elem
    def del_elem(self, timepos):
        """
        Delete the element at timepos, move the remaining notes
        in the bar to the left to fill the gap.
        """
        assert timepos in self.m_tdict
        bp = BarProxy(self, timepos)
        tp = self.get_timeposes_of(bp.m_bar)[-1]
        # If the last note in the bar is tied to the next bar, then
        # we must untie it.
        if (isinstance(self.m_tdict[tp]['elem'][0], Note)
            and self.m_tdict[tp]['elem'][0].m_tieinfo in ('go', 'start')):
            self.untie_next(tp)
        if isinstance(self.m_tdict[timepos]['elem'][0], Note):
            if self.is_last(timepos):
                self.untie_next(timepos)
            if self.m_tdict[timepos]['elem'][0].m_tieinfo == 'go':
                self.tie_prev_to_next(timepos)
            elif self.m_tdict[timepos]['elem'][0].m_tieinfo == 'end':
                self.untie_prev(timepos)
            elif self.m_tdict[timepos]['elem'][0].m_tieinfo == 'start':
                self.untie_next(timepos)
        del self.m_tdict[timepos]
        bp.remove_skips()
        bp.repack()
        bp.fill_skips()
    def try_set_elem(self, elem, timepos, insert_mode):
        """
        Replace whatever is at timepos with elem.
        Return True if succuessful.
        """
        bp = BarProxy(self, timepos)
        if isinstance(self.m_tdict[timepos]['elem'][0], Skip):
            if timepos + elem.m_duration.get_rat_value() <= bp.end():
                if isinstance(elem, Note):
                    stem = Stem(self, [elem], const.UP)
                    self.set_elem(stem, timepos)
                else:
                    self.set_elem([elem], timepos)
                    elem.w_parent = weakref.ref(self)
                bp.remove_skips()
                bp.repack()
                bp.fill_skips()
                return True
        else:
            max_free = bp.get_free_time()
            #flytt til bar-class
            delta = elem.m_duration.get_rat_value() - self.m_tdict[timepos]['elem'][0].m_duration.get_rat_value()
            def fix_ties(prev_timepos, cur_timepos, next_timepos):
                prev_e = self.m_tdict[prev_timepos]['elem'][0] if prev_timepos else None
                cur_e = self.m_tdict[cur_timepos]['elem'][0]
                next_e = self.m_tdict[next_timepos]['elem'][0] if next_timepos else None
                if isinstance(elem, Note):
                    t = None
                    if prev_timepos and isinstance(prev_e, Note) and prev_e.m_tieinfo in ('go', 'start'):
                        t = 'end'
                    if isinstance(next_e, Note) and next_e.m_tieinfo in ('go', 'end'):
                        if t == 'end':
                            t = 'go'
                        else:
                            t = 'start'
                    cur_e.m_tieinfo = t
                else:
                    assert isinstance(elem, Rest)
                    if prev_timepos and isinstance(prev_e, Note):
                        if prev_e.m_tieinfo == 'go':
                            prev_e.m_tieinfo = 'end'
                        elif prev_e.m_tieinfo == 'start':
                            prev_e.m_tieinfo = None
                    if isinstance(next_e, Note):
                        if next_e.m_tieinfo == 'go':
                            next_e.m_tieinfo = 'start'
                        elif next_e.m_tieinfo == 'end':
                            next_e.m_tieinfo = None

            if insert_mode:
                if max_free >= elem.m_duration.get_rat_value():
                    tmp_timepos = timepos + Rat(1, 1000000)
                    self.m_tdict[tmp_timepos] = self.m_tdict[timepos]
                    del self.m_tdict[timepos]
                    bp.remove_trailing(elem.m_duration.get_rat_value())
                    stem = Stem(self, [elem], const.UP)
                    self.set_elem(stem, timepos)
                    fix_ties(self.get_prev_timepos(timepos), timepos, tmp_timepos)
                    bp.remove_skips()
                    bp.repack()
                    bp.fill_skips()
                    return True
            if not insert_mode:
                if (max_free >= delta):
                    # We have space to add.
                    # Delete skips (and rests) from the end of the bar
                    # until we have enough space to add the elem.
                    if delta > Rat(0, 1):
                        bp.remove_trailing(delta)
                    stem = Stem(self, [elem], const.UP)
                    self.set_elem(stem, timepos)
                    fix_ties(self.get_prev_timepos(timepos), timepos, self.get_next_timepos(timepos))
                    bp.remove_skips()
                    bp.repack()
                    bp.fill_skips()
                    return True
    def fill_with_skips(self):
        """
        Fill the voice with skips. We assume the voice is empty.
        """
        for bar in self.w_score().m_bars:
            bar.fill_skips(self)
    def get_timeposes_of(self, bar):
        """
        Return a sorted list of all timeposes in bar in this Voice
        """
        v = sorted(self.m_tdict.keys())
        try:
            # this is the fastest way to set start_i
            start_i = v.index(bar.m_timepos)
        except ValueError:
            # but if code has recently removed the timepos, then we have to
            # search for it.
            start_i = 0
            while start_i < len(v) and v[start_i] < bar.m_timepos:
                start_i += 1
        if start_i >= len(v) or v[start_i] >= bar.end():
            start_i = None
        try:
            end_i = v.index(bar.end())
        except ValueError:
            end_i = None
        if start_i == None:
            return []
        elif end_i:
            return v[start_i:end_i]
        else:
            return v[start_i:]
    def get_time_pitch_list(self, bpm):
        """
        Return a list of tuples (pitch, duration-in-seconds) of the tones
        and rests in the voice. -1 is used for pitch for rests.
        """
        ret = []
        for timepos in sorted(self.m_tdict.keys()):
            # stem is a Stem or [Rest]
            stem = self.m_tdict[timepos]['elem']
            if len(stem) != 1:
                raise Voice.NotUnisonException()
            dur = float(stem[0].m_duration.get_rat_value()) * bpm[1] / bpm[0] * 60
            if isinstance(stem[0], Note):
                ret.append((stem[0].m_musicalpitch.semitone_pitch(), dur))
            elif isinstance(stem[0], Rest):
                ret.append((-1, dur))
        return ret
    def beam(self, notes):
        """
        Notes is a list of Note objects, once Note object from each stem
        you want to beam.
        The notes should be in sequence on this Voice. Behaviour if not
        sequential is undefined.
        """
        for note in notes:
            try:
                if note.w_parent().w_parent() != self:
                    raise self.NoteDontBelongHere()
            except AttributeError:
                raise self.NoteDontBelongHere()
        notes[0].w_parent().m_beaminfo = 'start'
        for n in notes[1:][:-1]:
            n.w_parent().m_beaminfo = 'go'
        notes[-1].w_parent().m_beaminfo = 'end'
    def tie_timepos(self, timepos):
        """
        Tie all notes on this timepos that has the same pitch as notes on the
        next timepos. Return True if tie(s) could be added.
        FIXME: The current version of this method only works as expected
        when there is only one notehead on each stem. This because it was
        implemented to create the rhythmwidget.
        """
        next_timepos = self.get_next_timepos(timepos)
        # if we are last in the score
        if not next_timepos:
            return
        if not isinstance(self.m_tdict[next_timepos]['elem'][0], Note):
            return
        # Assert there is only one notehead on each stem.
        assert len(self.m_tdict[timepos]['elem']) == 1
        assert len(self.m_tdict[next_timepos]['elem']) == 1
        if self.m_tdict[timepos]['elem'][0].m_musicalpitch == self.m_tdict[next_timepos]['elem'][0].m_musicalpitch:
            self.tie([self.m_tdict[timepos]['elem'][0],
                      self.m_tdict[next_timepos]['elem'][0]])
            return True
    def untie_next(self, timepos):
        """
        Return True if we removed the tie from timepos to the note after.
        Return False if not.
        """
        next_timepos = self.get_next_timepos(timepos)
        if self.m_tdict[timepos]['elem'][0].m_tieinfo == 'start':
            if self.m_tdict[next_timepos]['elem'][0].m_tieinfo == 'end':
                self.m_tdict[next_timepos]['elem'][0].m_tieinfo = None
            elif self.m_tdict[next_timepos]['elem'][0].m_tieinfo == 'go':
                self.m_tdict[next_timepos]['elem'][0].m_tieinfo = 'start'
            else:
                return False
            self.m_tdict[timepos]['elem'][0].m_tieinfo = None
        elif self.m_tdict[timepos]['elem'][0].m_tieinfo == 'go':
            if self.m_tdict[next_timepos]['elem'][0].m_tieinfo == 'end':
                self.m_tdict[next_timepos]['elem'][0].m_tieinfo = None
            elif self.m_tdict[next_timepos]['elem'][0].m_tieinfo == 'go':
                self.m_tdict[next_timepos]['elem'][0].m_tieinfo = 'start'
            else:
                return False
            self.m_tdict[timepos]['elem'][0].m_tieinfo = 'end'
        else:
            return False
        return True
    def untie_prev(self, timepos):
        """
        Remove True if we removed a tie from the prev note to this.
        Return False if not.
        """
        prev_timepos = self.get_prev_timepos(timepos)
        if self.m_tdict[timepos]['elem'][0].m_tieinfo == 'end':
            if self.m_tdict[prev_timepos]['elem'][0].m_tieinfo == 'start':
                self.m_tdict[prev_timepos]['elem'][0].m_tieinfo = None
            elif self.m_tdict[prev_timepos]['elem'][0].m_tieinfo == 'go':
                self.m_tdict[prev_timepos]['elem'][0].m_tieinfo = 'end'
            else:
                return False
            self.m_tdict[timepos]['elem'][0].m_tieinfo = None
        elif self.m_tdict[timepos]['elem'][0].m_tieinfo == 'go':
            if self.m_tdict[prev_timepos]['elem'][0].m_tieinfo == 'start':
                self.m_tdict[prev_timepos]['elem'][0].m_tieinfo = None
            elif self.m_tdict[prev_timepos]['elem'][0].m_tieinfo == 'go':
                self.m_tdict[prev_timepos]['elem'][0].m_tieinfo = 'end'
            else:
                return False
            self.m_tdict[timepos]['elem'][0].m_tieinfo = 'start'
    def tie_prev_to_next(self, timepos):
        assert self.m_tdict[timepos]['elem'][0].m_tieinfo == 'go'
        assert self.m_tdict[self.get_prev_timepos(timepos)]['elem'][0].m_tieinfo in ('start', 'go')
        assert self.m_tdict[self.get_next_timepos(timepos)]['elem'][0].m_tieinfo in ('end', 'go')
        self.m_tdict[timepos]['elem'][0].m_tieinfo = None
    def tie(self, notes):
        """
        The notes should be in sequence on this Voice. Behaviour if not
        sequential is undefined.
        """
        for note in notes:
            # FIXME common with beam
            try:
                if note.w_parent().w_parent() != self:
                    raise self.NoteDontBelongHere()
            except AttributeError:
                raise self.NoteDontBelongHere()
        if notes[0].m_tieinfo == 'end':
            notes[0].m_tieinfo = 'go'
        elif notes[0].m_tieinfo is None:
            notes[0].m_tieinfo = 'start'
        for n in notes[1:][:-1]:
            n.m_tieinfo = 'go'
        # This conditional is true when notes 2 and 3 are tied, and the
        # editor ties note 1 and note 2.
        if notes[-1].m_tieinfo == 'start':
            notes[-1].m_tieinfo = 'go'
        elif notes[-1].m_tieinfo is None:
            notes[-1].m_tieinfo = 'end'
    def tuplet(self, ratio, direction, notes):
        """
        ratio - a Rat, for example Rat(2, 3) for normal triplets.
        direction - const.UP, const.DOWN or const.BOTH
        notes - a list of Note objects, once Note object from each stem
                you want to have a visible tuplet engraver.
        The notes should be in sequence on this Voice. Behaviour if not
        sequential is undefined.
        """
        for note in notes:
            # FIXME common with beam
            try:
                if note.w_parent().w_parent() != self:
                    raise self.NoteDontBelongHere()
            except AttributeError:
                raise self.NoteDontBelongHere()
        if notes[0].w_parent().m_tupletinfo == 'end':
            notes[0].w_parent().m_tupletinfo = 'go'
        else:
            notes[0].w_parent().m_tupletinfo = 'start'
            notes[0].w_parent().m_tuplet_dir = direction
            notes[0].w_parent().m_tuplet_ratio = ratio
        for n in notes[1:][:-1]:
            n.w_parent().m_tupletinfo = 'go'
        notes[-1].w_parent().m_tupletinfo = 'end'
    def set_clef(self, clef):
        """
        Set the clef that will be inserted into the staff before the next
        music element.
        """
        self.w_parent().set_clef(clef, self.m_length)
    def set_key_signature(self, keysig):
        """
        Call the Staff and set the key signature at the timepos the next
        tone will be added to this voice.
        """
        self.w_parent().set_key_signature(keysig, self.m_length)
    def is_bar_full(self):
        """
        Return True if this the next tone will be placed on the first beat
        of a bar. This means that there are either nothing in the voice at
        all, or the current bar is full.
        """
        try:
            bar = self.w_score().get_bar_at(self.m_length)
            return bar.m_timepos == self.m_length
        except IndexError:
            return True
    def get_prev_timepos(self, timepos):
        """
        Return the previous timepos. Return None if this is the first
        timepos in the voice.
        """
        assert timepos in self.m_tdict
        v = sorted(self.m_tdict.keys())
        i = v.index(timepos)
        if i > 0:
            return v[i - 1]
    def get_next_timepos(self, timepos):
        """
        Return the next timepos. Return None if this is the last timepos
        in the Voice.
        """
        assert timepos in self.m_tdict
        v = sorted(self.m_tdict.keys())
        i = v.index(timepos)
        if i +1 < len(v):
            return v[i + 1]
    def get_timelist(self):
        retval = []
        for timepos in sorted(self.m_tdict.keys()):
            if isinstance(self.m_tdict[timepos]['elem'][0], Rest):
                if retval[-1][0] == False:
                    retval[-1][1] += self.m_tdict[timepos]['elem'][0].m_duration.get_rat_value()
                else:
                    retval.append([False, self.m_tdict[timepos]['elem'][0].m_duration.get_rat_value()])
            elif self.m_tdict[timepos]['elem'][0].m_tieinfo == 'start':
                nlen = self.m_tdict[timepos]['elem'][0].m_duration.get_rat_value()
            elif self.m_tdict[timepos]['elem'][0].m_tieinfo == 'continue':
                nlen += self.m_tdict[timepos]['elem'][0].m_duration.get_rat_value()
            else:
                if self.m_tdict[timepos]['elem'][0].m_tieinfo == 'end':
                    nlen += self.m_tdict[timepos]['elem'][0].m_duration.get_rat_value()
                else:
                    nlen = self.m_tdict[timepos]['elem'][0].m_duration.get_rat_value()
                retval.append([isinstance(self.m_tdict[timepos]['elem'][0], Note),
                  nlen])
                nlen = None
        return retval
    def is_last(self, timepos):
        """
        Return a bool telling if the elem at timepos is the last in the
        bar and fill it, so that the next elem has to be the first in the
        next bar.
        """
        return self.m_tdict[timepos]['elem'][0].m_duration.get_rat_value() + timepos == self.w_score().get_bar_at(timepos).end()
    def __getitem__(self, idx):
        v = sorted(self.m_tdict)
        return self.m_tdict[v[idx]]

class Bar(object):
    def __init__(self, timesig, timepos):
        """
        Time signature is the time signature of the bar. It does not
        necessarily mean that we will engrave a time signature on the
        score. All bar objects need to know their length.

        timepos is the time of the first music in the bar. So timepos
        + timesig will be the position of the next bar.
        """
        assert isinstance(timesig, TimeSignature)
        assert isinstance(timepos, Rat)
        self.m_timesig = timesig
        self.m_timepos = timepos
    def end(self):
        return self.m_timepos + self.m_timesig.as_rat()
    def fill_skips(self, voice):
        """
        Add Skips at the end of the bar, so that it is filled.
        We assume that any elements already added are placed at
        the correct timepos.
        """
        # nt = short for "next timepos", the timepos to start fill skips to
        if voice.get_timeposes_of(self):
            nt = voice.get_timeposes_of(self)[-1]
            nt = nt + voice.m_tdict[nt]['elem'][0].m_duration.get_rat_value()
        else:
            # we get here if the bar is empty
            nt = self.m_timepos
        default_skip = Rat(1, 4)
        # pos within default skip
        pp =  nt - int (nt / default_skip) * default_skip
        if pp != Rat(0, 1):
            # Here we add a skip so that the next column will be X times
            # default_skip
            voice.set_elem([Skip(Duration.new_from_rat(default_skip - pp))],
                          nt)
            nt += (default_skip - pp)
        # And the we fill the bar with Skips as long as default_skip.
        while nt < self.end():
            voice.set_elem([Skip(Duration.new_from_rat(default_skip))], nt)
            nt += default_skip
    def get_free_time(self, voice):
        """
        Return the duration, as a Rat value, on the end of the bar
        consisting of Rests and Skips.
        """
        d = Rat(0, 1)
        for timepos in reversed(voice.get_timeposes_of(self)):
            if not isinstance(voice.m_tdict[timepos]['elem'][0], (Skip, Rest)):
                break
            d += voice.m_tdict[timepos]['elem'][0].m_duration.get_rat_value()
        return d
    def pop_last_elem(self, voice):
        """
        Remove the last element form the voice, and return its
        duration as a Rat.
        """
        timepos = voice.get_timeposes_of(self)[-1]
        ret = voice.m_tdict[timepos]['elem'][0].m_duration.get_rat_value()
        del voice.m_tdict[timepos]
        return ret
    def remove_skips(self, voice):
        """
        Remove the skips from the bar, if any.
        Leave bar in inconsistent state. Need bar.repack or similar after
        calling this method.
        """
        for t in voice.get_timeposes_of(self):
            if isinstance(voice.m_tdict[t]['elem'][0], Skip):
                del voice.m_tdict[t]
    def remove_trailing(self, voice, duration):
        """
        Remove elements from the end of the bar, until their duration
        is a least 'duration' long.
        """
        assert isinstance(duration, Rat)
        total = Rat(0, 1)
        while total < duration:
            total += self.pop_last_elem(voice)
    def repack(self, voice):
        """
        Call this method to cleanup m_tdict for the bar after keys
        from m_tict have ben deleted. Example before bar.repack:
        0/4: Note
        1/4: Rest
        1/2: Note

        then del m_tdict[Rat(1, 4)] make the content of tdict look like this:
        0/4: Note
        1/2: Note

        Calling bar.repack will repack is like this:
        0/4: Note
        1/4: Note

        NOTE: This method does not add or remove any elements, including Skips
        """
        timeposes = voice.get_timeposes_of(self)
        if timeposes:
            last_is_last = voice.is_last(timeposes[-1])
        else:
            last_is_last = None
        corrected_timepos = self.m_timepos
        mods = {}
        for t in voice.get_timeposes_of(self):
            if t != corrected_timepos:
                mods[corrected_timepos] = t
            corrected_timepos += voice.m_tdict[t]['elem'][0].m_duration.get_rat_value()
            if corrected_timepos > self.end():
                raise voice.BarFullException()
        if mods:
            # This conditional is true if the elem we are replacing is shorter
            # than the new one. We must select the correct order to adjust the
            # timeposes so we don't overwrite values
            if mods.items()[0][0] < mods.items()[0][1]:
                keys = sorted(mods.keys())
            else:
                keys = reversed(sorted(mods.keys()))
            for n in keys:
                assert n not in voice.m_tdict
                voice.m_tdict[n] = voice.m_tdict[mods[n]]
                del voice.m_tdict[mods[n]]
        # If the last note is not filling the bar any more, then we must
        # remove the tie.
        if last_is_last:
            timeposes = voice.get_timeposes_of(self)
            if (timeposes and not voice.is_last(timeposes[-1])
                and isinstance(voice.m_tdict[timeposes[-1]]['elem'][0], Note)
                and voice.m_tdict[timeposes[-1]]['elem'][0].m_tieinfo in ('go', 'start')):
                voice.untie_next(timeposes[-1])
    def __repr__(self):
        return "<%s %i/%i %s at %s>" % (str(self.__class__).split(".")[-1][:-2], self.m_timesig.m_num,
            self.m_timesig.m_den, self.m_timepos, hex(id(self)))

class PartialBar(Bar):
    def __init__(self, duration, timesig, timepos):
        Bar.__init__(self, timesig, timepos)
        assert isinstance(duration, Duration)
        self.m_duration = duration
    def end(self):
        return self.m_timepos + self.m_duration.get_rat_value()

class BarProxy(object):
    def __init__(self, voice, timepos):
        self.m_voice = voice
        self.m_bar = voice.w_parent().w_parent().get_bar_at(timepos)
    def __getattr__(self, attr):
        if attr == 'end':
            return self.m_bar.end
        return lambda *f: getattr(self.m_bar, attr)(self.m_voice, *f)

class _StaffCommon(HasParent):
    """
    A voice is added to the staff when it is created.
    """
    def __init__(self, parent):
        assert isinstance(parent, Score)
        HasParent.__init__(self, parent)
        self.m_voices = []
        self.add_voice()
        # I think the only things stored in Staff.m_tdict are "clef" and
        # "keysig". We don't store time signature changes where, since
        # Score.m_bars take care about that.
        self.m_tdict = {}
    def copy(self, parent):
        staff = self.__class__(parent)
        staff.m_voices = [v.copy(staff) for v in self.m_voices]
        staff.m_tdict = self.m_tdict.copy()
        return staff
    def add_voice(self):
        self.m_voices.append(Voice(self))
        self.w_score().create_shortcuts()
        return self.m_voices[-1]
    def get_timeposes(self):
        """
        Return a sorted list of all timeposes in the staff.
        We generate the list by checking all timeposes added to the
        staff because of Clefs and TimeSignatures, and then all timeposes
        in the voices.
        """
        timeposes = set()
        for has_timeposes in self.m_voices + [self]:
            [timeposes.add(t) for t in has_timeposes.m_tdict]
        return sorted(timeposes)
    def get_timelist(self):
        data = {}
        for voice_idx, voice in enumerate(self.m_voices):
            for timepos in voice.m_tdict:
                n = voice.m_tdict[timepos]['elem'][0]
                if isinstance(n, Note):
                    if timepos not in data:
                        data[timepos] = {'start': set(), 'end': set()}
                    data[timepos]['start'].add(voice_idx)
                    endpos = timepos + n.m_duration.get_rat_value()
                    if endpos not in data:
                        data[endpos] = {'start': set(), 'end': set()}
                    data[endpos]['end'].add(voice_idx)
        retval = []
        v = sorted(data)[:]
        ppos = Rat(0, 1)
        voices = set()
        for timepos in v:
            if data[timepos]['start'] and data[timepos]['end']:
                for voice in data[timepos]['end']:
                    voices.remove(voice)
                for voice in data[timepos]['start']:
                    voices.add(voice)
                assert voices
                retval.append([True, timepos - ppos])
                ppos = timepos
            elif data[timepos]['start']:
                if not voices:
                    ppos = timepos
                else:
                    retval.append([True, timepos - ppos])
                    ppos = timepos
                for voice in data[timepos]['start']:
                    voices.add(voice)
            elif data[timepos]['end']:
                for voice in data[timepos]['end']:
                    voices.remove(voice)
                if not voices:
                    retval.append([True, timepos - ppos])
        return retval
    def set_property(self, timepos, name, value):
        d = self.m_tdict.setdefault(timepos, {})
        properties = d.setdefault('properties', {})
        properties[name] = value

class Staff(_StaffCommon):
    def __init__(self, parent):
        _StaffCommon.__init__(self, parent)
        self.set_clef("violin", Rat(0, 1))
    def set_clef(self, clef, timepos):
        if timepos not in self.m_tdict:
            self.m_tdict[timepos] = {}
        self.m_tdict[timepos]['clef'] = Clef(clef)
    def set_key_signature(self, keysig, timepos):
        if timepos not in self.m_tdict:
            self.m_tdict[timepos] = {}
        self.m_tdict[timepos]['keysig'] = keysig


class RhythmStaff(_StaffCommon):
    """
    We don't implement set_clef since there should be no clefs on a
    rhythm staff.
    """
    class OnlyOneVoiceException(Exception):
        pass
    def __init__(self, parent):
        _StaffCommon.__init__(self, parent)
    def add_voice(self):
        if len(self.m_voices) == 1:
            raise self.OnlyOneVoiceException()
        _StaffCommon.add_voice(self)
    def set_key_signature(self, keysig, timepos):
        """
        RhythmStaffs don't have key signatures.
        """
        return


class Score(object):
    class ConcatException(Exception):
        pass
    class StaffCountException(ConcatException):
        pass
    class StaffTypeException(ConcatException):
        pass
    class VoiceCountException(ConcatException):
        pass
    def __init__(self):
        self.m_staffs = []
        self.m_bars = []
    def copy(self):
        score = Score()
        score.m_staffs = [s.copy(score) for s in self.m_staffs]
        score.m_bars = copy.deepcopy(self.m_bars)
        return score
    def add_staff(self, staff_class=Staff):
        self.m_staffs.append(staff_class(self))
        self.create_shortcuts()
        return self.m_staffs[-1]
    def create_shortcuts(self):
        """
        (Re)create the voice and staff shortcuts.
        """
        # shortcut that is nice to people using the API directly.
        for staff_idx, staff in enumerate(self.m_staffs):
            setattr(self, "staff%i" % (staff_idx + 1), staff)
            for voice_idx, voice in enumerate(staff.m_voices):
                setattr(self, "voice%i%i" % (staff_idx + 1, voice_idx + 1), voice)
    def _get_new_bar_timepos(self):
        """
        Return the timepos where the next bar will be added.
        """
        if self.m_bars:
            return self.m_bars[-1].end()
        return Rat(0, 1)
    def _get_new_bar_timesig(self, timesig):
        """
        Return the time signature the next bar will get.
        """
        if timesig:
            return timesig
        elif self.m_bars:
            return self.m_bars[-1].m_timesig
        else:
            return TimeSignature(4, 4)
    def add_bar(self, timesig):
        """
        If timesig is None, then we use the same timesig as the last bar.
        Return the added bar.
        """
        self.m_bars.append(Bar(
            self._get_new_bar_timesig(timesig), self._get_new_bar_timepos()))
        return self.m_bars[-1]
    def add_partial_bar(self, duration, timesig):
        """
        Set to the duration of the pickup bar if we want one.
        This must be called before bars are added with Score.add_bar
        """
        self.m_bars.append(PartialBar(duration,
            self._get_new_bar_timesig(timesig), self._get_new_bar_timepos()))
        return self.m_bars[-1]
    def get_bar_at(self, timepos):
        """
        Return the bar timepos is within. Raise IndexError if timepos
        is after the last bar.
        """
        for bar in self.m_bars:
            if bar.m_timepos <= timepos < bar.end():
                return bar
            if bar.m_timepos > timepos:
                return IndexError(timepos)
        raise IndexError(timepos)
    def get_timelist(self):
        data = {}
        for staff_idx, staff in enumerate(self.m_staffs):
            for voice_idx, voice in enumerate(staff.m_voices):
                for timepos in voice.m_tdict:
                    n = voice.m_tdict[timepos]['elem'][0]
                    if isinstance(n, Note):
                        if timepos not in data:
                            data[timepos] = {'start': set(), 'end': set()}
                        if n.m_tieinfo not in ('go', 'end'):
                            data[timepos]['start'].add((staff_idx, voice_idx))
                        if n.m_tieinfo in (None, 'end'):
                            endpos = timepos + n.m_duration.get_rat_value()
                            if endpos not in data:
                                data[endpos] = {'start': set(), 'end': set()}
                            data[endpos]['end'].add((staff_idx, voice_idx))
        retval = []
        v = sorted(data)[:]
        ppos = Rat(0, 1)
        voices = set()
        for timepos in v:
            if data[timepos]['start'] and data[timepos]['end']:
                for voice in data[timepos]['end']:
                    voices.remove(voice)
                for voice in data[timepos]['start']:
                    voices.add(voice)
                assert voices
                retval.append([True, timepos - ppos])
                ppos = timepos
            elif data[timepos]['start']:
                if not voices:
                    if (timepos != ppos):
                        retval.append([False, timepos - ppos])
                        ppos = timepos
                else:
                    retval.append([True, timepos - ppos])
                    ppos = timepos
                for voice in data[timepos]['start']:
                    voices.add(voice)
            elif data[timepos]['end']:
                for voice in data[timepos]['end']:
                    voices.remove(voice)
                if not voices:
                    retval.append([True, timepos - ppos])
                    ppos = timepos
        return retval
    @staticmethod
    def concat(s1, s2):
        """
        Concatenate the two scores, and return a new score. Both scores
        need to have the exact same staff and voice layout.
        """
        assert isinstance(s1, Score)
        assert isinstance(s2, Score)
        if len(s1.m_staffs) != len(s2.m_staffs):
            raise Score.StaffCountException()
        if [type(x) for x in s1.m_staffs] != [type(x) for x in s2.m_staffs]:
            raise Score.StaffTypeException()
        for st1, st2 in zip(s1.m_staffs, s2.m_staffs):
            if len(st1.m_voices) != len(st2.m_voices):
                raise Score.VoiceCountException()
        ret = s1.copy()
        if not s1.m_staffs:
            return s1
        # do the adding
        for bar in s2.m_bars:
            bar.m_timepos = ret.m_bars[-1].end()
            ret.m_bars.append(bar)
        ret.create_shortcuts()
        if s1.m_bars:
            start = s1.m_bars[-1].end()
        else:
            start = Rat(0, 1)
        s2.create_shortcuts() # FIXME why?
        for staff_idx, staff in enumerate(s1.m_staffs):
            for voice_idx in range(len(staff.m_voices)):
                for k in s2.m_staffs[staff_idx].m_voices[voice_idx].m_tdict:
                    ret.m_staffs[staff_idx].m_voices[voice_idx].m_tdict[k + start] = s2.m_staffs[staff_idx].m_voices[voice_idx].m_tdict[k]
        return ret
    @staticmethod
    def concat2(s1, s2):
        """
        Return a new Score object concatenating the two scores. This is
        intended return value is intended for playback only, since the
        staffs placed below each other. So the first score will have empty
        bars at the end, and the last score will have empty bars at the
        beginning.
        """
        assert isinstance(s1, Score)
        assert isinstance(s2, Score)
        ret = s1.copy()
        if s1.m_bars:
            start = s1.m_bars[-1].end()
        else:
            start = Rat(0, 1)
        for bar in s2.m_bars:
            ret.m_bars.append(Bar(bar.m_timesig, ret.m_bars[-1].end()))
        for staff_idx, staff in enumerate(s2.m_staffs):
            ret.add_staff(staff_class=staff.__class__)
            for k in staff.m_tdict:
                ret.m_staffs[-1].m_tdict[start + k] = staff.m_tdict[k]
            for voice_idx in range(len(staff.m_voices)):
                if voice_idx != 0:
                    ret.m_staffs[-1].add_voice()
                # This line make the music from sc2 continue after the
                # point where the music from sc1 ends.
                ret.m_staffs[-1].m_voices[-1].m_length = s1.m_bars[-1].end()
                for elem in s2.m_staffs[staff_idx].m_voices[voice_idx]:
                    ret.m_staffs[-1].m_voices[-1].append(elem['elem'])
        ret.create_shortcuts()
        return ret
    def __deepcopy__(self, memo):
        ret = Score()
        ret.m_bars = copy.deepcopy(self.m_bars)
        return ret
