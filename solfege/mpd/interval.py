# GNU Solfege - free ear training software
# Copyright (C) 2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2011  Tom Cato Amundsen
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
The Interval class is a class that is used to do math with
intervals and musical pitches. You use this class if you
need to know the difference between an augmented second and
a minor third. If you don't require this you can probably
ise the simpler function mpdutils.int_to_intervalname
"""

import re
from solfege.mpd import _exceptions

# We have to list all possible interval names here so that xgettext
# can find them and add them to the .pot file for translation. We
# cannot translate the interval quality and interval number separately
# because we don't know how to concat them on other languages.
if 0:
    _("Perfect Unison")
    _("Diminished Unison")
    _("Augmented Unison")
    #
    _("Diminished Second")
    _("Minor Second")
    _("Major Second")
    _("Augmented Second")
    #
    _("Diminished Third")
    _("Minor Third")
    _("Major Third")
    _("Augmented Third")
    #
    _("Diminished Fourth")
    _("Perfect Fourth")
    _("Augmented Fourth")
    #
    _("Diminished Fifth")
    _("Perfect Fifth")
    _("Augmented Fifth")
    #
    _("Diminished Sixth")
    _("Minor Sixth")
    _("Major Sixth")
    _("Augmented Sixth")
    #
    _("Diminished Seventh")
    _("Minor Seventh")
    _("Major Seventh")
    _("Augmented Seventh")
    #
    _("Diminished Octave")
    _("Perfect Octave")
    _("Augmented Octave")
    # translators: Only translate the word after interval| , and don't include
    # interval| in the translated string. So for Norwegians, translate
    # "interval|Diminished" to "Forminsket". Do similar for all strings
    # that are preceded with "interval|"
    _("Minor Ninth")
    _("Major Ninth")
    _("Minor Tenth")
    _("Major Tenth")
    _("interval|Unison")
    _("interval|Second")
    _("interval|Third")
    _("interval|Fourth")
    _("interval|Fifth")
    _("interval|Sixth")
    _("interval|Seventh")
    _("interval|Octave")
    _("interval|Ninth")
    _("interval|Tenth")
    #
    _("interval|Diminished")
    _("interval|Perfect")
    _("interval|Augmented")
    _("interval|Minor")
    _("interval|Major")
    _("interval|Doubly-diminished")
    _("interval|Doubly-augmented")


min_interval = -24
max_interval = 24

short_name = (
    # translators: Sorry for changing a few of these interval names.
    # I want to follow the naming used by wikipedia an others.
    # See http://www.solfege.org/translate for important details
    # These strings are used as button labels for the check buttons
    # selecting which intervals to ask for.
    _i("interval|P1"),
    # translators: m2 is a short version of minor second
    _i("interval|m2"),
    # translators: M2 is a short string for major second
    _i("interval|M2"),
    # translators: m3 is a short string for minor third
    _i("interval|m3"),
    # translators: M3 is a short string for major third
    _i("interval|M3"),
    # translators: 4 is a short string for perfect fourth
    _i("interval|4"),
    # translators: TT is a short string for tritone
    _i("interval|TT"),
    # translators: 5 is a short string for perfect fifth
    _i("interval|P5"),
    # translators: m6 is a short string for minor sixth
    _i("interval|m6"),
    # translators: M6 is a short string for major sixth
    _i("interval|M6"),
    # translators: m7 is a short string for minor seventh
    _i("interval|m7"),
    # translators: M7 is a short string for major seventh
    _i("interval|M7"),
    # translators: 8 is a short string for perfect octave
    _i("interval|P8"),
    # translators: m9 is a short string for minor ninth
    _i("interval|m9"),
    # translators: M9 is a short string for major ninth
    _i("interval|M9"),
    # translators: m10 is a short string for minor tenth
    _i("interval|m10"),
    # translators: M10 is a short string for major tenth
    _i("interval|M10"),
    # translators: P11 is a short string for perfect 11th (octave + fourth)
    _i("interval|P11"),
    # translators: d12 is a short string for octave + tritone
    # I considered the name TT8 (tritone+octave), but rejected it.
    _i("interval|d12"),
    # translators: P12 is a short string for perfect 12th (octave + fifth)
    _i("interval|P12"),
    # translators: m13 is a short string for minor 13th (octave + m6)
    _i("interval|m13"),
    # translators: M13 is a short string for major 13th (octave + M6)
    _i("interval|M13"),
    # translators: m14 is a short string for minor 14th (octave + m7)
    _i("interval|m14"),
    # translators: M14 is a short string for major 14th (octave + M7)
    _i("interval|M14"),
    # translators: P15 is a short string for perfect double octave
    _i("interval|P15"),
    )

def number_name(steps):
    try:
        return {
            1: "Unison",
            2: "Second",
            3: "Third",
            4: "Fourth",
            5: "Fifth",
            6: "Sixth",
            7: "Seventh",
            8: "Octave",
            9: "Ninth",
            10: "Tenth",
            11: "Eleventh",
            12: "Twelfth",
            13: "Thirteenth",
            14: "Fourteenth",
            15: "Double Octave"}[steps]
    except KeyError:
        return "%ith" % steps

class InvalidIntervalnameException(_exceptions.MpdException):
    def __init__(self, notename):
        _exceptions.MpdException.__init__(self)
        self.m_intervalname = notename
    def __str__(self):
        return _("Invalid interval name: %s") % self.m_intervalname


class Interval:
    """
    The interval is internally a interval less than octave
    pluss n octaves. The data variables:
      m_dir
      m_octave
      m_interval
      m_mod
    should NOT be touched by anyone, except MusicalPitch.__add__
    """
    _nn_to_interval_quality = {
        'p': 'Perfect',
        'dd': 'Doubly-diminished',
        'd': 'Diminished',
        'm': 'Minor',
        'M': 'Major',
        'a': 'Augmented',
        'aa': 'Doubly-augmented',
        }
    def __init__(self, iname=None):
        self.m_dir = 1 # value as to be 1 or -1 for initialised obj
        self.m_octave = 0 # 0, 1, 2, 3 etc
        self.m_interval = 0 # 0:unison, 1:seond, ... 6: septim
        # unison:              dim   perfect   aug
        # second:  -2:dim -1:minor 0:major   1:aug
        # third:      dim    minor   major     aug
        # fourth:              dim   perfect   aug
        # fifth:               dim   perfect   aug
        # sixth:      dim    minor   major     aug
        # seventh:    dim    minor   major     aug
        self.m_mod = 0
        if iname:
            self.set_from_string(iname)
    def nn_to_translated_quality(interval_quality):
        """
        Return translated interval quality from internal short string.
        interval_quality can be: dd, d, m, M, a, a, p
        The C locale will return english names, as 'Perfect' and 'Diminished'
        """
        # Hack, just to xgettext should not grab the string for translation
        xgettext_wont_find_us = _i
        return xgettext_wont_find_us("interval|%s" % Interval._nn_to_interval_quality[interval_quality].title())
    nn_to_translated_quality = staticmethod(nn_to_translated_quality)
    def errorcheck(self):
        assert 0 <= self.m_interval <= 6
        assert -2 <= self.m_mod <= 1 # should be increased to -3 <= x <= 2
        assert self.m_octave >= 0
        assert self.m_dir in (-1, 1)
    def _set(self, direction, interval, mod, octave):
        self.m_dir = direction
        self.m_interval = interval
        self.m_mod = mod
        self.m_octave = octave
        if __debug__:
            self.errorcheck()
        return self
    def new_from_int(i):
        assert isinstance(i, int)
        new_int = Interval()
        new_int.set_from_int(i)
        return new_int
    new_from_int = staticmethod(new_from_int)
    def set_from_int(self, i):
        """It returns self to allow chaining: set_from_int(4).pretty_name()
        """
        if i < 0:
            self.m_dir = -1
        else:
            self.m_dir = 1
        self.m_octave = abs(i) / 12
        self.m_mod, self.m_interval = (
               (0, 0),          # unison
               (-1, 1), (0, 1), # second
               (-1, 2), (0, 2), # third
               (0, 3),          # fourth
               (-1, 4),         # dim 5, tritone
               (0, 4),          # fifth
               (-1, 5), (0, 5), # sixth
               (-1, 6), (0, 6))[abs(i) % 12] # seventh
        return self
    def set_from_string(self, s):
        """
        unison  p1
        second  m2 M2
        third   m3 M3
        fourth  p4
        fifth   d5 5
        sixth   m6 M6
        seventh m7 M7
        octave  p8
        ninth    m9 M9
        tenth   m10 M10
        """
        # up or down
        s_orig = s[:]
        s = s.strip()
        if s[0] == "-":
            self.m_dir = -1
            s = s[1:]
        else:
            self.m_dir = 1
        m = re.match("(m|M|d|a|p)(\d+)", s)
        if not m:
            raise InvalidIntervalnameException(s_orig)
        modifier, i = m.groups()
        i = int(i)
        if i <= 7:
            self.m_octave = 0
        else:
            self.m_octave = (i - 1) // 7
        self.m_interval = i - 1 - self.m_octave * 7
        if self.m_interval in (1, 2, 5, 6):
            try:
                self.m_mod = {'d': -2, 'm': -1, 'M': 0, 'a': 1}[modifier]
            except:
                raise InvalidIntervalnameException(s_orig)
        elif self.m_interval in (0, 3, 4):
            try:
                self.m_mod = {'d': -1, 'p': 0, '': 0, 'a': 1}[modifier]
            except:
                raise InvalidIntervalnameException(s_orig)
    def get_intvalue(self):
        if __debug__:
            self.errorcheck()
        return ([0, 2, 4, 5, 7, 9, 11][self.m_interval] + self.m_octave * 12 + self.m_mod) * self.m_dir
    def __str__(self):
        if __debug__:
            self.errorcheck()
        ret = "(Interval %i %imod %io" % (self.m_interval, self.m_mod, self.m_octave)
        if self.m_dir == -1:
            ret = ret + " down)"
        else:
            ret = ret + " up)"
        return ret
    def __repr__(self):
        if self.m_interval in (0, 3, 4):
            return "%s%s" % ({-2: 'dd', -1: 'd', 0: 'p', 1: 'a', 2: 'aa'}[self.m_mod], self.m_interval + 1 + self.m_octave * 7)
        return "%s%s" % ({-2: 'd', -1: 'm', 0: 'M', 1: 'a'}[self.m_mod],  (self.m_interval + 1 + self.m_octave * 7))
    def __eq__(self, interval):
        return self.m_dir == interval.m_dir \
            and self.m_octave == interval.m_octave \
            and self.m_mod == interval.m_mod \
            and self.m_interval == interval.m_interval
    def get_number_name(self):
        """
        Return the translated general name of the interval, like second, third
        etc. (major, minor etc.)
        """
        return _(number_name(self.steps()))
    def get_quality_short(self):
        """
        Return a short string telling the quality.
        This is a non-translated short string mostly used
        internally in the program.
        """
        if self.m_interval in (0, 3, 4):
            return {-2: "dd",
                    -1: "d",
                     0: "p",
                     1: "a",
                     2: "aa"}[self.m_mod]
        else:
            assert self.m_interval in (1, 2, 5, 6)
            return {-2: "d",
                    -1: "m",
                     0: "M",
                     1: "a"}[self.m_mod]
    def get_cname_short(self):
        """
        Return the short untranslated interval name, like p5 or M2
        """
        return "%s%i" % (self.get_quality_short(), self.steps())
    def get_cname(self):
        """
        Return the full untranslated interval name, both the number and quality.
        """
        if self.m_interval == 4 and self.m_mod == -1:
            if self.m_octave == 0:
                return u"Tritone"
            elif self.m_octave == 1:
                return u"Octave + Tritone"
        return u"%s %s" % (
                self._nn_to_interval_quality[self.get_quality_short()],
                number_name(self.steps()))
    def get_name(self):
        """
        Return the full translated intervalname, both the number and quality.
        """
        return _(self.get_cname())
    def steps(self):
        return self.m_octave * 7 + self.m_interval + 1



