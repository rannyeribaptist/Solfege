# Solfege - free ear training software
# Copyright (C) 2007, 2008, 2011 Tom Cato Amundsen
# License is GPL, see file COPYING

import unittest
from solfege import mpd
from solfege.testlib import TmpFileBase
from solfege.mpd.track import Track, MidiEventStream
from solfege.mpd.rat import Rat
from solfege import lessonfile
from solfege import cfg

class TmpFile(TmpFileBase):
    parserclass = lessonfile.QuestionsLessonfile

class TestTrack(unittest.TestCase):
    def test_simple1(self):
        t = Track()
        t.note(4, 90, 127)
        self.assertEquals(list(MidiEventStream(t)),
          [('program-change', 0, 0),
           ('volume', 0, 100),
           ('note-on', 0, 90, 127),
           ('notelen-time', Rat(1, 4)),
           ('note-off', 0, 90, 127)])
    def test_1voice_setpatch(self):
        t = Track()
        t.note(4, 90, 127)
        t.set_patch(3)
        t.note(4, 91, 127)
        self.assertEquals(list(MidiEventStream(t)),
          [('program-change', 0, 0),
           ('program-change', 1, 3),
           ('volume', 0, 100),
           ('note-on', 0, 90, 127),
           ('notelen-time', Rat(1, 4)),
           ('note-off', 0, 90, 127),
           ('volume', 1, 100),
           ('note-on', 1, 91, 127),
           ('notelen-time', Rat(1, 4)),
           ('note-off', 1, 91, 127),
           ])
    def test_midi_overlap(self):
        t1 = Track()
        t1.note(8, 92, 121)
        t1.note(8, 90, 122)
        t1.note(8, 92, 123)
        t1.note(8, 94, 124)
        t2 = Track()
        t2.note(2, 90, 120)
        m = MidiEventStream(t1, t2)
        self.assertEquals("p0:0 p1:0 v0:100 n0:92 n0:90 d1/8 o92 v1:100 n1:90 d1/8 o90 n0:92 d1/8 o92 n0:94 d1/8 o94 o90", m.str_repr(1))


