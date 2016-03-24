# Solfege - free ear training software
# Copyright (C) 2007, 2008, 2011 Tom Cato Amundsen
# License is GPL, see file COPYING

import unittest
from solfege.mpd.elems import Clef, UnknownClefException, Stem, Skip, Note
from solfege.mpd.parser import parse_to_score_object, ParseError, validate_only_notenames
from solfege import mpd
import solfege.mpd.lexer

from solfege.mpd import Rat

class TestClef(unittest.TestCase):
    def test_constructor_ok(self):
        c = Clef("violin")
        self.assertEquals(c.m_octaviation, 0)
        self.assertEquals(c.m_name, "violin")
        c = Clef("violin_8")
        self.assertEquals(c.m_octaviation, -7)
    def test_constructor_unknown_clef(self):
        self.assertRaises(UnknownClefException, Clef, "not a clefname")
        self.assertRaises(UnknownClefException, Clef, "violin _ 8")
    def test_octaviation(self):
        self.assertEquals(Clef("violin").steps_to_ylinepos(0), 13)
        self.assertEquals(Clef("violin_8").steps_to_ylinepos(0), 13 - 7)
    def test_steps_to_ylinepos(self):
        for s, c, o, i in (
            ("violin", "violin", 0, 13),
            ("violin_8", "violin", -7, 13 - 7),
            ("violin_15", "violin", -14, 13 - 14),
            ("violin^8", "violin", 7, 13 + 7),
            ("violin^15", "violin", 14, 13 + 14),
            ):
            clef = Clef(s)
            self.assertEquals(clef.m_name, c)
            self.assertEquals(clef.m_octaviation, o)
            self.assertEquals(clef.steps_to_ylinepos(0), i)

