# vim: set fileencoding=utf-8 :
# Solfege - free ear training software
# Copyright (C) 2007, 2008, 2011 Tom Cato Amundsen
# License is GPL, see file COPYING

from __future__ import absolute_import
import unittest
import traceback
import codecs

from solfege.testlib import I18nSetup, outdir, TmpFileBase
from solfege.dataparser import *
import solfege.parsetree as pt
import solfege.i18n
import os

class TestLexer(unittest.TestCase):
    def test_get_line(self):
        l = Lexer("""#comment1
#comment2
#comment3

var = 3
""", None)
        self.assertEquals(l.get_line(0), "#comment1")
        self.assertEquals(l.get_line(1), "#comment2")
        self.assertEquals(l.get_line(2), "#comment3")
        self.assertEquals(l.get_line(3), "")
        self.assertEquals(l.get_line(4), "var = 3")
    def test_scan(self):
        p = Dataparser()
        p._lexer = Lexer("\"string\" name 1.2 2 (", p)
        self.assertEquals(p._lexer.scan(STRING), "string")
        self.assertEquals(p._lexer.scan(NAME), "name")
        self.assertEquals(p._lexer.scan(FLOAT), "1.2")
        self.assertEquals(p._lexer.scan(INTEGER), "2")
        p._lexer = Lexer("1 2 3", p)
        try:
            p._lexer.scan(STRING)
        except DataparserException, e:
            self.assertEquals(u"(line 1): 1 2 3\n"
                              u"          ^",
                              e.m_nonwrapped_text)
        else:
            self.fail("DataparserException not raised")
    def test_unable_to_tokenize(self):
        p = Dataparser()
        try:
            p._lexer = Lexer("question { a = 3} |!", p)
        except UnableToTokenizeException, e:
            self.assertEquals("(line 1): question { a = 3} |!\n"
                              "                            ^",
                              e.m_nonwrapped_text)
        else:
            self.fail("UnableToTokenizeException not raised")
        try:
            p._lexer = Lexer("x = 4\n"
                             "question { a = 3} |!", p)
        except UnableToTokenizeException, e:
            self.assertEquals("(line 1): x = 4\n"
                              "(line 2): question { a = 3} |!\n"
                              "                            ^",
                              e.m_nonwrapped_text)
        else:
            self.fail("UnableToTokenizeException not raised")
    def test_encodings_utf8(self):
        s = u"""
        name = "øæå" """
        f = codecs.open(os.path.join(outdir, "file1"), 'w', 'utf-8')
        f.write(s)
        f.close()
        f = open(os.path.join(outdir, "file1"), 'rU')
        s = f.read()
        f.close()
        p = Dataparser()
        p._lexer = Lexer(s, p)
        self.assertEquals(p._lexer.m_tokens[2][1], u"øæå")
    def test_encodings_iso88591(self):
        s = u'#vim: set fileencoding=iso-8859-1 : \n' \
            u'name = "øæå" '
        f = codecs.open(os.path.join(outdir, "file1"), 'w', 'iso-8859-1')
        f.write(s)
        f.close()
        f = open(os.path.join(outdir, "file1"), 'rU')
        s = f.read()
        f.close()
        p = Dataparser()
        p._lexer = Lexer(s, p)
        self.assertEquals(p._lexer.m_tokens[2][1], u"øæå")
    def _test_encodings_delcar_not_first(self):
        """
        FIXME: I disabled this test because people suddenly started
        to report that UnableToTokenizeException was not raised.
        """
        s = '#\n#\n#vim: set fileencoding=iso-8859-1 : \n' \
            'name = "øæå" '
        f = codecs.open(os.path.join(outdir, "file1"), 'w', 'iso-8859-1')
        f.write(s)
        f.close()
        f = open(os.path.join(outdir, "file1"), 'rU')
        s = f.read()
        f.close()
        self.assertRaises(UnableToTokenizeException,
            Lexer, s, Dataparser())
    def _test_missing_encoding_definition_iso88591(self):
        """
        FIXME: I disabled this test because people suddenly started
        to report that UnableToTokenizeException was not raised.
        We write a simple datafile in iso-8859-1 encoding, but does not
        add the encoding line. The dataparser will assume files are utf-8
        by default, and will fail to tokenize.
        """
        s = 'name = "øæå" '
        f = codecs.open(os.path.join(outdir, "file1"), 'w', 'iso-8859-1')
        f.write(s)
        f.close()
        f = open(os.path.join(outdir, "file1"), 'rU')
        s = f.read()
        f.close()
        self.assertRaises(UnableToTokenizeException,
            Lexer, s, Dataparser())
    def test_X(self):
        s = r"""
question {
   music = music("\staff \stemUp  {
   \clef violin \key d \minor \time 4/4
    c4
    }a")
}
"""
        p = Dataparser()
        p._lexer = Lexer(s, p)

