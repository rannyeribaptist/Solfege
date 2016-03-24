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
>>> import locale, gettext
>>> gettext.NullTranslations().install()
>>> a = MusicalPitch.new_from_notename("g")
>>> b = MusicalPitch.new_from_notename("f")
>>> print a - b
2
>>> print (a - 2).get_octave_notename()
f
>>> print (a + 3).get_octave_notename()
ais
>>> print a < b
0
>>> print a > b
1
>>> print MusicalPitch.new_from_int(55) == a
1
>>> print MusicalPitch.new_from_notename(a.get_notename()) == a
1
>>> print a.clone() == a, id(a) == id(a.clone())
True False
>>> a=MusicalPitch()
>>> print a.m_octave_i == a.m_accidental_i == a.m_octave_i == 0
1
>>> print a.semitone_pitch()
48
>>> print a.get_octave_notename()
c
>>> print (a+2).get_octave_notename()
d
>>> print (2+a).get_octave_notename()
d
>>> print MusicalPitch.new_from_notename("des'").get_notename()
des
>>> print MusicalPitch.new_from_int(50).semitone_pitch()
50
>>> print MusicalPitch.new_from_int(50).get_notename()
d
>>> n=MusicalPitch.new_from_notename("fis,")
>>> print n.get_user_octave_notename()
f#,
>>> n=MusicalPitch.new_from_notename("b,,")
>>> print n.get_octave_notename()
b,,
>>> print n.get_user_octave_notename()
b,,
>>> gettext.translation('solfege', './share/locale/', languages=['nb_NO']).install()
>>> print n.get_octave_notename()
b,,
>>> print n.get_user_octave_notename()
<sub>1</sub>H
>>> print n.get_user_notename()
h
>>> print _("Close")
Lukk
>>> n = MusicalPitch()
>>> n.set_from_notename("d'")
>>> print n.get_octave_notename()
d'
"""

import logging
import random

from solfege.mpd import _exceptions

# The following are here so that the strings are caught by pygettext
_("notename|c")
_("notename|cb")
_("notename|cbb")
_("notename|c#")
_("notename|cx")
_("notename|d")
_("notename|db")
_("notename|dbb")
_("notename|d#")
_("notename|dx")
_("notename|e")
_("notename|eb")
_("notename|ebb")
_("notename|e#")
_("notename|ex")
_("notename|f")
_("notename|fb")
_("notename|fbb")
_("notename|f#")
_("notename|fx")
_("notename|g")
_("notename|gb")
_("notename|gbb")
_("notename|g#")
_("notename|gx")
_("notename|a")
_("notename|ab")
_("notename|abb")
_("notename|a#")
_("notename|ax")
_("notename|b")
_("notename|bb")
_("notename|bbb")
_("notename|b#")
_("notename|bx")

class InvalidNotenameException(_exceptions.MpdException):
    def __init__(self, n):
        _exceptions.MpdException.__init__(self)
        self.m_notename = n
    def __str__(self):
        return _("Invalid notename: %s") % self.m_notename

class MusicalPitch:
    LOWEST_STEPS = -28
    HIGHEST_STEPS = 47
    notenames = ('c', 'cis', 'd', 'dis', 'e', 'f', 'fis',
                 'g', 'gis', 'a', 'ais', 'b')
    natural_notenames = ('c', 'd', 'e', 'f', 'g', 'a', 'b')
    sharp_notenames = ('cis', 'dis', 'fis', 'gis', 'ais')
    def clone(self):
        r = MusicalPitch()
        r.m_octave_i = self.m_octave_i
        r.m_notename_i = self.m_notename_i
        r.m_accidental_i = self.m_accidental_i
        return r
    def new_from_notename(n):
        assert isinstance(n, basestring)
        r = MusicalPitch()
        r.set_from_notename(n)
        return r
    new_from_notename = staticmethod(new_from_notename)
    def new_from_int(i):
        assert type(i) == type(0)
        r = MusicalPitch()
        r.set_from_int(i)
        return r
    new_from_int = staticmethod(new_from_int)
    def __init__(self):
        """
         c,,,, is lowest: m_octave_i == -4, steps() == -28
         g'''''' is highest: m_octave_i = 6, steps() == 46
        """
        self.m_octave_i = self.m_accidental_i = self.m_notename_i = 0
    def transpose_by_musicalpitch(self, P):
        """Silly function used by mpd/parser.py and company
        (d') transposes up one major second.
        """
        tra = P.semitone_pitch() - 60
        old_p = self.semitone_pitch()
        self.m_notename_i = self.m_notename_i + P.m_notename_i
        self.m_accidental_i = self.m_accidental_i + P.m_accidental_i
        if self.m_notename_i > 6:
            self.m_notename_i = self.m_notename_i - 7
            self.m_octave_i = self.m_octave_i + 1
        self.m_octave_i = self.m_octave_i + P.m_octave_i - 1
        if self.semitone_pitch()-old_p < tra:
            self.m_accidental_i = self.m_accidental_i + 1
        elif self.semitone_pitch()-old_p > tra:
            self.m_accidental_i = self.m_accidental_i - 1
        self.sanitate_accidental()
        return self
    def sanitate_accidental(self):
        """
        Make use self.m_accidental_i is some of the values -2, -1, 0, 1, 2
        It can be out of this range if the musicalpitch has been transposed.
        This function will change notenames like gisisis, where m_accidental_i
        is 3 to ais where m_accidental_i is 1
        """
        if not -3 < self.m_accidental_i < 3:
            p = self.semitone_pitch()
            self.set_from_int(p)
    def enharmonic_flip(self):#FIXME find proper name.
        """
        Change the notename, so that gis becomes aes.
        What about d, should it be cisis or eeses??

        his,  c deses
        cisis d deses
        disis e fes
        eis   f geses
        fisis g aeses
        gisis a beses
        aisis b ces'

        cis des
        dis es
        fis ges
        gis aes
        ais bes
        """
        if self.m_accidental_i == 1 and self.m_notename_i < 6:
            self.m_accidental_i = -1
            self.m_notename_i += 1
    def normalize_double_accidental(self):
        """
        Change the tone so that we avoid double accidentals.
        """
        if self.m_accidental_i == 2:
            if self.m_notename_i in (0, 1, 3, 4, 5): # c d f g a
                self.m_notename_i += 1
                self.m_accidental_i = 0
            elif self.m_notename_i == 2: # e
                self.m_notename_i = 3
                self.m_accidental_i = 1
            else:
                assert self.m_notename_i == 6 # b
                self.m_notename_i = 0
                self.m_accidental_i = 1
                self.m_octave_i += 1
        elif self.m_accidental_i == -2:
            if self.m_notename_i in (1, 2, 4, 5, 6): # d e g a b
                self.m_notename_i -= 1
                self.m_accidental_i = 0
            elif self.m_notename_i == 3: # f
                self.m_notename_i = 2
                self.m_accidental_i = -1
            else:
                assert self.m_notename_i == 0
                self.m_notename_i = 6
                self.m_accidental_i = -1
                self.m_octave_i -= 1
    def steps(self):
        return self.m_notename_i + self.m_octave_i * 7
    def semitone_pitch(self):
        return [0, 2, 4, 5, 7, 9, 11][self.m_notename_i] + \
               self.m_accidental_i + self.m_octave_i * 12 + 48
    def pitch_class(self):
        return ([0, 2, 4, 5, 7, 9, 11][self.m_notename_i] + self.m_accidental_i) % 12
    def set_from_int(self, midiint):
        self.m_octave_i = (midiint-48)/12
        self.m_notename_i = {0:0, 1:0, 2:1, 3:1, 4:2, 5:3, 6:3, 7:4, 8:4,
                             9:5, 10:5, 11:6}[midiint % 12]
        self.m_accidental_i = midiint-(self.m_octave_i+4)*12 \
                              -[0, 2, 4, 5, 7, 9, 11][self.m_notename_i]
    def set_from_notename(self, notename):
        if not notename:
            raise InvalidNotenameException(notename)
        tmp = notename
        self.m_accidental_i = self.m_octave_i = 0
        while notename[-1] in ["'", ","]:
            if notename[-1] == "'":
                self.m_octave_i = self.m_octave_i + 1
            elif notename[-1] == ",":
                self.m_octave_i = self.m_octave_i - 1
            notename = notename[:-1]
        if notename.startswith('es'):
            notename = 'ees' + notename[2:]
        if notename.startswith('as'):
            notename = 'aes' + notename[2:]
        while notename.endswith('es'):
            self.m_accidental_i = self.m_accidental_i -1
            notename = notename[:-2]
        while notename.endswith('is'):
            self.m_accidental_i = self.m_accidental_i + 1
            notename = notename[:-2]
        try:
            self.m_notename_i = ['c', 'd', 'e', 'f', 'g', 'a', 'b'].index(notename)
        except ValueError:
            raise InvalidNotenameException(tmp)
    def randomize(self, lowest, highest):
        """
        lowest and highest can be an integer, string or a MusicalPitch instance
        """
        assert type(lowest) == type(highest)
        if isinstance(lowest, basestring):
            lowest = MusicalPitch.new_from_notename(lowest).semitone_pitch()
        if isinstance(highest, basestring):
            highest = MusicalPitch.new_from_notename(highest).semitone_pitch()
        self.set_from_int(random.randint(int(lowest), int(highest)))
        return self
    def __radd__(self, a):
        return self + a
    def __add__(self, i):
        """
        MusicalPitch + integer = MusicalPitch
        MusicalPitch + Interval = MusicalPitch
        """
        if type(i) == type(0):
            v = self.semitone_pitch()
            if not 0 <= v + i < 128:
                raise ValueError
            return MusicalPitch.new_from_int(v+i)
        elif i.__class__.__name__ == 'Interval':#isinstance(i, interval.Interval):
            if not 0 <= self.semitone_pitch() + i.get_intvalue() < 128:
                raise ValueError
            r = self.clone()
            _p = r.semitone_pitch()
            r.m_notename_i = r.m_notename_i + i.m_interval * i.m_dir
            r.m_octave_i = r.m_octave_i + r.m_notename_i / 7 + i.m_octave * i.m_dir
            r.m_notename_i = r.m_notename_i % 7
            _diff = r.semitone_pitch() - _p
            r.m_accidental_i = r.m_accidental_i + (i.get_intvalue() - _diff)
            # to avoid notenames like ciscisciscis :
            if r.m_accidental_i > 2:
                #                     c  d  f  g  a
                if r.m_notename_i in (0, 1, 3, 4, 5):
                    r.m_accidental_i -= 2
                else:
                    assert r.m_notename_i in (2, 6), r.m_notename_i
                    r.m_accidental_i -= 1
                r.m_notename_i = r.m_notename_i + 1
                if r.m_notename_i == 7:
                    r.m_notename_i = 0
                    r.m_octave_i = r.m_octave_i + 1
            if r.m_accidental_i < -2:
                r.m_accidental_i = r.m_accidental_i + 2
                r.m_notename_i = r.m_notename_i - 1
                if r.m_notename_i == -1:
                    r.m_notename_i = 6
                    r.m_octave_i = r.m_octave_i - 1
            if not 0 <= int(self) <= 127:
                raise ValueError
            return r
        else:
            raise _exceptions.MpdException("Cannot add %s" %type(i))
    def __sub__(self, i):
        """
        MusicalPitch - MusicalPitch = integer
        MusicalPitch - integer = MusicalPitch
        """
        if isinstance(i, MusicalPitch):
            return self.semitone_pitch() - i.semitone_pitch()
        assert isinstance(i, int)
        v = self.semitone_pitch()
        assert 0 <= v - i < 128
        return MusicalPitch.new_from_int(v-i)
    def __int__(self):
        return self.semitone_pitch()
    def __cmp__(self, B):
        if (self is None or self is None):
            return -1
        diff = self - B
        if diff < 0:
            return -1
        elif diff > 0:
            return 1
        else:
            return 0
    def __str__(self):
        return "(MusicalPitch %s)" % self.get_octave_notename()
    def get_user_notename(self):
        # xgettext:no-python-format
        return self._format_notename(_i("notenameformat|%(notename)s"))
    def get_user_octave_notename(self):
        # xgettext:no-python-format
        return self._format_notename(_i("notenameformat|%(notename)s%(oct)s"))
    def get_notename(self):
        return self._format_notename("%(utnotename)s")
    def get_octave_notename(self):
        return self._format_notename("%(utnotename)s%(oct)s")
    def _format_notename(self, format_string):
        """
        utnotename : untranslated notename, solfege-internal format.
        notename  : as the value translated in the po file
        notename2 : lowercase, but capitalized if below the tone c (as
                    "c" is defined internally in solfege.
        suboct :  '' (nothing) for c or higher
                  <sub>1</sub> for c,
                  <sub>2</sub> for c,,
        suboct2:  '' (nothing) for c, and higher
                  <sub>1</sub> for c,,
                  <sub>2</sub> for c,,,
        supoct:   '' (nothing) for tones lower than c'
                  <sup>1</sup> for c'
                  <sup>2</sup> for c'' etc.
        """
        assert -3 < self.m_accidental_i < 3, self.m_accidental_i
        utnotename = ['c', 'd', 'e', 'f', 'g', 'a', 'b'][self.m_notename_i]\
                   + ['eses', 'es', '', 'is', 'isis'][self.m_accidental_i+2]
        notename = "notename|" \
                 + ['c', 'd', 'e', 'f', 'g', 'a', 'b'][self.m_notename_i]\
                 + ['bb', 'b', '', '#', 'x'][self.m_accidental_i+2]
        notename = _i(notename)
        if self.m_octave_i < 0:
            notename2 = notename.capitalize()
        else:
            notename2 = notename
        if self.m_octave_i > 0:
            octave = "'" * self.m_octave_i
        elif self.m_octave_i < 0:
            octave = "," * (-self.m_octave_i)
        else:
            octave = ""
        if self.m_octave_i < 0:
            suboct = "<sub>%s</sub>" % (-self.m_octave_i)
        else:
            suboct = ""
        if self.m_octave_i < -1:
            suboct2 = "<sub>%s</sub>" % (-self.m_octave_i-1)
        else:
            suboct2 = ""
        if self.m_octave_i > 0:
            supoct = "<sup>%s</sup>" % (self.m_octave_i)
        else:
            supoct = ""
        D = {'utnotename': utnotename,
             'notename': notename,
             'notename2': notename2,
             'suboct': suboct,
             'suboct2': suboct2,
             'supoct': supoct,
             'oct': octave}
        try:
            return format_string % D
        except KeyError:
            logging.error("musicalpitch: Bad translation of notenameformat string")
            return "%(notename)s%(oct)s" % D

