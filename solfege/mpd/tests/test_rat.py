# Solfege - free ear training software
# Copyright (C) 2007, 2008, 2011 Tom Cato Amundsen
# License is GPL, see file COPYING

import unittest

from solfege.mpd.rat import Rat

class TestRat(unittest.TestCase):
    def test_constructor(self):
        self.assertEquals(float(Rat(1, 4)), 0.25)
        self.assertEquals(float(Rat(9, 8)), 1.125)
        self.assertEquals(float(Rat(4, 4)), 1.0)
        # I was a little surprised by the following, that 4/4 is not
        # simplified to 1, but I also see that we need it this way
        # for time signatures.
        r = Rat(4, 4)
        self.assertEquals(float(r), 1.0)
        self.assertEquals(r.m_num, 4)
        self.assertEquals(r.m_den, 4)
    def test_addition(self):
        self.assertEquals(Rat(1, 4) + Rat(1, 4), Rat(2, 4))
        self.assertEquals(Rat(3, 4) + Rat(1, 4), Rat(1, 1))
        self.assertEquals(Rat(3, 4) + Rat(1, 4), Rat(2, 2))
        self.assertEquals(Rat(4, 4) + Rat(1, 4), Rat(5, 4))
    def test_subtract(self):
        self.assertEquals(Rat(3, 4) - Rat(1, 4), Rat(1, 2))
    def test_division(self):
        r1 = Rat(1, 2)
        r2 = Rat(1, 2)
        d = r1 / r2
        self.assertEquals(Rat(1, 2) / Rat(1, 2), Rat(1, 1))
        self.assertEquals(Rat(1, 2) / Rat(2, 4), Rat(1, 1))
        self.assertEquals(Rat(1, 4) / 2, Rat(1, 8))
        self.assertEquals(Rat(1, 4) / Rat(3, 2),  Rat(1, 6))
    def test_cmp(self):
        self.assertNotEquals(Rat(4, 3), None)
        self.assertTrue(True)
    def test_listsort(self):
        v = [Rat(0, 4), Rat(3, 8), Rat(1, 8), Rat(1, 4)]
        self.assertEquals(v, [Rat(0, 4), Rat(3, 8), Rat(1, 8), Rat(1, 4)])
        v.sort()
        self.assertEquals(v, [Rat(0, 4), Rat(1, 8), Rat(1, 4), Rat(3, 8)])


suite = unittest.makeSuite(TestRat)
