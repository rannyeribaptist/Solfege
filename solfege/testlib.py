# Solfege - free ear training software
# Copyright (C) 2007, 2008, 2011 Tom Cato Amundsen
# License is GPL, see file COPYING

# Utility functions used by the test suite.

from __future__ import absolute_import

import __builtin__
import os
import unittest

from solfege import i18n

__builtin__.testsuite_is_running = True

outdir = 'test-outdir'

class I18nSetup(unittest.TestCase):
    def setUp(self):
        self.__saved_LANGUAGE = os.environ.get('LANGUAGE', None)
        os.environ['LANGUAGE'] = 'nb'
        i18n.setup(".")
    def tearDown(self):
        if self.__saved_LANGUAGE:
            os.environ['LANGUAGE'] = self.__saved_LANGUAGE


class TmpFileBase(unittest.TestCase):
    """
    Sub-classes must set .parserclass
    """
    tmpdir = "solfege/tests/tmp-lesson-files"
    def setUp(self):
        self.p = self.parserclass()
        self.m_files = set()
    def add_file(self, content, filename):
        self.m_files.add(filename)
        outfile = open(os.path.join(self.tmpdir, filename), 'w')
        outfile.write(content)
        outfile.close()
    def do_file(self, content):
        self.add_file(content, u'testfile')
        self.p.parse_file(os.path.join(self.tmpdir, u'testfile'))
        return self.p
    def tearDown(self):
        for filename in self.m_files:
            os.remove(os.path.join(self.tmpdir, filename))

