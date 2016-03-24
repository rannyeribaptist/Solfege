# Solfege - free ear training software
# Copyright (C) 2007, 2008, 2010, 2011 Tom Cato Amundsen
# License is GPL, see file COPYING

import unittest
from solfege.mpd.musicalpitch import MusicalPitch, InvalidNotenameException
from solfege.mpd.elems import *
from solfege.mpd import const
from solfege.mpd import parser
from solfege.mpd import performer
from solfege import mpd

def f3(s):
    return parser.parse_to_score_object(s).get_timelist()

class TestScore(unittest.TestCase):
    def setUp(self):
        self.score = Score()
        self.staff = self.score.add_staff() # default class is Staff
        self.__bp = None
    def get_bp(self):
        # We need a getter for .bp because we cannot create the BarProxy
        # before some elements have been added to the bar.
        if not self.__bp:
            self.__bp = BarProxy(self.score.voice11, Rat(0, 1))
        return self.__bp
    bp = property(get_bp)
    def test_constructor_ok(self):
        # add_staff automatically creates the first voice
        self.assertEquals(len(self.staff.m_voices), 1)
        # and creates the voice shortcut
        self.assertEquals(type(self.score.voice11), Voice)
    def test_add_note(self):
        self.score.voice11.append(Note.new_from_string("c'4"))
        self.score.voice11.append(Note.new_from_string("c'2"))
        self.score.voice11.append(Note.new_from_string("c'8"))
        self.assert_(isinstance(self.score.voice11.m_tdict[Rat(0, 1)]['elem'][0], Note))
        self.assert_(isinstance(self.score.voice11.m_tdict[Rat(0, 1)]['elem'][0].w_parent(), Stem))
        self.assert_(isinstance(self.score.voice11.m_tdict[Rat(0, 1)]['elem'][0].w_parent().w_parent(), Voice))
        # bar full:
        self.assertRaises(Voice.BarFullException, self.score.voice11.append,
            Note.new_from_string("c'4"))
        self.score.voice11.append(Note.new_from_string("c'8"))
        self.score.voice11.append([
            Note.new_from_string("c'1"),
            Note.new_from_string("e'1"),
            Note.new_from_string("g'1"),
        ])
    def test_add_rest(self):
        self.score.voice11.append(Rest(Duration.new_from_string("8")))
        self.assert_(isinstance(self.score.voice11.m_tdict[Rat(0, 1)]['elem'][0], Rest))
        self.assert_(isinstance(self.score.voice11.m_tdict[Rat(0, 1)]['elem'][0].w_parent(), Voice))
    def test_add_bar(self):
        self.assert_(isinstance(self.score.add_bar(TimeSignature(4, 4)), Bar))
        self.score.add_bar(TimeSignature(4, 4))
        self.score.add_bar(TimeSignature(1, 4))
        self.score.add_bar(TimeSignature(1, 4))
        self.assertEquals(self.score.m_bars[0].m_timepos, Rat(0, 1))
        self.assertEquals(self.score.m_bars[1].m_timepos, Rat(1, 1))
        self.assertEquals(self.score.m_bars[2].m_timepos, Rat(2, 1))
        self.assertEquals(self.score.m_bars[3].m_timepos, Rat(9, 4))
    def test_add_bar_autotimesig(self):
        self.score.add_bar(None)
        self.assertEquals(self.score.m_bars[0].m_timesig, TimeSignature(4, 4))
        self.score.add_bar(TimeSignature(5, 8))
        self.assertEquals(self.score.m_bars[1].m_timesig, TimeSignature(5, 8))
        self.score.add_bar(None)
        self.assertEquals(self.score.m_bars[2].m_timesig, TimeSignature(5, 8))
    def test_add_partial_bar(self):
        self.score.add_partial_bar(Duration.new_from_string("4"), TimeSignature(4, 4))
        self.score.add_bar(None)
        self.assertEquals(self.score.m_bars[0].m_timepos, Rat(0, 1))
        self.assertEquals(self.score.m_bars[0].end(), Rat(1, 4))
        self.assertEquals(self.score.m_bars[1].m_timepos, Rat(1, 4))
        self.assertEquals(self.score.get_bar_at(Rat(0, 1)), self.score.m_bars[0])
        self.assertEquals(self.score.get_bar_at(Rat(1, 4)), self.score.m_bars[1])
        self.score.voice11.append(Note.new_from_string("c4"))
        self.score.voice11.append(Note.new_from_string("c1"))
        self.score.voice11.append(Note.new_from_string("c1"))
    def test_get_bar_at(self):
        # Raise exception, since we have not added bars
        self.assertRaises(IndexError, self.score.get_bar_at, Rat(0, 1))
        # None is to get the default timesig 4/4
        self.score.add_bar(None)
        self.assert_(isinstance(self.score.get_bar_at(Rat(0, 1)), Bar))
    def test_set_clef(self):
        self.score.voice11.set_clef("violin")
        self.assertEquals(self.score.staff1.m_tdict[Rat(0, 1)]['clef'].m_name, "violin")
        self.score.voice11.set_clef("bass")
        # The last clef set is remembered
        self.assertEquals(self.score.staff1.m_tdict[Rat(0, 1)]['clef'].m_name, "bass")
        self.score.voice11.append(Note.new_from_string("c'8"))
        self.score.voice11.set_clef("treble")
        self.assertEquals(self.score.staff1.m_tdict[Rat(0, 1)]['clef'].m_name, "bass")
        self.assertEquals(self.score.staff1.m_tdict[Rat(1, 8)]['clef'].m_name, "treble")
    def test_stem_down(self):
        self.score.voice11.append(Note.new_from_string("c'8"))
        self.score.voice11.append(Note.new_from_string("c'8"), const.DOWN)
        self.assertEquals(self.score.voice11.m_tdict[Rat(0, 1)]['elem'].m_stemdir, const.BOTH)
        self.assertEquals(self.score.voice11.m_tdict[Rat(1, 8)]['elem'].m_stemdir, const.DOWN)
    def test_one_voice_in_rhythm_staff(self):
        staff = self.score.add_staff(RhythmStaff)
        self.assertRaises(staff.OnlyOneVoiceException,
            staff.add_voice)
    def test_no_chords_in_rhythm_staff(self):
        self.score.add_staff(RhythmStaff)
        self.score.voice21.append(Note.new_from_string("cis4"))
        self.assertRaises(Voice.NoChordsInRhythmStaffException,
                self.score.voice21.append,
                [Note.new_from_string("gis4"), Note.new_from_string("fis4")])
    def test_is_bar_full(self):
        self.assertTrue(self.score.voice11.is_bar_full())
        self.score.voice11.append(Note.new_from_string("c2"))
        self.assertFalse(self.score.voice11.is_bar_full())
        self.score.voice11.append(Note.new_from_string("c4"))
        self.assertFalse(self.score.voice11.is_bar_full())
        self.score.voice11.append(Note.new_from_string("c4"))
        self.assertTrue(self.score.voice11.is_bar_full())
    def test_midigen_rest(self):
        self.score.voice11.append(Note.new_from_string("c4"))
        self.score.voice11.append(Rest(Duration.new_from_string("4")))
        self.score.voice11.append(Note.new_from_string("c4"))
        t = mpd.score_to_tracks(self.score)
        self.assertEquals(t[0].str_repr(), "n48 d1/4 o48 d1/4 n48 d1/4 o48")
    def test_midigen_tie(self):
        n1 = Note.new_from_string("c4")
        n2 = Note.new_from_string("c4")
        n3 = Note.new_from_string("c4")
        n4 = Note.new_from_string("d4")
        self.score.voice11.append(n1)
        self.score.voice11.append(n2)
        self.score.voice11.append(n3)
        self.score.voice11.append(n4)
        self.score.voice11.tie([n1, n2, n3])
        p = performer.MidiPerformer(self.score)
        t = mpd.score_to_tracks(self.score)
        self.assertEquals(t[0].str_repr(), "n48 d3/4 o48 n50 d1/4 o50")
    def test_tuplets(self):
        n1 = Note(MusicalPitch.new_from_notename("g'"),
                  Duration(8, 0, Rat(2, 3)))
        n2 = Note(MusicalPitch.new_from_notename("g'"),
                  Duration(8, 0, Rat(2, 3)))
        n3 = Note(MusicalPitch.new_from_notename("g'"),
                  Duration(8, 0, Rat(2, 3)))
        self.score.voice11.append(n1)
        self.score.voice11.append(n2)
        self.score.voice11.append(n3)
        self.score.voice11.tuplet(Rat(2, 3), const.UP, [n1, n2, n3])
    def test_single_tuplet(self):
        n1 = Note(MusicalPitch.new_from_notename("g'"),
                  Duration(8, 0, Rat(2, 3)))
        self.score.voice11.append(n1)
        self.score.voice11.tuplet(Rat(2, 3), const.UP, [n1])
        self.assertEquals(n1.w_parent().m_tupletinfo, 'end')
    def test_rh_1(self):
        self.assertEquals(f3(r"\staff{c}"), [[True, Rat(1, 4)]])
        self.assertEquals(f3(r"\staff{c2}"), [[True, Rat(1, 2)]])
        self.assertEquals(f3(r"\staff{c4 c8}"), [
            [True, Rat(1, 4)],
            [True, Rat(1, 8)],
        ])
        self.assertEquals(f3(r"\staff{c4 c4}"), [
            [True, Rat(1, 4)],
            [True, Rat(1, 4)],
        ])
        self.assertEquals(f3(r"\staff{c4. c4}"), [
            [True, Rat(3, 8)],
            [True, Rat(1, 4)],
        ])
        self.assertEquals(f3(r"\staff{c4~ c8 c4}"), [
            [True, Rat(3, 8)],
            [True, Rat(1, 4)],
        ])
    def test_rh_rest(self):
        self.assertEquals(f3(r"\staff{c4 r8 c4}"), [
            [True, Rat(1, 4)],
            [False, Rat(1, 8)],
            [True, Rat(1, 4)],
        ])
        self.assertEquals(f3(r"\staff{c4 r8 r16 c4}"), [
            [True, Rat(1, 4)],
            [False, Rat(3, 16)],
            [True, Rat(1, 4)],
        ])
        self.assertEquals(f3(r"\staff{c4 c8 c8}"), [
            [True, Rat(1, 4)],
            [True, Rat(1, 8)],
            [True, Rat(1, 8)],
        ])
    def test_rh_tie(self):
        self.assertEquals(f3(r"\staff{c4~ c8 c8 r4 c4}"), [
            [True, Rat(3, 8)],
            [True, Rat(1, 8)],
            [False, Rat(1, 4)],
            [True, Rat(1, 4)]
        ])

    def test_rh_1a(self):
        self.assertEquals(f3(r"\staff{c8~ c8~ c8}"), [
            [True, Rat(3, 8)],
        ])
    def test_rh_1b(self):
        self.assertEquals(f3(r"\staff{c4~ c8}"), [
            [True, Rat(3, 8)],
        ])
    def test_rh_2a(self):
        self.assertEquals(f3(r"\staff{c2}\addvoice{c4 c4}"), [
            [True, Rat(1, 4)],
            [True, Rat(1, 4)],
        ])
    def test_rh_2b(self):
        self.assertEquals(f3(r"\staff{c2}\addvoice{c4}"), [
            [True, Rat(1, 2)],
        ])
    def test_rh_2c(self):
        self.assertEquals(f3(r"\staff{c2}\addvoice{r4 c4}"), [
            [True, Rat(1, 4)],
            [True, Rat(1, 4)],
        ])
    def test_rh_2d(self):
        self.assertEquals(f3(r"\staff{c2}\addvoice{r4 r4}"), [
            [True, Rat(1, 2)],
        ])
    def test_rh_2e(self):
        self.assertEquals(f3(r"\staff{c1}\addvoice{r4 g2 r4}"), [
            [True, Rat(1, 4)],
            [True, Rat(3, 4)],
        ])
    def test_rh_3(self):
        self.assertEquals(f3(r"\staff{c4}"), [
            [True, Rat(1, 4)],
        ])
        self.assertEquals(f3(r"\staff{c4 c8}"), [
            [True, Rat(1, 4)],
            [True, Rat(1, 8)]])
        self.assertEquals(f3(r"\staff{c4 c8}"), [
            [True, Rat(1, 4)],
            [True, Rat(1, 8)]])
        self.assertEquals(f3(r"\staff{c4 c8 c8}"), [
            [True, Rat(1, 4)],
            [True, Rat(1, 8)],
            [True, Rat(1, 8)]])
        self.assertEquals(f3(r"""\staff\relative c{
c4 c8 c8
}"""), [
            [True, Rat(1, 4)],
            [True, Rat(1, 8)],
            [True, Rat(1, 8)]])
    def test_bar_fill_skips(self):
        n1 = Note(MusicalPitch.new_from_notename("g'"),
                  Duration(4, 0))
        self.score.voice11.append(n1)
        self.score.voice11.append(Rest(Duration.new_from_string("4")))
        self.bp.fill_skips()
        self.assertTrue(isinstance(self.score.voice11.m_tdict[Rat(0, 1)]['elem'][0], Note))
        self.assertTrue(isinstance(self.score.voice11.m_tdict[Rat(1, 4)]['elem'][0], Rest))
        self.assertTrue(isinstance(self.score.voice11.m_tdict[Rat(1, 2)]['elem'][0], Skip))
        self.assertTrue(isinstance(self.score.voice11.m_tdict[Rat(3, 4)]['elem'][0], Skip))
    def test_repack_bar_1(self):
        """
        We delete one note, and sees that the bar is packed correctly.
        """
        self.score.voice11.append(Note.new_from_string("c4"))
        self.score.voice11.append(Note.new_from_string("d4"))
        self.score.voice11.append(Note.new_from_string("e4"))
        self.score.voice11.append(Note.new_from_string("d4"))
        self.assertEquals(sorted(self.score.voice11.m_tdict.keys()),
            [Rat(0, 1), Rat(1, 4), Rat(1, 2), Rat(3, 4)])
        del self.score.voice11.m_tdict[Rat(1, 2)]
        self.assertEquals(sorted(self.score.voice11.m_tdict.keys()),
            [Rat(0, 1), Rat(1, 4), Rat(3, 4)])
        self.bp.repack()
        self.assertEquals(sorted(self.score.voice11.m_tdict.keys()),
            [Rat(0, 1), Rat(1, 4), Rat(1, 2)])
    def test_repack_bar_2(self):
        """
        One note is changed from 1/4 to 1/2 length. Then we call
        bar.repack(voice11) and we see that the last note is moved
        further out in the bar. This works ok since the bar was not
        full. There where not Skips at the end of the bar.
        """
        self.score.voice11.append(Note.new_from_string("c4"))
        self.score.voice11.append(Note.new_from_string("d4"))
        self.score.voice11.append(Note.new_from_string("e4"))
        self.assertEquals(sorted(self.score.voice11.m_tdict.keys()),
            [Rat(0, 1), Rat(1, 4), Rat(1, 2)])
        self.score.voice11.m_tdict[Rat(1, 4)]['elem'][0] = Note.new_from_string("g2")
        self.assertEquals(sorted(self.score.voice11.m_tdict.keys()),
            [Rat(0, 1), Rat(1, 4), Rat(1, 2)])
        self.bp.repack()
        self.assertEquals(sorted(self.score.voice11.m_tdict.keys()),
            [Rat(0, 1), Rat(1, 4), Rat(3, 4)])
    def test_repack_bar_3(self):
        """
        One note is changed from 1/4 to 1/1 length. Then we call
        bar.repack and a BarFullException is raised.
        """
        self.score.voice11.append(Note.new_from_string("c4"))
        self.score.voice11.append(Note.new_from_string("d4"))
        self.score.voice11.append(Note.new_from_string("e4"))
        self.assertEquals(sorted(self.score.voice11.m_tdict.keys()),
            [Rat(0, 1), Rat(1, 4), Rat(1, 2)])
        self.score.voice11.m_tdict[Rat(1, 4)]['elem'][0] = Note.new_from_string("g1")
        self.assertEquals(sorted(self.score.voice11.m_tdict.keys()),
            [Rat(0, 1), Rat(1, 4), Rat(1, 2)])
        self.assertRaises(Voice.BarFullException, self.bp.repack)
    def test_get_timeposes_of(self):
        self.score.add_bar(TimeSignature(4, 4))
        self.score.add_bar(TimeSignature(4, 4))
        self.assertEquals(
            self.score.voice11.get_timeposes_of(self.score.m_bars[0]), [])
        self.assertEquals(
            self.score.voice11.get_timeposes_of(self.score.m_bars[1]), [])
        self.score.voice11.append(Note.new_from_string("c4"))
        self.assertEquals(
            self.score.voice11.get_timeposes_of(self.score.m_bars[0]),
            [Rat(0, 1)])
        self.assertEquals(
            self.score.voice11.get_timeposes_of(self.score.m_bars[1]), [])
    def test_get_time_pitch_list(self):
        def f(s, tempo=(60, 4)):
            s = parser.parse_to_score_object(r"\staff{ %s}" % s)
            return s.voice11.get_time_pitch_list(tempo)
        self.assertEquals(f("c4 d4"), [(48, 1.0), (50, 1.0)])
        self.assertEquals(f("c4 d2"), [(48, 1.0), (50, 2.0)])
        self.assertEquals(f("c4 d2", (120, 4)), [(48, 0.5), (50, 1.0)])
        self.assertEquals(f(r" \times 2/3 { c4 d2 }"), [(48, 2.0/3), (50, 4.0/3)])
        self.assertEquals(f("c4 r8. d4"), [(48, 1.0), (-1, 0.75), (50, 1.0)])
        self.assertRaises(Voice.NotUnisonException, f, "<c4 d4>")
    def test_is_last(self):
        voice = self.score.voice11
        voice.append(Note.new_from_string("c2"))
        voice.append(Note.new_from_string("d2"))
        voice.append(Note.new_from_string("f1"))
        voice.append(Note.new_from_string("g4"))
        self.assertTrue(voice.is_last(Rat(1, 2)))
        self.assertFalse(voice.is_last(Rat(0, 1)))
        self.assertTrue(voice.is_last(Rat(1, 2)))
        self.assertTrue(voice.is_last(Rat(1, 1)))
        self.assertFalse(voice.is_last(Rat(2, 1)))
    def test_partial_bar(self):
        voice = self.score.voice11


