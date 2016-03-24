# Solfege - free ear training software
# vim: set fileencoding=utf-8 :
# Copyright (C) 2007, 2008, 2011 Tom Cato Amundsen
# License is GPL, see file COPYING

from __future__ import absolute_import
from gi.repository import Gtk
import unittest
import time

from solfege.testlib import I18nSetup, TmpFileBase
import solfege.lessonfile
solfege.lessonfile._test_mode = True
from solfege.lessonfile import *
from solfege import dataparser
from solfege import mpd
from solfege.mpd import mpdutils
from solfege import cfg
from solfege import parsetree as pt


class MObjTest(TmpFileBase):
    parserclass = QuestionsLessonfile
    def _m(self, idx=0):
        return self.p.m_questions[idx]['music']


class TestParser(TmpFileBase):
    parserclass = LessonfileCommon
    def test_wrong_argument_count(self):
        try:
            self.do_file('question {\nmusic = music("c e g", "chor") }')
        except pt.FunctionCall.WrongArgumentCount, e:
            self.assertEquals('(line 1): question {\n'
                              '(line 2): music = music("c e g", "chor") }\n'
                              '                        ^',
                              e.m_nonwrapped_text)
        else:
            self.fail("WrongArgumentCount not raised")
    def test_wrong_argument_count_multiline(self):
        try:
            self.do_file('\n'.join([
                'question {',
                'music = music("c e g",',
                '   "chor")',
                '}']))
        except pt.FunctionCall.WrongArgumentCount, e:
            self.assertEquals('(line 1): question {\n'
                              '(line 2): music = music("c e g",\n'
                              '                        ^',
                              e.m_nonwrapped_text)
        else:
            self.fail("WrongArgumentCount not raised")
    def test_exception_functioncall_no_args(self):
        try:
            self.do_file("a=1\n"
                         "b = func() c=3")
        except pt.LookupException, e:
            self.assertEquals("(line 1): a=1\n"
                              "(line 2): b = func() c=3\n"
                              "              ^",
                              e.m_nonwrapped_text)
        else:
            self.fail("LookupException not raised")
    def test_exception_functionsall_two_args(self):
        try:
            self.do_file("a=1\n"
                         "b = func(3, 4) c=3")
        except pt.LookupException, e:
            #self.assertEquals(e.m_token[TOKEN_STRING], 'func')
            self.assertEquals("(line 1): a=1\n"
                              "(line 2): b = func(3, 4) c=3\n"
                              "              ^",
                              e.m_nonwrapped_text)
        else:
            self.fail("LookupError not raised")
    def test_exception_atom(self):
        try:
            self.do_file("a=b")
        except pt.LookupException, e:
            #self.assertEquals(e.m_token[TOKEN_STRING], "b")
            self.assertEquals("(line 1): a=b\n"
                              "            ^",
                              e.m_nonwrapped_text)
        else:
            self.fail("LookupError not raised")
    def test_simplest(self):
        p = self.do_file("a=yes")
        self.assertEquals(p.m_globals['a'], True)
    def test_tempo_tuple(self):
        p = self.do_file("tempo = 240/4")
        self.assertEquals(p.m_globals['tempo'], (240, 4))
    def test_gettext(self):
        p = self.do_file('question {\n' \
            '  name = _("chord|m7")\n' \
            '  iname = _i("chord|m7")\n' \
            '  s = _("Major")\n' \
            '}')
        self.assertEquals(p.m_questions[0].name, "chord|m7")
        self.assertEquals(p.m_questions[0].name.cval, "chord|m7")
        self.assertEquals(p.m_questions[0].iname, "m7")
        self.assertEquals(p.m_questions[0].iname.cval, "chord|m7")
        self.assertEquals(p.m_questions[0].s, "Dur")
        self.assertEquals(p.m_questions[0].s.cval, "Major")
    def test_predef(self):
        self.p.m_module_predefs['treble'] = u'treble'
        p = self.do_file("header { clef = treble }")
        self.assert_(isinstance(p.header['clef'], unicode))
        self.assertEquals(p.header['clef'], 'treble')
    def test_module_names(self):
        """
        Test that all module names are allowed, even if they crash
        with predefined functions or constants.
        """
        for modulename in ('rhythm', 'unknownmodule', 'yes'):
            p = self.do_file("\n".join([
                'header {',
                '   module=%s',
                '}',
            ]) % modulename)
            self.assert_(isinstance(p.header['module'], unicode))
            self.assertEquals(p.header['module'], modulename)
    def test_include(self):
        self.add_file('element I { label = "I" }', 'progression_elements')
        p = self.do_file('include("progression_elements")')
        self.assert_('element' in p.blocklists)
    def test_include_dont_overwrite_header_vars_but_adds_new(self):
        self.add_file('header{ c = 2 d = 5 }', u'incfile')
        p = self.do_file('\n'.join([
            'header{ c = 4 }',
            'include("incfile")',
        ]))
        self.assertEquals(p.header['c'], 4)
        self.assertEquals(p.header['d'], 5)
    def test_that_real_header_overwrites_previously_included(self):
        self.add_file('header{ c = 2 }', 'incfile')
        p = self.do_file('\n'.join([
            'include("incfile")',
            'header{ c = 4 }',
            'include("incfile")',
        ]))
        self.assertEquals(p.header['c'], 4)
    def test_load(self):
        self.add_file('text', 'file-to-load')
        p = self.do_file('s = load("file-to-load")')
        self.assert_('s' in p.m_globals and p.m_globals['s'] == 'text')
    def test_element_def(self):
        p = self.do_file('element progI { label = progressionlabel("I") }')
        self.assert_('label' in p.blocklists['element'][0])
        self.assertEquals(p.blocklists['element'][0]['name'], 'progI')
        self.assertEquals(p.m_globals['progI']['name'], 'progI')
    def test_music_shortcut(self):
        p = self.do_file('question { chord("c e g") }')
        self.assert_('music' in p.m_questions[0])
    def test_music_shortcut_string(self):
        p = self.do_file('question { "c d e" }')
        self.assert_('music' in p.m_questions[0])
    def test_error_music_shortcut_string(self):
        try:
            self.do_file('question { "c d e"')
        except dataparser.DataparserSyntaxError, e:
            self.assertEquals(e.m_nonwrapped_text, "\n".join([
                '(line 1): question { "c d e"',
                '                            ^',
            ]))
        else:
            self.fail("DataparserSyntaxError not raised")
    def test_addition(self):
        p = self.do_file(u"""
              a = "en " + "to"
              i = 3 + 5
              tr1 = _("major")
              title = _("Is the interval flat, in tune or sharp? %s cent wrong") % 10
              """)
        self.assertEquals(p.m_globals['a'], "en to")
        self.assertEquals(p.m_globals['i'], 8)
        self.assertEquals(p.m_globals['tr1'], 'dur')
    def test_absolute_import(self):
        """
        This test will import progression_elements and will show that
        the program will import Solfege progression_elements, and not
        the file in solfege/tests/lib/
        """
        p = LessonfileCommon()
        p.parse_file(u"solfege/tests/lesson-files/test_absolute_import")
        self.assertFalse('tests_progression_elements' in p.m_globals)
        self.assertEquals(p.m_globals['progression_elements'].m_globals['I']['label'].m_labeltype, 'progressionlabel')
        self.assertEquals(p.m_globals['progression_elements'].m_globals['I']['label'].m_labeldata, 'I')
    def test_absolute_import_not_found_but_relative_exists(self):
        """
        absolute import will load the the file relative to the lesson
        file if it does not exist in the standard exercises
        """
        p = LessonfileCommon()
        self.assertFalse(os.path.exists("exercises/standard/lib/not_in_standard"))
        p.parse_file(u"solfege/tests/lesson-files/test_absolute_import_not_found_load_relative")
    def test_absolute_import_as(self):
        """
        This test will import progression_elements and will show that
        the program will import Solfege progression_elements, and not
        the file in solfege/tests/lib/
        """
        p = LessonfileCommon()
        p.parse_file(u"solfege/tests/lesson-files/test_absolute_import_as")
        self.assertFalse('tests_progression_elements' in p.m_globals)
        self.assertEquals(p.m_globals['p'].m_globals['I']['label'].m_labeltype, 'progressionlabel')
        self.assertEquals(p.m_globals['p'].m_globals['I']['label'].m_labeldata, 'I')

    def test_relative_import(self):
        """
        rimport will import the file in solfege/tests/lib, not the file
        in the standard exercises
        """
        p = LessonfileCommon()
        p.parse_file(u"solfege/tests/lesson-files/test_relative_import")
        self.assertTrue('tests_progression_elements' in p.m_globals['progression_elements'].m_globals)
    def test_relative_import_as(self):
        """
        rimport will import the file in solfege/tests/lib, not the file
        in the standard exercises
        """
        p = LessonfileCommon()
        p.parse_file(u"solfege/tests/lesson-files/test_relative_import_as")
        self.assertTrue('tests_progression_elements' in p.m_globals['p'].m_globals)
    def test_relative_import_not_found_load_standard(self):
        """
        rimport will load from the standard exercises if the file is not
        found relative to the lesson file location.
        """
        p = LessonfileCommon()
        p.parse_file(u"solfege/tests/lesson-files/test_relative_import_not_found_load_standard")
        self.assertFalse(os.path.exists("solfege/tests/lib/jazz_progressions"))