class TestDataParser(TmpFileBase):
    parserclass = Dataparser
    def assertRaisedIn(self, methodname):
        t = traceback.extract_tb(sys.exc_info()[2])
        self.assertEquals(t[-1][2], methodname)
    def test_exception_statement_1(self):
        try:
            self.do_file("b")
        except DataparserSyntaxError, e:
            self.assertRaisedIn('statement')
            self.assertEquals(u"(line 1): b\n"+
                              u"           ^",
                              e.m_nonwrapped_text)
            self.assertEquals(e.m_token, ('EOF', None, 1, 0))
        else:
            self.fail("DataparserSyntaxError not raised")
    def test_exception_statement_2(self):
        try:
            self.do_file("a)")
        except DataparserSyntaxError, e:
            self.assertRaisedIn('statement')
            self.assertEquals(u"(line 1): a)\n"+
                              u"           ^",
                              e.m_nonwrapped_text)
            self.assertEquals(e.m_token, (')', ')', 1, 0))
        else:
            self.fail("DataparserSyntaxError not raised")
    def test_exception_statement_3(self):
        try:
            self.do_file("""#comment
  XYZ
""")
        except DataparserSyntaxError, e:
            self.assertRaisedIn('statement')
            self.assertEquals(u"(line 1): #comment\n"+
                              "(line 2):   XYZ\n"+
                              "(line 3): \n"+
                              "          ^",
                              e.m_nonwrapped_text)
        else:
            self.fail("DataparserSyntaxError not raised")
    def test_exception_statement_4(self):
        try:
            self.do_file("""#comment
  A)
""")

        except DataparserSyntaxError, e:
            self.assertRaisedIn('statement')
            self.assertEquals(u"(line 1): #comment\n"+
                              "(line 2):   A)\n"+
                              "             ^",
                              e.m_nonwrapped_text)
        else:
            self.fail("DataparserSyntaxError not raised")
    def test_exception_assignment(self):
        try:
            self.do_file("question = 3")
        except AssignmentToReservedWordException, e:
            self.assertRaisedIn('assignment')
            self.assertEquals(u"(line 1): question = 3\n" +
                              u"          ^",
                              e.m_nonwrapped_text)
        else:
            self.fail("AssignmentToReservedWordException not raised")
    def test_istr_translations_in_file1(self):
        p = self.do_file("""
         foo = "foo-C"
         foo[nb] = "foo-nb"
         question {
           var = "var-C"
           var[nb] = "var-nb"
         }
        """)
        self.assertEquals(p.tree[0].right.evaluate({}, {}),
                          u'foo-C')
        self.assertEquals(p.tree[1].right.evaluate({}, {}),
                          u'foo-nb')
        self.assertEquals(p.tree[2][0].right.evaluate({}, {}),
                          u'var-C')
        self.assertEquals(p.tree[2][1].right.evaluate({}, {}),
                          u'var-nb')
        self.assert_(isinstance(p.tree[2][0].right.evaluate({}, {}), istr))
    def test_istr_translations_in_file_lang_before_C(self):
        """
        The Dataparser will accept setting the translated var before the
        C locale. But the lesson file interpreter will report an
        error for this.
        """
        p = self.do_file("""
           foo[no] = "foo-no"
           foo = "foo-C"
        """)
        self.assertEquals(p.tree[0].left, "foo[no]")
        self.assertEquals(p.tree[0].right.m_value, u"foo-no")
        self.assertEquals(p.tree[0].right.m_value.cval, u"foo-no")
        self.assertEquals(p.tree[1].right.m_value, u"foo-C")
    def test_i18n_list_fails(self):
        try:
            self.do_file('foo[no] = "foo-no", "blabla" ')
        except CanOnlyTranslateStringsException, e:
            self.assertEquals(e.m_nonwrapped_text,
               u'(line 1): foo[no] = "foo-no", "blabla" \n'
               +'                    ^')
        else:
            self.fail("CanOnlyTranslateStringsException not raised")
    def test_i18n_int_fails(self):
        try:
            self.do_file('foo[no] = 8')
        except CanOnlyTranslateStringsException, e:
            self.assertEquals(e.m_nonwrapped_text,
               u'(line 1): foo[no] = 8\n'
               +'                    ^')
        else:
            self.fail("CanOnlyTranslateStringsException not raised")
    def test_import(self):
        p = self.do_file("\n".join([
            "import progression_elements",
            "t = progression_elements.I",
        ]))
        self.assertEquals(len(p.tree), 2)
        self.assert_(isinstance(p.tree[0], pt.Assignment))
        self.assert_(isinstance(p.tree[0].right, pt.Program))
        self.assert_(isinstance(p.tree[1], pt.Assignment))
        self.assert_(isinstance(p.tree[1].right, pt.Identifier))
    def test_import_as(self):
        p = self.do_file("\n".join([
            "import progression_elements as p",
            "t = p.I",
            "question {",
            "   prog = p.I",
            "}"]))
        self.assertEquals(len(p.tree), 3)
        self.assert_(isinstance(p.tree[0], pt.Assignment))
        self.assert_(isinstance(p.tree[0].right, pt.Program))
        self.assert_(isinstance(p.tree[1].right, pt.Identifier))
        self.assert_(isinstance(p.tree[2][0].right, pt.Identifier))
    def test_pt_2(self):
        p = self.do_file("""header {
        module = idbyname
        help = "idbyname-intonation"
        title = _("Is the interval flat, in tune or sharp? %s cent wrong") % 10
        lesson_heading = _("Just interval: %s") % _("Minor Second") + " (16:15)"
        filldir = vertic
}
        """)
        for d in p.tree[0]:
            if d.left == 'module':
                self.assertEquals(d.right, 'idbyname')
    def test_nested_block(self):
        """
        As we can see, the Dataparser class and the parsetree code
        can handle nested blocks.
        """
        p = self.do_file("question { a = 4 subbl { b = 5} }")
        self.assert_(isinstance(p.tree[0], pt.Block))
        self.assert_(isinstance(p.tree[0][0], pt.Assignment))
        self.assert_(isinstance(p.tree[0][1], pt.Block))
        self.assert_(isinstance(p.tree[0][1][0], pt.Assignment))
        self.assertEquals(p.tree[0][1][0].right.evaluate({}, {}), 5)
    def test_named_block(self):
        p = self.do_file('element I { label = "label-I" } '
                      +'element II { label = "label-II" }')
        self.assertEquals(len(p.tree), 2)
        self.assertEquals(len(p.tree[0]), 1)
        self.assertEquals(len(p.tree[1]), 1)
        self.assert_(isinstance(p.tree[0], pt.NamedBlock))
        self.assertEquals(p.tree[0][0].right.evaluate({}, {}), 'label-I')
        self.assert_(isinstance(p.tree[1], pt.NamedBlock))
        self.assertEquals(p.tree[1][0].right.evaluate({}, {}), 'label-II')