class TestNote(unittest.TestCase):
    def setUp(self):
        self.score = Score()
        self.staff = self.score.add_staff() # default class is Staff
    def test_contructor(self):
        n = Note(MusicalPitch.new_from_notename("c'"),
                 Duration.new_from_string("4."))
        self.assertRaises(AssertionError,
                          Note, "4.", MusicalPitch.new_from_notename("c'"))
        self.assertRaises(AssertionError,
                          Note, Duration.new_from_string("4."), "c'")
    def test_new_from_string(self):
        n = Note.new_from_string("c'4.")
        self.assertRaises(InvalidNotenameException, Note.new_from_string, "x")
    def test_beam(self):
        voice = self.score.voice11
        n1 = Note.new_from_string("c'8")
        n2 = Note.new_from_string("d'8")
        voice.append(n1)
        voice.append(n2)
        voice.beam([n1, n2])
        voice2 = self.score.staff1.add_voice()
        n3 = Note.new_from_string("d'8")
        n4 = Note.new_from_string("d'8")
        self.assertRaises(Voice.NoteDontBelongHere, voice.beam, [n3, n4])
    def test_tie_2notes(self):
        voice = self.score.voice11
        n1 = Note.new_from_string("c'4")
        n2 = Note.new_from_string("c'8")
        voice.append(n1)
        voice.append(n2)
        voice.tie([n1, n2])
    def test_tie_3notes(self):
        voice = self.score.voice11
        n1 = Note.new_from_string("c'4")
        n2 = Note.new_from_string("c'4")
        n3 = Note.new_from_string("c'4")
        voice.append(n1)
        voice.append(n2)
        voice.append(n3)
        voice.tie([n1, n2, n3])


class TestBarProxy(unittest.TestCase):
    def setUp(self):
        self.score = Score()
        self.staff = self.score.add_staff()
        v = self.score.voice11
        v.append(Note.new_from_string("c'4"))
        v.append(Note.new_from_string("d'2"))
        v.append(Note.new_from_string("c'4"))
        v.append(Note.new_from_string("c'4"))
        v.append(Note.new_from_string("c'4"))
        v.append(Note.new_from_string("c'4"))
        v.append(Note.new_from_string("c'4"))
    def test_1(self):
        bp = BarProxy(self.score.voice11, Rat(0, 1))
        bp.remove_trailing(Rat(1, 4))
        bp.pop_last_elem()
        bp.remove_skips()
        bp.repack()
        bp.fill_skips()
        bp.end()

suite = unittest.makeSuite(TestScore)
suite.addTest(unittest.makeSuite(TestNote))
suite.addTest(unittest.makeSuite(TestBarProxy))