class TestParserTranslations(TmpFileBase, I18nSetup):
    parserclass = LessonfileCommon
    def setUp(self):
        TmpFileBase.setUp(self)
        I18nSetup.setUp(self)
    def tearDown(self):
        TmpFileBase.tearDown(self)
        I18nSetup.tearDown(self)
    def test_istr_translations_in_file(self):
        p = self.do_file("""
           foo = "foo-C"
           foo[nb] = "foo-nb"
           # bar is not translated because the lang fr is not in the
           # list of languages when the test suite is run
           bar = "bar-C"
           bar[fr] = "bar-fr"
        """)
        self.assertEquals(p.m_globals['foo'], u"foo-nb")
        self.assertEquals(p.m_globals['foo'].cval, u"foo-C")
        self.assertEquals(p.m_globals['bar'], u"bar-C")
        self.assertEquals(p.m_globals['bar'].cval, u"bar-C")
    def test_istr_translation_of_list(self):
        try:
            p = self.do_file('\n'.join(['foo = "foo-C", "fo2-C"',
                                      'foo[nb] = "foo-nb", "fo2-nb"']))
        except dataparser.CanOnlyTranslateStringsException, e:
            self.assertEquals(e.m_nonwrapped_text, '\n'.join([
                 '(line 1): foo = "foo-C", "fo2-C"',
                 '(line 2): foo[nb] = "foo-nb", "fo2-nb"',
                 '                    ^']))
        else:
            self.fail("CanOnlyTranslateStringsException not raised")
    def test_istr_translation_of_int(self):
        try:
            p = self.do_file('\n'.join(['foo = 1',
                                      'foo[nb] = 2']))
        except dataparser.CanOnlyTranslateStringsException, e:
            self.assertEquals(e.m_nonwrapped_text, '\n'.join([
                 '(line 1): foo = 1',
                 '(line 2): foo[nb] = 2',
                 '                    ^']))
        else:
            self.fail("CanOnlyTranslateStringsException not raised")


class TestMpdTransposable(TmpFileBase):
    parserclass = LessonfileCommon
    def setUp(self):
        TmpFileBase.setUp(self)
        cfg.set_bool('config/override_default_instrument', False)
        self.do_file("""
        header { random_transpose = "atonal", -5, 5 }
        question { music = chord("c e g") }
        """)
        self.p.m_transpose = mpd.MusicalPitch.new_from_notename("d'")
        self.p._idx = 0
    def test_get_musicdata_transposed(self):
        self.assertEquals("d fis a", self.p.m_questions[0]['music'].get_musicdata_transposed(self.p))
        self.p.header.random_transpose = ("key", -5, 6)
        # get_musicdata_transposed works for all transposition modes.
        self.assertEquals("d fis a", self.p.m_questions[0]['music'].get_musicdata_transposed(self.p))
        self.assertEquals("c e g", self.p.m_questions[0]['music'].m_musicdata)

