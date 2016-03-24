# vim: set fileencoding=utf8 :
# Solfege - free ear training software
# Copyright (C) 2009, 2011 Tom Cato Amundsen
# License is GPL, see file COPYING

from __future__ import absolute_import
import unittest
from solfege import statistics
from solfege import application
from solfege import lessonfile
from solfege import optionparser
from solfege.exercises import idbyname

class TestDB(unittest.TestCase):
    def test_en(self):
        s1 = "var = 1"
        s2 = "#comment\nvar = 1"
        s3 = "#comment\n\nvar = 1"
        self.assertEqual(statistics.hash_lessonfile_text(s1),
                         statistics.hash_lessonfile_text(s2))
        self.assertEqual(statistics.hash_lessonfile_text(s1),
                         statistics.hash_lessonfile_text(s3))
    def test_two(self):
        opt_parser = optionparser.SolfegeOptionParser()
        options, args = opt_parser.parse_args()
        a = application.SolfegeApp(options)
        t = idbyname.Teacher('idbyname')
        t.set_lessonfile(u'solfege:lesson-files/chord-min-major')
        t.m_statistics.reset_session()
        t.m_statistics.add_wrong('minor', 'major')
        t.m_statistics.add_wrong('minor', 'major')
        t.m_statistics.add_wrong('minor', 'minor')
        t.m_statistics.add_correct('major')
        for seconds in (-1, 0, 10000):
            self.assertEquals(t.m_statistics.get_num_correct_for_key(seconds, 'minor'), 1)
            self.assertEquals(t.m_statistics.get_num_guess_for_key(seconds, 'minor'), 3)
    def test_store_variables(self):
        db = statistics.DB()
        db.set_variable('database_version', 2)
        self.assertEquals(db.get_variable('database_version'), 2)
        db.set_variable('database_version', 3)
        self.assertEquals(db.get_variable('database_version'), 3)
        self.assertRaises(db.VariableTypeError,
            db.set_variable, 'database_version', '3')
        db.set_variable('textvar', u'this is кофе')
        self.assertEquals(db.get_variable('textvar'), u'this is кофе')
        self.assertRaises(db.VariableTypeError,
            db.set_variable, 'textvar', 5)
        self.assertRaises(db.VariableTypeError,
            db.set_variable, 'textvar', 5.5)
        self.assertRaises(db.VariableTypeError,
            db.set_variable, 'textvar', True)
        self.assertRaises(db.VariableTypeError,
            db.set_variable, 'str_text', 'string')
        db.set_variable('known_number', 3.14159265)
        self.assertEquals(db.get_variable('known_number'), 3.14159265)
        self.assertRaises(db.VariableUndefinedError,
            db.get_variable, 'e')
        db.del_variable('known_number')
        self.assertRaises(db.VariableUndefinedError,
            db.del_variable, 'does_not_exist')


suite = unittest.makeSuite(TestDB)