class TestMidiEventStream(TmpFile):
    def setUp(self):
        TmpFile.setUp(self)
        cfg.set_bool('config/override_default_instrument', True)
    def test_track1(self):
        t = Track()
        t.prepend_patch(33)
        t.note(4, 60, 120)
    def test_3instr(self):
        t1 = Track()
        t1.set_patch(3)
        t1.note(4, 93, 127)
        t2 = Track()
        t2.set_patch(4)
        t2.note(4, 94, 127)
        t3 = Track()
        t3.set_patch(5)
        t3.note(4, 95, 127)
        self.assertEquals(list(MidiEventStream(t1, t2, t3)),
           [('program-change', 0, 3),
            ('program-change', 1, 4),
            ('program-change', 2, 5),
            ('volume', 0, 100),
            ('note-on', 0, 93, 127),
            ('volume', 1, 100),
            ('note-on', 1, 94, 127),
            ('volume', 2, 100),
            ('note-on', 2, 95, 127),
            ('notelen-time', Rat(1, 4)),
            ('note-off', 0, 93, 127),
            ('note-off', 1, 94, 127),
            ('note-off', 2, 95, 127)])
        self.assertEquals(MidiEventStream(t1, t2, t3).str_repr(details=1),
            "p0:3 p1:4 p2:5 v0:100 n0:93 v1:100 n1:94 v2:100 n2:95 d1/4 o93 o94 o95")
    def test_str_repr(self):
        t1 = Track()
        t1.set_volume(88)
        t1.set_patch(3)
        t1.note(4, 93, 127)
        t2 = Track()
        t2.set_patch(4)
        t2.note(4, 94, 127)
        t3 = Track()
        t3.set_patch(5)
        t3.note(4, 95, 127)
        self.assertEquals(list(MidiEventStream(t1, t2, t3)),
           [
            ('program-change', 0, 3),
            ('program-change', 1, 4),
            ('program-change', 2, 5),
            ('volume', 0, 88),
            ('note-on', 0, 93, 127),
            ('volume', 1, 100),
            ('note-on', 1, 94, 127),
            ('volume', 2, 100),
            ('note-on', 2, 95, 127),
            ('notelen-time', Rat(1, 4)),
            ('note-off', 0, 93, 127),
            ('note-off', 1, 94, 127),
            ('note-off', 2, 95, 127)])
        self.assertEquals(MidiEventStream(t1, t2, t3).str_repr(details=1),
            "p0:3 p1:4 p2:5 v0:88 n0:93 v1:100 n1:94 v2:100 n2:95 d1/4 o93 o94 o95")
    def test_track2(self):
        self.do_file("""
        header { random_transpose = no }
        question { music = music("\staff{ c'' }"
                                + "\\addvoice{ e' }"
                                + "\staff{ c }")
        }
        """)
        self.p._idx = 0
        tracklist = mpd.music_to_tracklist(self.p.get_question()['music'].get_mpd_music_string(self.p))
    def test_track3(self):
        self.do_file("""
        header { random_transpose = no }
        question { music = music("\staff{ c''1 c''1 }"
                                + "\\addvoice{ r4 e'2. e'1 }"
                                + "\staff{ r4 r g2 g1 }"
                                + "\\addvoice{ r4 r r c c1}")
        }
        """)
        self.p._idx = 0
        tracklist = mpd.music_to_tracklist(self.p.get_question()['music'].get_mpd_music_string(self.p))
        track_fasit = ["n72 d1/1 o72 n72 d1/1 o72",
                       "d1/4 n64 d3/4 o64 n64 d1/1 o64",
                       "d1/2 n55 d1/2 o55 n55 d1/1 o55",
                       "d3/4 n48 d1/4 o48 n48 d1/1 o48"]
        for idx, correct in enumerate(track_fasit):
            self.assertEquals(tracklist[idx].str_repr(), correct)
        for idx in range(4):
            tracklist[idx].prepend_patch(idx + 1)
            track_fasit[idx] = "p%i " % (idx + 1) + track_fasit[idx]
        for idx, correct in enumerate(track_fasit):
            self.assertEquals(tracklist[idx].str_repr(), correct)
        self.assertEquals(MidiEventStream(*tracklist).str_repr(details=1),
          "p0:1 p1:2 p2:3 p3:4 v0:100 n0:72 d1/4 "
          "v1:100 n1:64 d1/4 "
          "v2:100 n2:55 d1/4 "
          "v3:100 n3:48 d1/4 "
          "o72 o64 o55 o48 "
          "n0:72 n1:64 n2:55 n3:48 d1/1 "
          "o72 o64 o55 o48")
    def test_track3_1(self):
        self.do_file("""
        header { random_transpose = no }
        question { music = music("\staff{ c''1 c''1 }"
                                + "\staff{ r4 r g2 g1 }")
        }
        """)
        self.p._idx = 0
        tracklist = mpd.music_to_tracklist(self.p.get_question()['music'].get_mpd_music_string(self.p))
        track_fasit = ["n72 d1/1 o72 n72 d1/1 o72",
                       "d1/2 n55 d1/2 o55 n55 d1/1 o55"]
        for idx, correct in enumerate(track_fasit):
            self.assertEquals(tracklist[idx].str_repr(), correct)
        for idx in range(2):
            tracklist[idx].prepend_patch(idx + 1)
            track_fasit[idx] = "p%i " % (idx + 1) + track_fasit[idx]
        for idx, correct in enumerate(track_fasit):
            self.assertEquals(tracklist[idx].str_repr(), correct)
        self.assertEquals(MidiEventStream(*tracklist).str_repr(details=1),
          "p0:1 p1:2 v0:100 n0:72 d1/2 v1:100 n1:55 d1/2 o72 o55 n0:72 n1:55 d1/1 o72 o55")
    def test_track3_2(self):
        self.do_file(r"""
        header { random_transpose = no }
        question { music = music("\staff{ c''1 c''1 }"
                                + "\staff{ r4 r g2 g1 }"
                                + "\staff{ r4 r r c c1}")
        }
        """)
        self.p._idx = 0
        tracklist = mpd.music_to_tracklist(self.p.get_question()['music'].get_mpd_music_string(self.p))
        track_fasit = ["n72 d1/1 o72 n72 d1/1 o72",
                       "d1/2 n55 d1/2 o55 n55 d1/1 o55",
                       "d3/4 n48 d1/4 o48 n48 d1/1 o48"]
        for idx, correct in enumerate(track_fasit):
            self.assertEquals(tracklist[idx].str_repr(), correct)
        for idx in range(3):
            tracklist[idx].prepend_patch(idx + 1)
            track_fasit[idx] = "p%i " % (idx + 1) + track_fasit[idx]
        for idx, correct in enumerate(track_fasit):
            self.assertEquals(tracklist[idx].str_repr(), correct)
        self.assertEquals(MidiEventStream(*tracklist).str_repr(details=1),
          "p0:1 p1:2 p2:3 v0:100 n0:72 d1/2 "
          "v1:100 n1:55 d1/4 "
          "v2:100 n2:48 d1/4 "
          "o72 o55 o48 "
          "n0:72 n1:55 n2:48 d1/1 "
          "o72 o55 o48")
    def test_bug1(self):
        """
        For each moment in time, all note-off events have to be
        done before the note-on events. This to avoid problems
        with the same note being played two times after each other
        in different tracks.
        """
        t1 = Track()
        t1.set_patch(3)
        t1.note(4, 93, 127)
        t1.note(4, 95, 127)
        t2 = Track()
        t2.set_patch(4)
        t2.note(4, 95, 127)
        t2.note(4, 97, 127)
        self.assertEquals(list(MidiEventStream(t1, t2)),
           [('program-change', 0, 3),
            ('program-change', 1, 4),
            ('volume', 0, 100),
            ('note-on', 0, 93, 127),
            ('volume', 1, 100),
            ('note-on', 1, 95, 127),
            ('notelen-time', Rat(1, 4)),
            ('note-off', 0, 93, 127),
            ('note-off', 1, 95, 127),
            ('note-on', 0, 95, 127),
            ('note-on', 1, 97, 127),
            ('notelen-time', Rat(1, 4)),
            ('note-off', 0, 95, 127),
            ('note-off', 1, 97, 127)])
        self.assertEquals(MidiEventStream(t1, t2).str_repr(details=1),
            "p0:3 p1:4 v0:100 n0:93 v1:100 n1:95 d1/4 o93 o95 n0:95 n1:97 d1/4 o95 o97")
    def test_melodic_interval_2_tracks(self):
        """
        In this test, only MIDI channel 0 will be allocated, even though
        two different patches and volumes are used. This because the tones
        from the two tracks does not sound at the same time.
        """
        t1 = Track()
        t1.set_patch(1)
        t1.set_volume(101)
        t1.note(4, 64)
        t2 = Track()
        t2.set_patch(2)
        t2.set_volume(102)
        t2.notelen_time(4)
        t2.note(4, 66)
        self.assertEquals(t1.str_repr(), "p1 v101 n64 d1/4 o64")
        self.assertEquals(t2.str_repr(), "p2 v102 d1/4 n66 d1/4 o66")
        m = MidiEventStream(t1, t2)
        self.assertEquals(m.str_repr(1),
            "p0:1 p1:2 v0:101 n0:64 d1/4 o64 v1:102 n1:66 d1/4 o66")
    def test_patch_volume_order(self):
        """
        Assert that the order of set_patch and set_volume does not matter.
        """
        t1 = Track()
        t1.set_patch(1)
        t1.set_volume(101)
        t1.note(4, 64)
        self.assertEquals(MidiEventStream(t1).str_repr(details=1), "p0:1 v0:101 n0:64 d1/4 o64")
        # Then with patch and volume in reverse order
        t1 = Track()
        t1.set_volume(101)
        t1.set_patch(1)
        t1.note(4, 64)
        self.assertEquals(MidiEventStream(t1).str_repr(details=1), "p0:1 v0:101 n0:64 d1/4 o64")
    def test_prepend_patch(self):
        """
        If multiple set_patch is done, the last will be used.
        """
        t = Track()
        t.prepend_patch(2)
        t.prepend_patch(3)
        t.note(4, 55)
        self.assertEquals(MidiEventStream(t).str_repr(),
                "p0:2 v0:100 n55 d1/4 o55")
    def test_set_patch(self):
        """
        If multiple set_patch is done, the last will be used.
        """
        t = Track()
        t.set_patch(2)
        t.set_patch(3)
        t.note(4, 55)
        self.assertEquals(MidiEventStream(t).str_repr(),
                "p0:3 v0:100 n55 d1/4 o55")
    def test_set_patch2(self):
        """
        Assert that there is not sendt a new volume event when we change patch.
        """
        t = Track()
        t.set_patch(2)
        t.note(4, 55)
        t.set_patch(3)
        t.note(4, 57)
        self.assertEquals(MidiEventStream(t).str_repr(),
                "p0:2 p1:3 v0:100 n55 d1/4 o55 v1:100 n57 d1/4 o57")
    def test_set_volume(self):
        """
        Assert that there is not sendt a new pacth event when we change volume
        """
        t = Track()
        t.set_volume(98)
        t.note(4, 55)
        t.set_volume(99)
        t.note(4, 57)
        self.assertEquals(MidiEventStream(t).str_repr(),
                "p0:0 p1:0 v0:98 n55 d1/4 o55 v1:99 n57 d1/4 o57")
    def test_set_bpm(self):
        t = Track()
        t.set_bpm(120)
        t.note(4, 50)
        self.assertEquals(MidiEventStream(t).str_repr(1),
            "t120/4 p0:0 v0:100 n0:50 d1/4 o50")
    def test_set_bpm2(self):
        """
        Two set_bpm in a row should only generate MIDI events for the
        last one.
        """
        t = Track()
        t.set_bpm(120)
        t.set_bpm(121)
        t.note(4, 50)
        self.assertEquals(MidiEventStream(t).str_repr(1),
            "t121/4 p0:0 v0:100 n0:50 d1/4 o50")
    def test_set_bpm3(self):
        """
        When two tracks set a different tempo, the tempo from the
        last track is used. There is not issues two MIDI events.
        """
        t1 = Track()
        t1.set_bpm(120)
        t1.note(4, 50)
        t2 = Track()
        t2.set_bpm(121)
        t2.note(4, 55)
        self.assertEquals(MidiEventStream(t1, t2).str_repr(1),
            "t121/4 p0:0 v0:100 n0:50 n0:55 d1/4 o50 o55")
    def test_x1(self):
        t1 = Track()
        t1.set_patch(1)
        t1.note(4, 60)
        t1.set_patch(2)
        t1.note(4, 60)
        t1.set_patch(3)
        t1.note(4, 60)
        t1.set_patch(4)
        t1.note(4, 60)
        m = MidiEventStream(t1)
        self.assertEquals("p0:1 p1:2 p2:3 p3:4 v0:100 n0:60 d1/4 o60 v1:100 n1:60 d1/4 o60 v2:100 n2:60 d1/4 o60 v3:100 n3:60 d1/4 o60", m.str_repr(1))
    def test_x2(self):
        t1 = Track()
        t1.note(4, 62)
        t1.note(4, 60)
        t1.note(2, 62)
        t2 = Track()
        t2.note(1, 60)
        m = MidiEventStream(t1, t2)
        self.assertEquals("p0:0 p1:0 v0:100 n0:62 n0:60 d1/4 o62 v1:100 n1:60 d1/4 o60 n0:62 d1/2 o62 o60", m.str_repr(1))
    def test_x3(self):
        t1 = Track()
        t1.note(4, 62)
        t1.note(4, 60)
        t1.note(2, 62)
        t2 = Track()
        t2.note(1, 60)
        m = MidiEventStream(t1, t2)
        m.num_MIDI_channels = 1
        # We don't handle running out of MIDI channels yet
        self.assertRaises(Exception, m.str_repr, 1)


