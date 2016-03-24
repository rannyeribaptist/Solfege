# Solfege - free ear training software
# Copyright (C) 2007, 2008, 2011 Tom Cato Amundsen
# License is GPL, see file COPYING

import gettext
import unittest
import doctest

import solfege.mpd.musicalpitch
from solfege.mpd.musicalpitch import MusicalPitch
from solfege.mpd.interval import Interval

class TestMusicalPitch(unittest.TestCase):
    def test_normalize_double_accidental(self):
        for a, b in (("c", "c"),
                     ("cisis", "d"),
                     ("disis", "e"),
                     ("eisis", "fis"),
                     ("fisis", "g"),
                     ("gisis", "a"),
                     ("aisis", "b"),
                     ("bisis", "cis'"),
                     ("ceses", "bes,"),
                     ("deses", "c"),
                     ("eses", "d"),
                     ("feses", "ees"),
                     ("geses", "f"),
                     ("ases", "g"),
                     ("beses", "a"),
                     ):
            n = MusicalPitch.new_from_notename(a)
            n.normalize_double_accidental()
            self.assertEquals(n.get_octave_notename(), b)
    def test_add(self):
        n = MusicalPitch.new_from_notename('c')
        n = n + 2
        self.assertEquals(n.get_octave_notename(), 'd')
    def test_subtract(self):
        a = MusicalPitch.new_from_notename("g")
        b = MusicalPitch.new_from_notename("f")
        self.assertEquals(a - b, 2)
    def test_add_integer_fail(self):
        n = MusicalPitch.new_from_int(120)
        self.assertRaises(ValueError, lambda: n + 20)
    def test_add_interval_fail(self):
        n = MusicalPitch.new_from_int(120)
        i = Interval("M10")
        self.assertRaises(ValueError, lambda: n + i)
    def test_internals(self):
        a = MusicalPitch()
        self.assertTrue(a.m_octave_i == a.m_accidental_i == 0)
    def test_trans(self):
        gettext.translation('solfege', './share/locale/', languages=['nb_NO']).install()
        n = MusicalPitch.new_from_notename("b,,")
        self.assertEquals(n.get_octave_notename(), "b,,")
        self.assertEquals(n.get_user_octave_notename(), "<sub>1</sub>H")
        self.assertEquals(n.get_user_notename(), "h")
    def test_pitch_class(self):
        for n, i in (("c", 0), ("cis", 1), ("g", 7), ("ges", 6), ("gisis", 9),
                ("b", 11), ("bis", 0), ("bisis", 1), ("ces", 11)):
            p = MusicalPitch.new_from_notename(n)
            self.assertEquals(p.pitch_class(), i)

suite = unittest.makeSuite(TestMusicalPitch)
suite.addTest(doctest.DocTestSuite(solfege.mpd.musicalpitch))