class TestMpdParser(unittest.TestCase):
    """
    These tests does not check that the engraving is correct,
    but we at least know that the parser and engraver does not
    crash.
    """
    def _check(self, e, s, substring):
        """
        e is an exception.
        s is the string to search in
        substring is the string to find
        """
        self.assertEquals(s.split("\n")[e.m_lineno]
                                       [e.m_linepos1:e.m_linepos2], substring)
    def test_rest(self):
        # cmp to 1 because this is one track
        self.assertEquals(len(mpd.music_to_tracklist(r"\staff {r}")), 1)
    def test_skip(self):
        score = parse_to_score_object(r"\staff{ c s }")
        d = score.m_staffs[0].m_voices[0].m_tdict
        self.assert_(isinstance(d[mpd.Rat(0, 1)]['elem'], Stem))
        self.assert_(isinstance(d[mpd.Rat(1, 4)]['elem'][0], Skip))
    def test_dotted_rest(self):
        self.assertEquals(len(mpd.music_to_tracklist(r"\staff {r4.}")), 1)
        self.assertEquals(len(mpd.music_to_tracklist(r"\staff {r4..}")), 1)
    def test_dottt(self):
        t = mpd.music_to_tracklist(r"\staff { c4 r4. c4 }")
        self.assertEquals(t[0].str_repr(), "n48 d1/4 o48 d3/8 n48 d1/4 o48")
        t = mpd.music_to_tracklist(r"\staff { c4 r4.. c4 }")
        self.assertEquals(t[0].str_repr(), "n48 d1/4 o48 d7/16 n48 d1/4 o48")
        t = mpd.music_to_tracklist(r"\staff { c4.. c16 }")
        self.assertEquals(t[0].str_repr(), "n48 d7/16 o48 n48 d1/16 o48")
    def test_parse_brace_not_allowed(self):
        s = "\\staff{ c4 { e \n" \
            "}"
        try:
            t = mpd.music_to_tracklist(s)
        except ParseError, e:
            self._check(e, s, '{')
            self.assertEquals((e.m_linepos1, e.m_linepos2), (11, 12))
        else:
            self.assertFalse("No exception raised!")
    def test_parse_err1(self):
        s = "\\staff{ c4 < d < e \n" \
            "}"
        try:
            t = mpd.music_to_tracklist(s)
        except ParseError, e:
            self._check(e, s, '<')
            self.assertEquals((e.m_linepos1, e.m_linepos2), (15, 16))
        else:
            self.assertFalse("No exception raised!")
    def test_parse_err2(self):
        s = "\\staff{ \n" \
            "  c4 < d < e \n" \
            "}"
        try:
            t = mpd.music_to_tracklist(s)
        except ParseError, e:
            self._check(e, s, '<')
            self.assertEquals((e.m_linepos1, e.m_linepos2), (9, 10))
        else:
            self.assertFalse("No exception raised!")
    def test_parse_err3(self):
        s = "\\staff{ \n" \
            "  c4 d > \times 3/2"
        try:
            t = mpd.music_to_tracklist(s)
        except ParseError, e:
            self._check(e, s, '>')
            self.assertEquals((e.m_linepos1, e.m_linepos2), (7, 8))
        else:
            self.assertFalse("No exception raised!")
    def test_parse_times_do_not_nest(self):
        s = "\\staff { c4 \\times 3/2 { \\times 3/2 { c4 c4 } } }\n"
        try:
            t = mpd.music_to_tracklist(s)
        except ParseError, e:
            self._check(e, s, '\\times 3/2 {')
            self.assertEquals((e.m_linepos1, e.m_linepos2), (25, 37))
        else:
            self.assertFalse("No exception raised!")
    def test_parse_addvoice_before_staff(self):
        s = "   \\addvoice { \n" \
            "  c4 d }"
        try:
            t = mpd.music_to_tracklist(s)
        except ParseError, e:
            self._check(e, s, '\\addvoice')
            self.assertEquals((e.m_linepos1, e.m_linepos2), (3, 12))
        else:
            self.assertFalse("No exception raised!")
    def test_whitespace_at_end(self):
        s = "   \\staff { \n" \
            "  c4 d } \n" \
            "\t \n"
        t = mpd.music_to_tracklist(s)
    def test_relative(self):
        s = r"\staff\relative d'{ d f }"
        score = parse_to_score_object(s)
        self.assertEquals(score.voice11.m_tdict[Rat(0, 1)]['elem'][0],
                          Note.new_from_string("d'4"))
        self.assertEquals(score.voice11.m_tdict[Rat(1, 4)]['elem'][0],
                          Note.new_from_string("f'4"))
    def test_transpose(self):
        s = r"\staff\transpose d'{ c d }"
        score = parse_to_score_object(s)
        self.assertEquals(score.voice11.m_tdict[Rat(0, 1)]['elem'][0],
                          Note.new_from_string("d4"))
        self.assertEquals(score.voice11.m_tdict[Rat(1, 4)]['elem'][0],
                          Note.new_from_string("e4"))
        s = r"\staff\transpose d''{ c d }"
        score = parse_to_score_object(s)
        self.assertEquals(score.voice11.m_tdict[Rat(0, 1)]['elem'][0],
                          Note.new_from_string("d'4"))
        self.assertEquals(score.voice11.m_tdict[Rat(1, 4)]['elem'][0],
                          Note.new_from_string("e'4"))
    def test_transpose_relative(self):
        s = r"\staff\transpose d'\relative c'{ c d }"
        score = parse_to_score_object(s)
        self.assertEquals(score.voice11.m_tdict[Rat(0, 1)]['elem'][0],
                          Note.new_from_string("d'4"))
        self.assertEquals(score.voice11.m_tdict[Rat(1, 4)]['elem'][0],
                          Note.new_from_string("e'4"))
        s = r"\staff\transpose d''\relative c'{ c d e}"
        score = parse_to_score_object(s)
        self.assertEquals(score.voice11.m_tdict[Rat(0, 1)]['elem'][0],
                          Note.new_from_string("d''4"))
        self.assertEquals(score.voice11.m_tdict[Rat(1, 4)]['elem'][0],
                          Note.new_from_string("e''4"))
        self.assertEquals(score.voice11.m_tdict[Rat(1, 2)]['elem'][0],
                          Note.new_from_string("fis''4"))
    def test_partial_bar(self):
        s = r"\partial 4\staff\relative c'{ c d e }"
        score = parse_to_score_object(s)
    def test_bar_full(self):
        try:
            p = mpd.parser.parse_to_score_object(r"\staff{ c2. c }")
        except mpd.MpdException, e:
            self.assertEquals((e.m_lineno, e.m_linepos1, e.m_linepos2),
                              (0, 12, 13))
    def test_times(self):
        t = mpd.music_to_tracklist(r"\staff{ \times 2/3{c8 d e} }")
        self.assertEquals(t[0].str_repr(),
            "n48 d1/12 o48 n50 d1/12 o50 n52 d1/12 o52")
        score = parse_to_score_object(r"\staff{ \times 2/3{c8 d e} }")