class TestChord(MObjTest):
    def setUp(self):
        MObjTest.setUp(self)
        cfg.set_bool('config/override_default_instrument', False)
        self.do_file("""
        header { random_transpose = no }
        question { music = chord("c e g") }
        """)
        self.p.m_transpose = mpd.MusicalPitch.new_from_notename("d'")
        self.p._idx = 0
    def get_get_mpd_music_string(self):
        self.assertEquals(self.p.m_questions[0]['music'].get_mpd_music_string(self.p),
            r"\staff{ <c e g> }")
        self.p.header.random_transpose = (True,)
        self.assertEquals(self.p.m_questions[0]['music'].get_mpd_music_string(self.p),
            r"\staff\transpose d'{ <c e g> }")
    def test_get_music_as_notename_list(self):
        self.assertEquals(self.p.m_questions[0]['music'].get_music_as_notename_list(self.p), ['c', 'e', 'g'])
        self.p.header.random_transpose = (True,)
        self.p.m_transpose = mpd.MusicalPitch.new_from_notename("d'")
        self.assertEquals(self.p.m_questions[0]['music'].get_music_as_notename_list(self.p), ['d', 'fis', 'a'])
    def test_get_lilypond_code(self):
        self.assertEquals(self.p.m_questions[0]['music'].get_lilypond_code(self.p), "\\score{  \\transpose c' d'{ <c e g> } \\layout {   ragged-last = ##t   \\context { \\Staff \\remove \"Time_signature_engraver\" }  }}")
        self.p.header.random_transpose = ('atonal', -5, 5)
        self.assertEquals(self.p.m_questions[0]['music'].get_lilypond_code(self.p), "\\score{    { <d fis a> } \\layout {   ragged-last = ##t   \\context { \\Staff \\remove \"Time_signature_engraver\" }  }}")
    def test_get_lilypond_code_first_note(self):
        self.assertEquals(self.p.m_questions[0]['music'].get_lilypond_code_first_note(self.p), r"\transpose c' d'{ c }")
        self.p.header.random_transpose = ('atonal', -5, 5)
        self.assertEquals(self.p.m_questions[0]['music'].get_lilypond_code_first_note(self.p), r"{ d }")
    def test_play(self):
        question = self.p.m_questions[0]
        question['music'].play(self.p, question)
        self.assertEquals(soundcard.synth.flush_testdata(),
            "t60/4 p0:0 v0:100 n48 n52 n55 d1/4 o48 o52 o55")
    def test_3patch_play(self):
        cfg.set_bool('config/override_default_instrument', True)
        question = self.p.m_questions[0]
        question['music'].play(self.p, question)
        self.assertEquals(soundcard.synth.flush_testdata(1),
            "t60/4 p0:1 p1:2 p2:3 v0:121 n0:48 v1:122 n1:52 v2:123 n2:55 d1/4 o48 o52 o55")
    def test_play_arpeggio(self):
        question = self.p.m_questions[0]
        question['music'].play_arpeggio(self.p, question)
        self.assertEquals(soundcard.synth.flush_testdata(),
            "t180/4 p0:0 v0:100 n48 d1/4 o48 n52 d1/4 o52 n55 d1/4 o55")
        self.p.header.random_transpose = (True,)
        question['music'].play_arpeggio(self.p, question)
        self.assertEquals(soundcard.synth.flush_testdata(),
            "t180/4 p0:0 v0:100 n50 d1/4 o50 n54 d1/4 o54 n57 d1/4 o57")
        cfg.set_bool('config/override_default_instrument', True)
        question['music'].play_arpeggio(self.p, question)
        self.assertEquals(soundcard.synth.flush_testdata(),
            "t180/4 p0:1 p1:2 p2:3 v0:121 n50 d1/4 o50 v1:122 n54 d1/4 o54 v2:123 n57 d1/4 o57")
    def test_atonal_transpose(self):
        self.p.header.random_transpose = ('atonal', -4, 4)
        self.assertEquals(self.p.m_questions[0]['music'].get_musicdata_transposed(self.p), "d fis a")
        self.p.m_transpose = mpd.MusicalPitch.new_from_notename("es'")
        self.assertEquals(self.p.m_questions[0]['music'].get_musicdata_transposed(self.p), "ees g bes")

class TestMusic(MObjTest):
    def setUp(self):
        MObjTest.setUp(self)
        cfg.set_bool('config/override_default_instrument', False)
        self.do_file("""
        header { random_transpose = no }
        question { music = music("\staff{c''}\staff{e'}\staff{c}") }
        question {
            instrument = 33, 34, 35, 36, 37, 38
            music = music("\staff{c''}\staff{e'}\staff{c}")
        }
        question {
            instrument = 33, 34, 35, 36, 37, 38
            music = music("\staff{c''}\staff{b'}")
        }
        question {
            instrument = 33, 34, 35, 36, 37, 38
            music = music("\staff{c''}")
        }
        """)
        self.p.m_transpose = mpd.MusicalPitch.new_from_notename("d'")
        self.p._idx = 0
    def test_too_many_instruments_play(self):
        # If the question has two tracks, and the instrument variable
        # has more instruments, then only the first and last instrument
        # is used
        question = self.p.m_questions[2]
        question['music'].play(self.p, question)
        self.assertEquals(soundcard.synth.flush_testdata(1),
            "t60/4 p0:37 p1:33 v0:38 n0:72 v1:34 n1:71 d1/4 o72 o71")
        # If the question has only one track, the last instrument,
        # representing the highest instrument, is used.
        question = self.p.m_questions[3]
        question['music'].play(self.p, question)
        self.assertEquals(soundcard.synth.flush_testdata(1),
            "t60/4 p0:37 v0:38 n0:72 d1/4 o72")
    def test_play(self):
        question = self.p.m_questions[0]
        question['music'].play(self.p, question)
        self.assertEquals(soundcard.synth.flush_testdata(1),
            "t60/4 p0:0 v0:100 n0:72 n0:64 n0:48 d1/4 o72 o64 o48")
        # Music objects should ignore config/override_default_instrument
        cfg.set_bool('config/override_default_instrument', True)
        question['music'].play(self.p, question)
        self.assertEquals(soundcard.synth.flush_testdata(1),
            "t60/4 p0:0 v0:100 n0:72 n0:64 n0:48 d1/4 o72 o64 o48")
        #
        question = self.p.m_questions[1]
        # If the instrument variable it set, and it has more than one
        # instrument, as it as in questions[1], then even Music will
        # play with more than one instrument.:w
        question['music'].play(self.p, question)
        self.assertEquals(soundcard.synth.flush_testdata(1),
            "t60/4 p0:37 p1:35 p2:33 v0:38 n0:72 v1:36 n1:64 v2:34 n2:48 d1/4 o72 o64 o48")
    def test_play_slowly(self):
        question = self.p.m_questions[0]
        #test.py TestMusic viser at det ikke blir generert riktig instrument
        #for ovelser som progressions-2 (harmonicprogressiondictation)
        question['music'].play_slowly(self.p, question)
        self.assertEquals(soundcard.synth.flush_testdata(1),
            "t30/4 p0:0 v0:100 n0:72 n0:64 n0:48 d1/4 o72 o64 o48")
        cfg.set_bool('config/override_default_instrument', True)
        question['music'].play_slowly(self.p, question)
        self.assertEquals(soundcard.synth.flush_testdata(1),
            "t30/4 p0:0 v0:100 n0:72 n0:64 n0:48 d1/4 o72 o64 o48")

