# Solfege - free ear training software
# Copyright (C) 2007, 2008, 2011 Tom Cato Amundsen
# License is GPL, see file COPYING


import unittest

from solfege import mpd
from solfege.mpd import elems
from solfege.mpd import engravers

class TestMisc(unittest.TestCase):
    def test_empty(self):
        sc = elems.Score()
        # This has always worked.
        e = engravers.ScoreContext(sc)
        sc.add_staff()
        e = engravers.ScoreContext(sc)

class TestClefs(unittest.TestCase):
    def test_raise_on_bad_clef(self):
        for clef in ('XX', ):
            def f():
                score = mpd.parser.parse_to_score_object(r"\staff{ \clef %s c' }" % clef)
                score.get_engravers(20)
            self.assertRaises(elems.UnknownClefException, f)
    def test_clefs(self):
        testdata =        [('violin', 6),
                           ('treble', 6),
                           ('G', 6),
                           ('G2', 6),
                           ('alto', 0),
                           ('C', 0),
                           ('tenor', -2),
                           ('bass', -6),
                           ('french', 8),
                           ('soprano', 4),
                           ('mezzosoprano', 2),
                           ('baritone', -4),
                           ('varbaritone', -4),
                           ('subbass', -8),
                           ]
        testdata = testdata + [('"%s"' % c, i) for (c, i) in testdata]
        testdata.extend([
            ('"violin_8"', 6 - 7),
            ('"violin_15"', 6 - 14),
            ('"G^8"', 6 + 7),
            ('"G^15"', 6 + 14),
        ])
        for clef, ypos in testdata:
            score = mpd.parser.parse_to_score_object(r"\staff{ \clef %s c' }" % clef)
            sc = engravers.ScoreContext(score)
            eng = sc.m_contexts
            e = [e for e in eng[0] if isinstance(e, mpd.engravers.NoteheadEngraver)][0]
            self.assertEquals(e.m_ypos, ypos, "c' after %s clef is placed wrong" % clef)
    def test_select_clef(self):
        self.assertEquals(mpd.select_clef("c' e'"), "violin")
        self.assertEquals(mpd.select_clef("as e'"), "violin")
        self.assertEquals(mpd.select_clef("a d'"), "bass")
        self.assertEquals(mpd.select_clef("c e'"), "bass")
        self.assertEquals(mpd.select_clef("f e''"), "violin")
        self.assertEquals(mpd.select_clef("g' a"), "violin")
        self.assertEquals(mpd.select_clef("b d'"), "violin")
        self.assertEquals(mpd.select_clef("bes d'"), "violin")
        self.assertEquals(mpd.select_clef("bes des'"), "bass")
        self.assertEquals(mpd.select_clef("ces' cisis'"), "violin")

suite = unittest.makeSuite(TestClefs)
suite.addTest(unittest.makeSuite(TestMisc))

