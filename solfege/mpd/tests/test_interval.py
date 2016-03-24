# Solfege - free ear training software
# Copyright (C) 2007, 2008, 2011 Tom Cato Amundsen
# License is GPL, see file COPYING


import unittest
from solfege.mpd.interval import Interval
from solfege.mpd.musicalpitch import MusicalPitch

class TestInterval(unittest.TestCase):
    def test_constructor(self):
        for s, a, b, c, i, steps in (
                ('p1', 0, 0, 0, 0, 1),
                ('d1', 0, 0, -1, -1, 1),
                ('a1', 0, 0, 1, 1, 1),
                ('p4', 3, 0, 0, 5, 4),
                ('p5', 4, 0, 0, 7, 5),
                ('p8', 0, 1, 0, 12, 8),
                ('d8', 0, 1, -1, 11, 8),
                ('a8', 0, 1, 1, 13, 8),
                ('p11', 3, 1, 0, 17, 11), # octave + fourth
                ('p12', 4, 1, 0, 19, 12), # octave + fifth
                ('p15', 0, 2, 0, 24, 15), # 2*octave
                ('d15', 0, 2, -1, 23, 15), # 2*octave
                ('a15', 0, 2, 1, 25, 15), # 2*octave
                ('m2', 1, 0, -1, 1, 2),
                ('M2', 1, 0, 0, 2, 2),
                ('M3', 2, 0, 0, 4, 3),
                ('M6', 5, 0, 0, 9, 6),
                ('M9', 1, 1, 0, 14, 9),
                ('m10', 2, 1, -1, 15, 10), # tenth
                ('M13', 5, 1, 0, 21, 13), # octave + sixth
                ('m14', 6, 1, -1, 22, 14), # octave + seventh
                ('M16', 1, 2, 0, 26, 16), # 2*octave + second
                ):
            n = Interval(s)
            self.assertEquals((n.m_interval, n.m_octave, n.m_mod), (a, b, c))
            self.assertEquals(repr(n), s)
            self.assertEquals(i, n.get_intvalue())
            self.assertEquals(steps, n.steps())
    def test_addition(self):
        a = MusicalPitch.new_from_notename("c'")
        b = Interval("m2")
        self.assertEquals((a+b).get_octave_notename(), "des'")
    def test_add_d5(self):
        a = MusicalPitch.new_from_notename("b")
        b = Interval("-d5")
        self.assertEquals((a+b).get_octave_notename(), "eis")
        a = MusicalPitch.new_from_notename("bis")
        b = Interval("-d5")
        self.assertEquals((a+b).get_octave_notename(), "eisis")
        a = MusicalPitch.new_from_notename("bisis")
        b = Interval("-d5")
        self.assertEquals((a+b).get_octave_notename(), "fisis")
    def test_new_from_int(self):
        for x in range(-12, 12):
            i = Interval.new_from_int(x)
            a = MusicalPitch.new_from_notename("bisis")
            b = a + i
            self.assertEquals(int(a) + x, int(b))
    def test_get_cname(self):
        for i, s in enumerate((
            "Perfect Unison",
            "Minor Second",
            "Major Second",
            "Minor Third",
            "Major Third",
            "Perfect Fourth",
            "Tritone",
            "Perfect Fifth",
            "Minor Sixth",
            "Major Sixth",
            "Minor Seventh",
            "Major Seventh",
            "Perfect Octave",
            "Minor Ninth",
            "Major Ninth",
            "Minor Tenth",
            "Major Tenth",
            "Perfect Eleventh",
            "Octave + Tritone",
            "Perfect Twelfth",
            "Minor Thirteenth",
            "Major Thirteenth",
            "Minor Fourteenth",
            "Major Fourteenth",
            "Perfect Double Octave",
        )):
            self.assertEquals(Interval.new_from_int(i).get_cname(), s, (i, s))

suite = unittest.makeSuite(TestInterval)