class TestMusic3(MObjTest):
    def setUp(self):
        MObjTest.setUp(self)
        cfg.set_bool('config/override_default_instrument', False)
        self.do_file("""
        header { random_transpose = no }
        question { music = music3("\staff{c''}\staff{e'}\staff{c}") }
        question {
            instrument = 33, 34, 35, 36, 37, 38
            music = music3("\staff{c''}\staff{g'}\staff{e'}\staff{c}")
        }
        """)
        self.p.m_transpose = mpd.MusicalPitch.new_from_notename("d'")
        self.p._idx = 0
    def test_play(self):
        question = self.p.m_questions[0]
        question['music'].play(self.p, question)
        self.assertEquals(soundcard.synth.flush_testdata(1),
            "t60/4 p0:0 v0:100 n0:72 n0:64 n0:48 d1/4 o72 o64 o48")
        #
        cfg.set_bool('config/override_default_instrument', True)
        question['music'].play(self.p, question)
        self.assertEquals(soundcard.synth.flush_testdata(1),
            "t60/4 p0:3 p1:2 p2:1 v0:123 n0:72 v1:122 n1:64 v2:121 n2:48 d1/4 o72 o64 o48")
        #
        question = self.p.m_questions[1]
        question['music'].play(self.p, question)
        self.assertEquals(soundcard.synth.flush_testdata(1),
            "t60/4 p0:37 p1:35 p2:33 v0:38 n0:72 v1:36 n1:67 n1:64 v2:34 n2:48 d1/4 o72 o67 o64 o48")

class TestVoiceCommon(unittest.TestCase):
    def test_get_first_pitch(self):
        for s, n in (
            ("c d e", "c"),
            ("<c'' e>", "c''"),
            ("< c'' e>", "c''"),
            (" c,,16", "c,,"),
            (" \n c d e", "c"),
            (r"\clef bass c d e", "c"),
            (r"\clef violin \time 3/8 fis", "fis"),
            (r'\clef "violin_8" d', "d"),
            ("\\key g \\major \\time 2/4\n d'8 | [g g]", "d'"),
            ("\nc", "c"),
            ):
            x = Rvoice(s)
            self.assertEquals(x.get_first_pitch().get_octave_notename(), n)
        self.assertRaises(MusicObjectException, Rvoice("\\clef bass").get_first_pitch)


class TestVoice(MObjTest):
    def setUp(self):
        MObjTest.setUp(self)
        cfg.set_bool('config/override_default_instrument', False)
        self.p = QuestionsLessonfile()
        self.do_file("""
        header { random_transpose = no }
        question { music = voice("c d e") }
        question { music = voice("< e") }
        """)
        self.p.m_transpose = mpd.MusicalPitch.new_from_notename("d'")
        self.p._idx = 0
    def test_get_mpd_music_string(self):
        self.assertEquals(self._m().get_mpd_music_string(self.p),
                          "\\staff{\nc d e\n}")
        self.p.header.random_transpose = [True]
        self.assertEquals(self._m().get_mpd_music_string(self.p),
                          "\\staff\\transpose d'{\nc d e\n}")
        self.p.header.random_transpose = ['atonal', -5, 6]
        self.assertEquals(self._m().get_mpd_music_string(self.p),
                          "\\staff{\nd e fis\n}")
    def test_get_lilypond_code(self):
        self.assertEquals(self._m().get_lilypond_code(self.p),
                          r"{ c d e }")
        self.p.header.random_transpose = [True]
        self.assertEquals(self._m().get_lilypond_code(self.p),
                          r"\transpose c' d'{ c d e }")
        self.p.header.random_transpose = "atonal", -5, 6
        self.assertEquals(self._m().get_lilypond_code(self.p),
                          r"{ d e fis }")
    def test_get_lilypond_code_first_note(self):
        self.assertEquals(self.p.m_questions[0]['music'].get_lilypond_code_first_note(self.p), r"\score{ \new Staff<< \new Voice{ \cadenzaOn c } \new Voice{ \hideNotes c d e } >> \layout { ragged-last = ##t } }")
        self.p.header.random_transpose = [True]
        self.assertEquals(self.p.m_questions[0]['music'].get_lilypond_code_first_note(self.p), ur"\score{ \new Staff<< \new Voice\transpose c' d'{ \cadenzaOn c } \new Voice{ \hideNotes c d e } >> \layout { ragged-last = ##t } }")
        self.p.header.random_transpose = "atonal", -5, 6
        self.assertEquals(self.p.m_questions[0]['music'].get_lilypond_code_first_note(self.p), r"\score{ \new Staff<< \new Voice{ \cadenzaOn d } \new Voice{ \hideNotes c d e } >> \layout { ragged-last = ##t } }")
    def _test_play(self):
        question = self.p.m_questions[0]
        question['music'].play(self.p, question)
        self.assertEquals(soundcard.synth.flush_testdata(),
            "t60/4 p0:0 v0:100 n48 d1/4 o48 n50 d1/4 o50 n52 d1/4 o52")
    def test_play(self):
        self._test_play()
    def test_3patch_play(self):
        """
        voice music objects ignore config/override_default_instrument
        by design.
        """
        question = self.p.m_questions[0]
        self._test_play()
    def test_play_slowly(self):
        question = self.p.m_questions[0]
        question['music'].play_slowly(self.p, question)
        self.assertEquals(soundcard.synth.flush_testdata(),
            "t30/4 p0:0 v0:100 n48 d1/4 o48 n50 d1/4 o50 n52 d1/4 o52")
    def test_findfirst(self):
        for p1, p2, s, n in (
            (0, 1, "c d e", "c"),
            (1, 4, "<c'' e>", "c''"),
            (2, 5, "< c'' e>", "c''"),
            (2, 5, "\n\nERR", "ERR"),
            (1, 4, " c,,16", "c,,"),
            (3, 4, " \n c d e", "c"),
            (11, 12, r"\clef bass c d e", "c"),
            (23, 26, r"\clef violin \time 3/8 fis", "fis"),
            (17, 18, r'\clef "violin_8" d', "d"),
            (25, 27, "\\key g \\major \\time 2/4\n d'8 | [g g]", "d'"),
            (1, 2, "\nc", "c"),
            ):
            x = Rvoice(s)
            self.assertEquals((p1, p2), mpdutils.find_possible_first_note(x.m_musicdata), "String failed: %s: %s" % (s, mpdutils.find_possible_first_note(x.m_musicdata)))
            self.assertEquals(s[p1:p2], n)
    def test_error_handling(self):
        m = self._m(1).get_mpd_music_string(self.p)
        try:
            mpd.parser.parse_to_score_object(m)
        except mpd.MpdException, e:
            self._m(1).complete_to_musicdata_coords(self.p, e)
            ec = self._m(1).get_err_context(e, self.p)
            self.assertEquals(ec,
              "Bad input to the music object of type voice made\n"
              "the parser fail to parse the following generated\n"
              "music code:\n"
              "\\staff{\n"
              "< e\n"
              "}\n"
              "^")

        else:
            self.fail("Test failed. No exception raised.")

