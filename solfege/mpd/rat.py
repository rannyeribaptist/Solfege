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
def gcd(a, b):
    while b:
        a, b = b, a % b
    return a

class Rat(object):
    __slots__ = ('m_num', 'm_den')
    """
    This is NOT a generic rational number class, it includes
    only the features needed for the the soundcard and mpd
    module included in Solfege.
    """
    def __init__(self, num, den=1):
        assert isinstance(num, int)
        assert isinstance(den, int)
        self.m_num = num
        self.m_den = den
    def clone(self):
        return Rat(self.m_num, self.m_den)
    def __repr__(self):
        return "(Rat %i/%i)" % (self.m_num, self.m_den)
    def __str__(self):
        return "(Rat %i/%i)" % (self.m_num, self.m_den)
    def __add__(self, B):
        assert isinstance(self, Rat)
        assert isinstance(B, Rat)
        a = self.m_num * B.m_den + B.m_num * self.m_den
        b = self.m_den * B.m_den
        g = gcd(a, b)
        return Rat(a/g, b/g)
    def __sub__(self, B):
        assert isinstance(self, Rat)
        assert isinstance(B, Rat)
        a = (self.m_num * B.m_den - B.m_num * self.m_den)
        b = self.m_den * B.m_den
        g = gcd(a, b)
        return Rat(a/g, b/g)
    def __mul__(self, B):
        assert isinstance(self, Rat)
        if type(B) == type(0):
            g = gcd(self.m_num*B, self.m_den)
            return Rat(self.m_num*B/g, self.m_den/g)
        assert isinstance(B, Rat)
        g = gcd(self.m_num*B.m_num, self.m_den*B.m_den)
        return Rat(self.m_num*B.m_num/g, self.m_den*B.m_den/g)
    def __rdiv__(self, B):
        """ called when integer / Rat
        """
        assert isinstance(B, int)
        assert isinstance(self, Rat)
        a = B * self.m_den
        b = self.m_num
        g = gcd(a, b)
        return Rat(a/g, b/g)
    def __div__(self, i):
        if isinstance(i, int):
            i = Rat(i, 1)
        r = Rat(self.m_num * i.m_den, self.m_den * i.m_num)
        g = gcd(r.m_num, r.m_den)
        return Rat(r.m_num / g, r.m_den / g)
    def __rmul__(self, B):
        """ called when integer * Rat
        """
        assert isinstance(self, Rat)
        assert isinstance(B, int)
        a = self.m_num * B
        g = gcd(a, self.m_den)
        return Rat(a/g, self.m_den/g)
    def __int__(self):
        return self.m_num / self.m_den
    def __float__(self):
        return 1.0 * self.m_num / self.m_den
    def __hash__(self):
        return hash((self.m_num, self.m_den))
    def __cmp__(self, B):
        if B is None:
            return 1
        return cmp(1.0*self.m_num/self.m_den, 1.0*B.m_num/B.m_den)


