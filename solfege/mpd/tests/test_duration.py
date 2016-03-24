# Solfege - free ear training software
# Copyright (C) 2007, 2008, 2011 Tom Cato Amundsen
# License is GPL, see file COPYING

import unittest
import doctest

import solfege.mpd.duration
from solfege.mpd.duration import Duration
from solfege.mpd.rat import Rat

class TestDuration(unittest.TestCase):
    def test_constructor(self):
        for a, b, f in ((1, 0, 1.0), (2, 0, 0.5), (2, 1, 0.75)):
            d = Duration(a, b)
            r = d.get_rat_value()
            self.assertEquals(float(r), f)
    def test_new_from_string(self):
        d = Duration.new_from_string("4")
        self.assertEquals(d.get_rat_value(), Rat(1, 4))
        self.assertRaises(Duration.BadStringException,
            Duration.new_from_string, "44x")
    def test_set_from_rat(self):
        for i in (1, 2, 4, 8, 16, 32, 64):
            d = Duration.new_from_rat(Rat(1, i))
            self.assertEquals(d, Duration(i, 0))
        d = Duration.new_from_rat(Rat(3, 8))
        self.assertEquals(d.get_rat_value(), Rat(3, 8))
    def test_misc(self):
        d1=Duration(4, 0, Rat(1, 1))
        d2=Duration(4, 1, Rat(1, 1))
        self.assertFalse(d1 == d2)
        self.assertEquals(d1.get_rat_value(), Rat(1, 4))
        self.assertEquals(d2.get_rat_value(), Rat(3, 8))
        d3=Duration(4, 2, Rat(2, 3))
        self.assertEquals(d3.get_rat_value(), Rat(7, 24))

suite = unittest.makeSuite(TestDuration)
suite.addTest(doctest.DocTestSuite(solfege.mpd.duration))