class TestErrorHandling(MObjTest):
    def setUp(self):
        MObjTest.setUp(self)
        cfg.set_bool('config/override_default_instrument', False)
    def _dotest(self, musictypes, bad_code):
        for t in musictypes:
            for code, err_context in bad_code:
                self.do_file('''
                header { random_transpose = no }
                question { music = %s("%s") }
                ''' % (t, code))
                self.p.m_transpose = mpd.MusicalPitch.new_from_notename("d'")
                self.p._idx = 0
                question = self.p.m_questions[0]
                try:
                    self.p.play_question(question)
                except MusicObjectException, e:
                    self.assertEquals(err_context, str(e))
                except mpd.MpdException, e:
                    ec = question.music.get_err_context(e, self.p)
                    self.assertEquals(err_context, ec, "Music failed with musictype %s:\n%s !=\n%s" % (t, err_context, ec))
                else:
                    self.fail("No exception raised in this code: %s" % code)
    def test_1(self):
        cfg.set_bool('config/override_default_instrument', False)
        self._test_1()
    def test_1_3patches(self):
        """
        Test with 3 different patches, just in case implementation details
        make error handling different with config/override_default_instrument
        set and unset.
        """
        cfg.set_bool('config/override_default_instrument', True)
        self._test_1()
    def _test_1(self):
        self._dotest(("chord", "voice",),
                   (("c d e ERR f",
                     "c d e ERR f\n"
                     "      ^^^"),
                    ("c d e f\ng ERR a",
                    "g ERR a\n"
                     "  ^^^"),
                    ("c d XX e f\ng ERR a",
                     "c d XX e f\n"
                     "    ^^"),
                    ("ERR",
                     "ERR\n"
                     "^^^"),
                  ))
    def test_barfull(self):
        self._dotest(("music",),
                   (("\\staff { c2. c }",
                     "\\staff { c2. c }\n"
                      "             ^"),
                    ))
        self._dotest(("voice",),
                   (("c2. c",
                     "c2. c\n"
                     "    ^"),
                    ))
    def test_bad_clef(self):
        self._dotest(("music",),
                     (("\\staff { \\clef ERR",
                      "\\staff { \\clef ERR\n"
                        "         ^^^^^^^^^"),))
        self._dotest(("voice", "rvoice"),
                     (("\\clef ERR c d e",
                       "\\clef ERR c d e\n"
                        "^^^^^^^^^"),
                      ("c \\clef ERR c d e",
                       "c \\clef ERR c d e\n"
                        "  ^^^^^^^^^"),
                      ("\\time 4/4\n"
                       "   c d \clef ERR3 e f\n"
                       "  ",
                       "   c d \clef ERR3 e f\n"
                       "       ^^^^^^^^^^"),
                        ))
    def test_satb(self):
        self._test_satb()
    def test_satb_3patches(self):
        cfg.set_bool('config/override_default_instrument', True)
        self._test_satb()
    def _test_satb(self):
        self._dotest(("satb",),
            (("c'' | ERR | g | c",
              "c'' | ERR | g | c\n"
              "     ^^^^^"),
             ("c''|g'|ERR| c",
              "c''|g'|ERR| c\n"
              "       ^^^"),
             ("c'' |e' d'|\n ERR |c",
              "The music code from the lesson file has been modified by\n"
              "removing the new-line characters. This to more easily show\n"
              "where the error occured. Satb music should not contain music\n"
              "characters.\n"
              "c'' |e' d'| ERR |c\n"
              "           ^^^^^"),
             ("|||",
              "Satb music does not allow an empty voice"),
             ("{ | g",
              "Satb music should be divided into 4 parts by the '|' character",),
              ))
    def test_music(self):
        self._dotest(("music",),
            (("\\staff{ c' d ERR e }",
              "\\staff{ c' d ERR e }\n"
              "             ^^^"),
             ("\\staff{ c4. c. }",
              "\\staff{ c4. c. }\n"
              "            ^^"),
             ("\\addvoice{ jojo ",
              "\\addvoice{ jojo \n"
              "^^^^^^^^^"),
             ("\\staff { c4 c4. c. }",
              "\\staff { c4 c4. c. }\n"
              "                ^^"),
             ("\\staff { c4\n"
              "ERR }",
              "ERR }\n"
              "^^^"),
             ("\\staff{ \\clef ERROR c",
              "\\staff{ \\clef ERROR c\n"
                "        ^^^^^^^^^^^"),
            ))


class TestRvoice(MObjTest):
    def setUp(self):
        MObjTest.setUp(self)
        cfg.set_bool('config/override_default_instrument', False)
        self.do_file("""
        header { random_transpose = no }
        question { music = rvoice("c' d b c") }
        question { music = rvoice("[c'8 d] e16") }
        question { music = rvoice("c,, d' b c") }
        question { music = rvoice("b,, d' b c") }
        question { music = rvoice("< e") }
        question { music = rvoice("ERR") }
        question { music = rvoice("c d e f\ng ERR a") }
        """)
        self.p.m_transpose = mpd.MusicalPitch.new_from_notename("d'")
        self.p._idx = 0
    def test_get_mpd_music_string(self):
        self.assertEquals(self._m().get_mpd_music_string(self.p),
            "\\staff\\relative c'{\nc d b c\n}")
        self.p.header.random_transpose = (True,)
        self.assertEquals(self._m().get_mpd_music_string(self.p),
            "\\staff\\transpose d'\\relative c'{\nc d b c\n}")
        self.p.header.random_transpose = ['atonal', -5, 6]
        self.assertEquals(self._m().get_mpd_music_string(self.p),
            "\\staff\\relative d'{\nd e cis d\n}")
        self.assertEquals(self._m(1).get_mpd_music_string(self.p),
            "\\staff\\relative d'{\n[ d8 e ] fis16\n}")
        self.assertEquals(self._m(2).get_mpd_music_string(self.p),
            "\\staff\\relative d,,{\nd e' cis d\n}")
        self.assertEquals(self._m(3).get_mpd_music_string(self.p),
            "\\staff\\relative cis,{\ncis e' cis d\n}")
    def _test_play(self):
        question = self.p.m_questions[0]
        question['music'].play(self.p, question)
        self.assertEquals(soundcard.synth.flush_testdata(),
            "t60/4 p0:0 v0:100 n60 d1/4 o60 n62 d1/4 o62 n59 d1/4 o59 n60 d1/4 o60")
    def test_play(self):
        self._test_play()
    def test_3patch_play(self):
        """
        rvoice music objects ignore config/override_default_instrument
        by design.
        """
        question = self.p.m_questions[0]
        self._test_play()
    def test_play_slowly(self):
        question = self.p.m_questions[0]
        question['music'].play_slowly(self.p, question)
        self.assertEquals(soundcard.synth.flush_testdata(),
            "t30/4 p0:0 v0:100 n60 d1/4 o60 n62 d1/4 o62 n59 d1/4 o59 n60 d1/4 o60")
    def test_get_lilypond_code(self):
        self.assertEquals(self.p.m_questions[0]['music'].get_lilypond_code(self.p), r"\transpose c' d'\relative c{ c' d b c }")
    def test_get_lilypond_code_first_note(self):
        self.assertEquals(self.p.m_questions[0]['music'].get_lilypond_code_first_note(self.p), r"\score{ \new Staff<< \new Voice\transpose c' d'\relative c{ \cadenzaOn c' } \new Voice{ \hideNotes c' d b c } >> \layout { ragged-last = ##t } }")
    def test_bad_first_note(self):
        self.p.header.random_transpose = (True, 0, 0)
        m = self._m(4).get_mpd_music_string(self.p)
        try:
            mpd.parser.parse_to_score_object(m)
        except mpd.parser.ParseError, e:
            self.assertEquals(self._m(4).get_err_context(e, self.p),
                "Bad input to the music object of type rvoice made\n"
                "the parser fail to parse the following generated\n"
                "music code:\n"
                "\\staff\\transpose d'\\relative e{\n"
                "< e\n"
                "}\n"
                "^")
        else:
            self.fail("Test failed. No exception raised.")
        m = self._m(5).get_mpd_music_string(self.p)
        try:
            mpd.parser.parse_to_score_object(m)
        except mpd.InvalidNotenameException, e:
            self.assertEquals(self._m(5).get_err_context(e, self.p),
                "Bad input to the music object of type rvoice made\n"
                "the parser fail to parse the following generated\n"
                "music code:\n"
                "\\staff\\transpose d'\\relative ERR{\n"
                "                   ^^^^^^^^^^^^^\n"
                "ERR\n"
                "}")
        else:
            self.fail("Test failed. No exception raised.")
        m = self._m(6).get_mpd_music_string(self.p)
        try:
            mpd.parser.parse_to_score_object(m)
        except mpd.InvalidNotenameException, e:
            self.assertEquals(self._m(6).get_err_context(e, self.p),
                "Bad input to the music object of type rvoice made\n"
                "the parser fail to parse the following generated\n"
                "music code:\n"
                "\\staff\\transpose d'\\relative c{\n"
                "c d e f\n"
                "g ERR a\n"
                "  ^^^\n"
                "}")
        else:
            self.fail("Test failed. No exception raised.")