class TestChannelDevice(unittest.TestCase):
    def setUp(self):
        self.cd = MidiEventStream.ChannelDevice()
    def test_1(self):
        ch_dev = MidiEventStream.ChannelDevice()
        self.assertEquals(0, ch_dev.require_channel(60, 0, 100))
        ch_dev.start_note(0, 60)
        self.assertEquals(1, ch_dev.require_channel(61, 1, 100))
        ch_dev.start_note(1, 61)
        self.assertEquals(2, ch_dev.require_channel(62, 1, 70))
        ch_dev.start_note(2, 62)
        self.assertEquals(0, ch_dev.require_channel(63, 0, 100))
        ch_dev.start_note(0, 63)
        # New channel since we want to play another tone with the
        # same pitch as the one playing in channel 0
        self.assertEquals(3, ch_dev.require_channel(63, 0, 100))
        ch_dev.start_note(3, 63)
        ch_dev.stop_note(0, 60)
        ch_dev.stop_note(1, 61)
        ch_dev.stop_note(2, 62)
        ch_dev.stop_note(0, 63)
        self.assertEquals(0, ch_dev.require_channel(63, 0, 100))
        ch_dev.start_note(0, 63)

suite = unittest.makeSuite(TestTrack)
suite.addTest(unittest.makeSuite(TestMidiEventStream))
suite.addTest(unittest.makeSuite(TestChannelDevice))