class TestLexer(unittest.TestCase):
    def test_simplest(self):
        l = mpd.lexer.Lexer("c4 r4")
        g = l.next()
        self.assertEquals(l.NOTE, g[0])
        self.assertEquals(g[1].m_duration.get_rat_value(), mpd.Rat(1, 4))
        g = l.next()
        self.assertEquals(l.REST, g[0])
        self.assertEquals(g[1].m_duration.get_rat_value(), mpd.Rat(1, 4))
    def test_note_dotting(self):
        l = mpd.lexer.Lexer("c4 c4. c.")
        self.assertEquals(l.next()[1].m_duration, mpd.duration.Duration(4, 0))
        t, m = l.next()
        self.assertEquals(t, mpd.lexer.Lexer.NOTE)
        self.assertEquals(m.m_duration, mpd.duration.Duration(4, 1))
        self.assertRaises(mpd.lexer.LexerError, l.next)
    def test_rest_dotting(self):
        l = mpd.lexer.Lexer("c4 r4. r.")
        self.assertEquals(l.next()[1].m_duration, mpd.duration.Duration(4, 0))
        t, m = l.next()
        self.assertEquals(t, mpd.lexer.Lexer.REST)
        self.assertEquals(m.m_duration, mpd.duration.Duration(4, 1))
        self.assertRaises(mpd.lexer.LexerError, l.next)
    def test_inherited_time_dotting(self):
        l = mpd.lexer.Lexer("r4.. c")
        t, m = l.next()
        self.assertEquals(t, mpd.lexer.Lexer.REST)
        self.assertEquals(m.m_duration, mpd.duration.Duration(4, 2))
        t, m = l.next()
        self.assertEquals(t, mpd.lexer.Lexer.NOTE)
        self.assertEquals(getattr(m, 'm_duration', None), None)
    def test_whitespace(self):
        l = mpd.lexer.Lexer("\t\nc4 \n r4   \n")
        g = l.next()
        self.assertEquals(l.NOTE, g[0])
        self.assertEquals(g[1].m_duration.get_rat_value(), mpd.Rat(1, 4))
        g = l.next()
        self.assertEquals(l.REST, g[0])
        self.assertEquals(g[1].m_duration.get_rat_value(), mpd.Rat(1, 4))
    def test_tokenizing(self):
        for music in (
                r"c d e",
                r"c4 d e8",
                r"c4 d8. e f4",
                r"\staff{ c }",
                r"\staff{ \time 3/4 c'8 g, }",
                r"\staff{ \time 3/4 c'8 g, } \addvoice{ c }",
                r"\staff{ \clef bass c }",
                r"\stemUp c \stemDown d \stemBoth e",
                r"\staff\transpose d'{ c }",
                r"\key a \minor c \key fis \major",
                r"c4 s2 s s8",
                r"r r2 r",
                r"\staff\relative g''{ c d e }",
                r"\times 2/3{ c }",
                r"\staff{ \tupletDown \times 2/3{ [ c'8 d' e' ] } }",
                r"c \tupletDown d \tupletBoth e \tupletUp f",
                r"< c4 e g >",
                r"[ c'8 e ]",
                r"\partial 8 c8",
                ):
            self.assertEquals(music, mpd.lexer.Lexer.to_string(list(mpd.lexer.Lexer(music))))
    def test_set_first_pitch_ok(self):
        fis = mpd.MusicalPitch.new_from_notename("fis")
        for s, n in (
            ("c d e", "fis d e"),
            ("<c'' e>", "<fis e>"),
            ("< c'' e>", "< fis e>"),
            (" c,,16", " fis16"),
            (" \n c d e", " \n fis d e"),
            (r"\clef bass c d e", r"\clef bass fis d e"),
            (r"\clef violin \time 3/8 g", r"\clef violin \time 3/8 fis"),
            (r'\clef "violin_8" d', r'\clef "violin_8" fis'),
            ("\\key g \\major \\time 2/4\n d'8 | [g g]",
             "\\key g \\major \\time 2/4\n fis8 | [g g]"),
            ("\nc", "\nfis"),
            ("\n\\time 3/4\nc d e", "\n\\time 3/4\nfis d e"),
            ("", ""),
            ):
            lex = mpd.lexer.Lexer(s)
            lex.set_first_pitch(fis)
            self.assertEquals(lex.m_string, n)
    def test_set_first_pitch_errors(self):
        fis = mpd.MusicalPitch.new_from_notename("fis")
        lex = mpd.lexer.Lexer("c d ERR e f")
        lex.set_first_pitch(fis)
        self.assertEquals(lex.m_string, "fis d ERR e f")
        #
        lex = mpd.lexer.Lexer("\clef bass c d ERR e f")
        lex.set_first_pitch(fis)
        self.assertEquals(lex.m_string, "\clef bass fis d ERR e f")
        #
        lex = mpd.lexer.Lexer("\clef bass c d ERR e f")
        lex.set_first_pitch(fis)
        self.assertEquals(lex.m_string, "\clef bass fis d ERR e f")
    def test_m_notelen(self):
        lexer = mpd.lexer.Lexer("c8 d s16 r32")
        toc, toc_data = lexer.next()
        self.assertEquals(toc_data.m_duration.get_rat_value(), mpd.Rat(1, 8))
        self.assertEquals(lexer.m_notelen.get_rat_value(), mpd.Rat(1, 8))
        toc, toc_data = lexer.next()
        self.assertEquals(lexer.m_notelen.get_rat_value(), mpd.Rat(1, 8))
        toc, toc_data = lexer.next()
        self.assertEquals(toc_data.m_duration.get_rat_value(), mpd.Rat(1, 16))
        toc, toc_data = lexer.next()
        self.assertEquals(toc_data.m_duration.get_rat_value(), mpd.Rat(1, 32))
    def test_partial(self):
        lexer = mpd.lexer.Lexer(r"\partial 4. \staff")
        toc, toc_data = lexer.next()
        self.assertEquals(toc, lexer.PARTIAL)
        self.assertEquals(toc_data, mpd.duration.Duration.new_from_string("4."))
        toc, toc_data = lexer.next()
        self.assertEquals(toc, lexer.STAFF)

