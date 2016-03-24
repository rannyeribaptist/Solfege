# vim: set fileencoding=utf-8 :
# Solfege - free ear training software
# Copyright (C) 2011 Tom Cato Amundsen
# License is GPL, see file COPYING

from __future__ import absolute_import

import os
import unittest

from solfege import dataparser
from solfege.dataparser import Dataparser
from solfege.lfmod import parse_tree_interpreter
from solfege.testlib import TmpFileBase
import solfege.parsetree as pt

class TestLfMod(TmpFileBase):
    parserclass = Dataparser
    def get_mod(self, builtins=None):
        return parse_tree_interpreter(self.p.tree, builtins)
    def test_simplest(self):
        self.do_file("a = 1  b = 5")
        mod = self.get_mod()
        self.assertEquals(mod.m_globals['a'], 1)
        self.assertEquals(mod.m_globals['b'], 5)
    def test_list_assignment(self):
        self.do_file("s = 3, 4, 5 ")
        self.assertEquals(self.get_mod().m_globals['s'], [3, 4, 5])
    def test_addition(self):
        self.do_file("a = 3 + 4")
        mod = self.get_mod()
        self.assertEquals(mod.m_globals['a'], 7)
        self.assertTrue(isinstance(self.p.tree[0], pt.Assignment))
        self.assertTrue(isinstance(self.p.tree[0].left, pt.Identifier))
        self.assertTrue(isinstance(self.p.tree[0].right, pt.Addition))
    def test_question(self):
        self.do_file("a = 2 question { q = 2 }")
        mod = self.get_mod()
        self.assertEquals(mod.m_globals.keys(), ['a'])
        self.assertEquals(mod.m_blocklists['question'][0]['q'], 2)
    def test_nested_block(self):
        """
        parse_tree_interpreter does not handle nested blocks, even though
        Dataparser and parse does.
        FIXME: an exception and error message that make sense for end
        users would be preferred.
        """
        self.do_file("question { a = 4 subbl { b = 5 } }")
        self.assertRaises(Exception, self.get_mod)
    def test_named_block(self):
        self.do_file("element I { q = 2 }")
        mod = self.get_mod()
        self.assert_('I' in mod.m_globals)
        self.assertEquals(mod.m_globals['I']['q'], 2)
    def test_global_lookup_in_question(self):
        self.do_file("\n".join([
            "a = 3",
            "question { q = a }",
        ]))
        mod = self.get_mod()
        self.assertEquals(mod.m_globals['a'], 3)
        self.assertEquals(mod.m_blocklists['question'][0]['q'], 3)
    def test_music_shortcut(self):
        def chord(s): return s
        self.do_file('question { name="test-name" chord("c e g") } ')
        mod = self.get_mod({'chord': (None, chord)})
        self.assertEquals(mod.m_blocklists['question'][0]['name'], "test-name")
        self.assertEquals(mod.m_blocklists['question'][0]['music'], "c e g")
    def test_global_lookup_in_question_redef_global(self):
        self.do_file("\n".join([
            "a = 3",
            "question { q = a }",
            "a = 4",
            "question { q = a }",
        ]))
        mod = self.get_mod()
        self.assertEquals(mod.m_blocklists['question'][0]['q'], 3)
        self.assertEquals(mod.m_blocklists['question'][1]['q'], 4)
        self.assertEquals(mod.m_globals['a'], 4)
    def test_1level_namespace_lookup(self):
        self.p.parse_file("solfege/tests/lesson-files/test_absolute_import_not_found_load_relative")
        mod = parse_tree_interpreter(self.p.tree)
        self.assertEquals(mod.m_globals['var'], 55)

suite = unittest.makeSuite(TestLfMod)