class TestSatb(MObjTest):
    def setUp(self):
        MObjTest.setUp(self)
        cfg.set_bool('config/override_default_instrument', False)
        self.do_file("""
        header { random_transpose = no }
        question { music = satb("c''| e'| g | c") }
        question { key = "aes \\major" music = satb("c''|as'|es'|as") }
        question { music = satb("c''| g' e'| g | c") }
        """)
        self.p.m_transpose = mpd.MusicalPitch.new_from_notename("d'")
        self.p._idx = 0
    def test_get_mpd_music_string(self):
        self.assertEquals(self.p.m_questions[0]['music'].get_mpd_music_string(self.p),
            "\\staff{ \\key c \\major\\stemUp <c''> }\n" \
            "\\addvoice{ \\stemDown <e'> }\n" \
            "\\staff{ \\key c \\major\\clef bass \\stemUp <g>}\n" \
            "\\addvoice{ \\stemDown <c>}")
        # FIXME Satb only works if the music object is the current selected
        # question. Can we get around this?
        self.p._idx  = 1
        self.assertEquals(self.p.m_questions[1]['music'].get_mpd_music_string(self.p),
            "\\staff{ \\key aes \\major\\stemUp <c''> }\n" \
            "\\addvoice{ \\stemDown <as'> }\n" \
            "\\staff{ \\key aes \\major\\clef bass \\stemUp <es'>}\n" \
            "\\addvoice{ \\stemDown <as>}")
    def test_play(self):
        question = self.p.m_questions[0]
        question['music'].play(self.p, question)
        self.assertEquals(soundcard.synth.flush_testdata(),
            "t60/4 p0:0 v0:100 n72 n64 n55 n48 d1/4 o72 o64 o55 o48")
    def test_play_arpeggio(self):
        question = self.p.m_questions[0]
        question['music'].play_arpeggio(self.p, question)
        self.assertEquals(soundcard.synth.flush_testdata(),
            "t60/4 p0:0 v0:100 n60 d1/4 o60 n52 d1/4 o52 n55 d1/4 o55 n48 d1/4 o48")
        question = self.p.m_questions[2]
        question['music'].play_arpeggio(self.p, question)
        self.assertEquals(soundcard.synth.flush_testdata(),
            "t60/4 p0:0 v0:100 n60 d1/4 o60 n55 d1/4 o55 n52 d1/4 o52 n55 d1/4 o55 n48 d1/4 o48")
        # Then with transposition
        self.p.header.random_transpose = (True,)
        question['music'].play_arpeggio(self.p, question)
        self.assertEquals(soundcard.synth.flush_testdata(),
            "t60/4 p0:0 v0:100 n62 d1/4 o62 n57 d1/4 o57 n54 d1/4 o54 n57 d1/4 o57 n50 d1/4 o50")

class TestRhythm(MObjTest):
    def setUp(self):
        MObjTest.setUp(self)
        cfg.set_bool('config/override_default_instrument', False)
        self.do_file(r"""
        question { music = rhythm("d c8") }
        question { music = rhythm("c \time 3\4 c d") }
        """)
        self.p._idx = 0
    def test_play(self):
        question = self.p.m_questions[0]
        question['music'].play(self.p, question)
        self.assertEquals(soundcard.synth.flush_testdata(),
            "t60/4 v9:100 P80 d1/4 o80 P37 d1/8 o37")
    def test_bad_time(self):
        question = self.p.m_questions[1]
        self.assertRaises(mpd.InvalidNotenameException,
            question.music.get_mpd_music_string, self.p)

class TestPercussion(MObjTest):
    def setUp(self):
        MObjTest.setUp(self)
        cfg.set_bool('config/override_default_instrument', False)
        self.p = QuestionsLessonfile()
        self.do_file('question { music = percussion("e16 f g4") }')
        self.p._idx = 0
    def test_play(self):
        question = self.p.m_questions[0]
        question['music'].play(self.p, question)
        self.assertEquals(soundcard.synth.flush_testdata(),
            "t60/4 v9:100 P52 d1/16 o52 P53 d1/16 o53 P55 d1/4 o55")


class TestWavfile(MObjTest):
    def setUp(self):
        MObjTest.setUp(self)
        self.do_file('question { music = wavfile("exercises/standard/lesson-files/share/fifth-small-293.33.wav") }')
        self.p._idx = 0
    def test_play(self):
        question = self.p.m_questions[0]
        if cfg.get_bool('testing/may_play_sound'):
            question['music'].play(self.p, question)
            time.sleep(3)
    def test_get_mpd_music_string(self):
        question = self.p.m_questions[0]
        self.assertEquals(question['music'].get_mpd_music_string(self.p),
                          "Wavfile:exercises/standard/lesson-files/share/fifth-small-293.33.wav")
        self.assertEquals(question.music.m_musicdata,
                          "exercises/standard/lesson-files/share/fifth-small-293.33.wav")
        self.assertTrue(isinstance(question.music, Wavfile))