class TestFunctions(unittest.TestCase):
    def test_validate_only_notenames(self):
        self.assertEquals(validate_only_notenames("c e g"), (None, None, None))
        self.assertEquals(validate_only_notenames("c4 e2 g"), (None, None, None))
        self.assertEquals(validate_only_notenames("c4 e2 g~ g"), (0, 7, 8))
        self.assertEquals(validate_only_notenames("c4 [e8 e] "), (0, 3, 4))
        self.assertEquals(validate_only_notenames("c ERR g"), (0, 2, 5))
        self.assertEquals(validate_only_notenames("c\nERR\ng"), (1, 0, 3))
        self.assertEquals(validate_only_notenames("c\n  ERR\ng"), (1, 2, 5))

class TestScore(unittest.TestCase):
    def test_timelist(self):
        score = parse_to_score_object(
            r"\staff{c2    r4 r8 a8}"
            r"\staff{c4 c2    r8 g8}")
        self.assertEquals(score.get_timelist(), [
            [True, Rat(1, 4)],
            [True, Rat(1, 2)],
            [False, Rat(1, 8)],
            [True, Rat(1, 8)],
        ])
        score = parse_to_score_object(
            r"\staff{c4   d8 }"
            r"\staff{r8 e    }")
        self.assertEquals(score.get_timelist(), [
            [True, Rat(1, 8)],
            [True, Rat(1, 8)],
            [True, Rat(1, 8)],
        ])
        score = parse_to_score_object(
            r"\staff{c4    r8 r8 d8 }"
            r"\staff{r8 e8 r8 r4   }")
        self.assertEquals(score.get_timelist(), [
            [True, Rat(1, 8)],
            [True, Rat(1, 8)],
            [False, Rat(1, 4)],
            [True, Rat(1, 8)],
        ])

suite = unittest.makeSuite(TestClef)
suite.addTest(unittest.makeSuite(TestMpdParser))
suite.addTest(unittest.makeSuite(TestFunctions))
suite.addTest(unittest.makeSuite(TestLexer))
suite.addTest(unittest.makeSuite(TestScore))