class TestIstr(I18nSetup):
    def test_musicstr(self):
        s = istr(r"\staff{ c e g }")
        self.assert_(isinstance(s, basestring))
    def test_add_translations1(self):
        #i18n.langs: nb_NO, nb, C
        # name = "Yes"
        # name[no] = "Ja"
        s = "Yes"
        s = istr(s)
        self.assertEquals(unicode(s), u'Yes')
        s = s.add_translation('nb', 'Ja')
        self.assertEquals(s, u'Ja')
        s = s.add_translation('nb_NO', 'Ja!')
        self.assertEquals(s, u'Ja!')
    def test_add_translations2(self):
        #i18n.langs: nb_NO, nb, C
        # name = "Yes"
        # name[no] = "Ja"
        s = "Yes"
        s = istr(s)
        self.assertEquals(s, u'Yes')
        s = s.add_translation('nb_NO', 'Ja!')
        self.assertEquals(s, u'Ja!')
        s = s.add_translation('nb', 'Ja')
        self.assertEquals(s, u'Ja!', "Should still be 'Ja!' because no_NO is preferred before no")
    def test_override_gettext(self):
        s = dataparser_i18n_func("major")
        self.assertEquals(s, "dur")
        self.assertEquals(s.cval, "major")
        s = s.add_translation('nb', "Dur")
        self.assertEquals(s, u"Dur")
    def test_type(self):
        s = istr("jo")
        self.assert_(type(s) == istr)
        self.assertRaises(TypeError, lambda s: type(s) == str)
        self.assert_(isinstance(s, istr))
        self.assert_(not isinstance(s, str))
        self.assert_(isinstance(s, unicode))

suite = unittest.makeSuite(TestLexer)
suite.addTest(unittest.makeSuite(TestDataParser))
suite.addTest(unittest.makeSuite(TestIstr))