class TestMidifile(MObjTest):
    def setUp(self):
        MObjTest.setUp(self)
        self.do_file('question { music = midifile("exercises/standard/lesson-files/share/fanfare.midi") }')
        self.p._idx = 0
    def test_play(self):
        question = self.p.m_questions[0]
        if cfg.get_bool('testing/may_play_sound'):
            question['music'].play(self.p, question)
            time.sleep(3)
    def test_get_mpd_music_string(self):
        question = self.p.m_questions[0]
        self.assertEquals(question['music'].get_mpd_music_string(self.p),
                          "Midifile:exercises/standard/lesson-files/share/fanfare.midi")
        self.assertEquals(question.music.m_musicdata,
                          "exercises/standard/lesson-files/share/fanfare.midi")
        self.assertTrue(isinstance(question.music, Midifile))


class TestCmdline(MObjTest):
    def setUp(self):
        MObjTest.setUp(self)
        self.do_file('question { music = cmdline("/usr/bin/play exercises/standard/lesson-files/share/fifth-pure-220.00.wav") }')
        self.p._idx = 0
    def test_play(self):
        question = self.p.m_questions[0]
        if cfg.get_bool('testing/may_play_sound'):
            question['music'].play(self.p, question)
            time.sleep(3)

class TestCSound(MObjTest):
    def test_CSound(self):
        self.do_file('''
header {
    module = idbyname
    help = "idbyname-intonation"
    title = "Test "
}

question {
 name = "III temperature"
 set=0
 csound_sco = """
f1     0    4096 10   1  ; use GEN10 to compute a sine wave
; p1  p2    p3  p4     p5    p6     p7
;ins  strt  dur amp    freq  attack release
  i1  0     1   10000  440   0.2    0.08
  i1  +     1   10000  660   0.08    0.08
e
 """
 music = csound(load("../../../exercises/standard/lesson-files/share/sinus-ad.orc"), csound_sco)
}''')
        question = self.p.m_questions[0]
        if cfg.get_bool('testing/may_play_sound'):
            question['music'].play(self.p, question)


class TestMma(MObjTest):
    def test_1arg(self):
        p = self.do_file("""
        question {
            music = mma("1 Cmaj7")
        }
        """)
        q = p.m_questions[0]
        if cfg.get_bool('testing/may_play_sound'):
            q['music'].play(p, q)
    def test_2arg(self):
        p = self.do_file("""
        question {
            music = mma("ballad", "1 Cmaj7")
        }
        """)
        q = p.m_questions[0]
        if cfg.get_bool('testing/may_play_sound'):
            q['music'].play(p, q)


class TestLessonfileHeader(MObjTest, I18nSetup):
    def setUp(self):
        MObjTest.setUp(self)
        I18nSetup.setUp(self)
    def test_untranslated_variable(self):
        self.do_file("""
        header { untranslated = "jojo"
           translated = _("major")
        }
        question { } #dummy question to avoid NoQuestionsInFileException
        """)
        self.assertEquals(self.p.header['untranslated'], u"jojo")
        self.assertEquals(self.p.header['untranslated'].cval, u"jojo")
        self.assertEquals(self.p.header['translated'], u"dur")
        self.assertEquals(self.p.header['translated'].cval, u"major")
        self.assertEquals(self.p.header.untranslated, u"jojo")
        self.assertEquals(self.p.header.untranslated.cval, u"jojo")
        self.assertEquals(self.p.header.translated, u"dur")
        self.assertEquals(self.p.header.translated.cval, u"major")
    def test_infile_translations_discard(self):
        self.do_file("""
        header {
           title = "C-locale header"
           title[et] = "et-locale header"
        }
        question { } #dummy question to avoid NoQuestionsInFileException
        """)
        # This test is run with LANGUAGE='no', so the 'et' translation
        # is discarded
        self.assertEquals(self.p.header.title, "C-locale header")
        self.assertEquals(self.p.header.title.cval, "C-locale header")

class TestLessonfileQuestion(MObjTest, I18nSetup):
    def setUp(self):
        MObjTest.setUp(self)
        I18nSetup.setUp(self)
    def test_question_name(self):
        self.do_file("""
        question { name = "untranslated" }
        question { name = _("major") }
        question { # question has no name
        }
        """)
        self.assertEquals(self.p.m_questions[0].name, u"untranslated")
        self.assertEquals(self.p.m_questions[0].name.cval, u"untranslated")
        self.assertEquals(self.p.m_questions[1].name, u"dur")
        self.assertEquals(self.p.m_questions[1].name.cval, u"major")
        self.assertRaises(AttributeError, lambda : self.p.m_questions[2].name)
    def test_setattr(self):
        q = dataparser.Question()
        q.var = 1
        self.assertEquals(q.var, 1)
        self.assertEquals(q['var'], 1)

class TestLessonfileMisc(TmpFileBase):
    parserclass = IdPropertyLessonfile
    def test_eq(self):
        c = Chord("a b c")
        d = Rvoice("a b c")
        e = Rvoice("a b c")
        f = Rvoice("c c c")
        self.assertNotEquals(c, d)
        self.assertNotEquals(d, e)
        self.assertNotEquals(d, f)
    def test_IdPropertyLessonfileFilter(self):
        s = """header {
                qprops = "name", "inversion"
                qprop_labels = _("Name"), _("Inversion")
            }
            question { name = "one" }
            question { name = "two" inversion=2 }
            """
        p = self.do_file(s)
        # One question should be discarded because it does not have
        # the inversion variable
        self.assertEquals(len(p.m_discards), 1)
        self.assertEquals(len(p.m_questions), 1)
    def test_IdPropertyLessonfileFilter2(self):
        s = 'header { qprops = "name", "inversion" qprop_labels = "Name", "Inversion" }\n' \
            'question { name = "one" inversion=1} \n' \
            'question { name = "two" inversion=2 top=0 } '
        p = self.do_file(s)
        # No questions are discaded.
        # top is not a property since it is not added to qprops, so
        # thats why the first question is not discarded.
        self.assertEquals(len(p.m_discards), 0)
        self.assertEquals(len(p.m_questions), 2)
    def test_IdPropertyLessonfile_qprops(self):
        s = 'header { qprops = "name", "inversion", "toptone" qprop_labels = "Name", "Inversion", "Toptone" }\n' \
            'question { name = "one" inversion=1} \n' \
            'question { name = "two" inversion=2 top=0 } '
        p = self.do_file(s)
        # No questions are discarded, since they both contain the same
        # two properties, of the tree listed in qprops. The 'top' variable
        # in the second question does not affect what is or is not discarded
        # because is it not a property (not defined in qprops)
        self.assertEquals(len(p.m_questions), 2)
    def test_ChordLessonfileFilter(self):
        s = """header { }
            question { name = "one" }
            question { name = "two" inversion=2 }
            """
        self.p = ChordLessonfile()
        p = self.do_file(s)
        # One question should be discarded because it does not have
        # the inversion variable
        self.assertEquals(len(p.m_questions), 1)
    def test_ChordLessonfileFilter2(self):
        s = 'header { qprops = "name", "inversion" qprop_labels = "Name", "Inversion" }\n' \
            'question { name = "one" inversion=1} \n' \
            'question { name = "two" inversion=2 top=0 } '
        self.p = ChordLessonfile()
        p = self.do_file(s)
        # No questions are discaded.
        # top is not a property since it is not added to qprops, so
        # thats why the first question is not discarded.
        self.assertEquals(len(p.m_questions), 2)
    def test_IdProperty(self):
        """
        Once, a single item qprops did not work.
        """
        s = 'header { qprops = "name" qprop_labels = "NAME" } ' \
            'question { name = "major" music = chord("c e g") } '
        self.p = IdPropertyLessonfile()
        p = self.do_file(s)
        self.assertEquals(p.header.qprops, [u'name'])
    def test_nrandom(self):
        self._worker_Xrandom("nrandom")
    def test_prandom(self):
        self._worker_Xrandom("prandom")
    def _worker_Xrandom(self, rfunc):
        styles = ["8beat", "ballad", "rock"]
        s = """
        styles = %s
        question {
            style = %s("8beat", "ballad")
        }
        question {
            style = %s(styles)
        }
        """ % (", ".join(['"%s"' % x for x in styles]), rfunc, rfunc)
        self.p = QuestionsLessonfile()
        p = self.do_file(s)
        for idx in range(2):
            st = p.m_questions[idx]['style']
            for x in range(20):
                self.assert_(str(st) in styles)
                self.assert_(unicode(st) in styles)
                st.randomize()
            # This test only works with nrandom, because prandom will
            # return a possible different value every time.
            if rfunc == 'nrandom':
                l = Gtk.Label(label=st)
                self.assert_(l.get_text() == unicode(st), "%s and gtk does not cooperate." % rfunc)

class TestLabelObject(unittest.TestCase):
    def test_construct(self):
        l = LabelObject("pangomarkup", "abc")
        self.assertEquals(l.cval, ("pangomarkup", "abc"))
    def test_rn_markup(self):
        for s, v in (
            ("Imaj7-", [('I', 'maj', '7', '-')]),
            ("bIIIm7 -", [('bIII', 'm', '7', ' -')]),
            (u"♯IIIm7 -", [(u'♯III', 'm', '7', ' -')]),
            (u"♭IIIm7 -", [(u'♭III', 'm', '7', ' -')]),
            ("Imaj7-IIm7-V9-Imaj7", [('I', 'maj', '7', '-'),
                                     ('II', 'm', '7', '-'),
                                     ('V', '', '9', '-'),
                                     ('I', 'maj', '7', '')]),
            ("Imaj7", [('I', 'maj', '7', '')]),
            ("iim9b5+13", [('ii', 'm', '9b5+13', '')]),
            ("Imaj7-V7", [('I', 'maj', '7', '-'), ('V', '', '7', '')]),
            ("Imaj7  -IIm9", [('I', 'maj', '7', '  -'), ('II', 'm', '9', '')]),
                ):
            self.assertEquals(rnc_markup_tokenizer(s), v, (rnc_markup_tokenizer(s), v))

    def test_chordname_markup(self):
        for s, v in (
            ("cis4", [('cis', '4', '', '')]),
            ('gmaj7', [('g', 'maj7', '', '')]),
            ('gesmaj7:9b5', [('ges', 'maj7', '9b5', '')]),
            ('g/g', [('g', '', '', 'g')]),
            ('g', [('g', '', '', '')]),
            ('gm', [('g', 'm', '', '')]),
            ('g:7', [('g', '', '7', '')]),
            ('gm:7', [('g', 'm', '7', '')]),
            ('d/fis', [('d', '', '', 'fis')]),
            ('gm/f', [('g', 'm', '', 'f')]),
            ('gm:7/d', [('g', 'm', '7', 'd')]),
            ('gm:13/5-/d', [('g', 'm', '13/5-', 'd')]),
            ):
            self.assertEquals(chordname_markup_tokenizer(s), v)

class TestOurLessonFiles(unittest.TestCase):
    def test_test_requirement(self):
        """
        Check that all lesson files that has the header.test variable
        also defines header.test_requirement
        """
        d = os.path.join("exercises", "standard", "lesson-files")
        for fn in os.listdir(d):
            if fn == 'Makefile':
                continue
            fullname = os.path.join(d, fn)
            if os.path.isfile(fullname):
                if fn.endswith("~") or fn.startswith("."):
                    continue
                f = parse_lesson_file_header(fullname)
                self.failIf(f is None, "Parsing lesson header failed: %s" % fullname)
                if 'test' in f.header:
                    self.failIf('test_requirement' not in f.header, fullname)

suite = unittest.makeSuite(TestParser)
suite.addTest(unittest.makeSuite(TestParserTranslations))
suite.addTest(unittest.makeSuite(TestMpdTransposable))
suite.addTest(unittest.makeSuite(TestChord))
suite.addTest(unittest.makeSuite(TestMusic))
suite.addTest(unittest.makeSuite(TestMusic3))
suite.addTest(unittest.makeSuite(TestVoiceCommon))
suite.addTest(unittest.makeSuite(TestVoice))
suite.addTest(unittest.makeSuite(TestRvoice))
suite.addTest(unittest.makeSuite(TestSatb))
suite.addTest(unittest.makeSuite(TestRhythm))
suite.addTest(unittest.makeSuite(TestPercussion))
suite.addTest(unittest.makeSuite(TestWavfile))
suite.addTest(unittest.makeSuite(TestMidifile))
suite.addTest(unittest.makeSuite(TestCmdline))
suite.addTest(unittest.makeSuite(TestCSound))
suite.addTest(unittest.makeSuite(TestMma))
suite.addTest(unittest.makeSuite(TestLessonfileHeader))
suite.addTest(unittest.makeSuite(TestLessonfileQuestion))
suite.addTest(unittest.makeSuite(TestLessonfileMisc))
suite.addTest(unittest.makeSuite(TestErrorHandling))
suite.addTest(unittest.makeSuite(TestLabelObject))
suite.addTest(unittest.makeSuite(TestOurLessonFiles))
