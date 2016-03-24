# Solfege - free ear training software
# Copyright (C) 2007, 2008, 2011 Tom Cato Amundsen
# License is GPL, see file COPYING

from __future__ import absolute_import
import unittest
import os

class TestSourceCode(unittest.TestCase):
    def test_next(self):
        for dirpath, dirnames, filenames in os.walk("."):
            if "test_sourcecode.py" in filenames:
                filenames.remove("test_sourcecode.py")
            for fn in filenames:
                if fn.endswith(".py"):
                    s = open(os.path.join(dirpath, fn), 'r').read()
                    self.assertEquals(s.find("os.getcwd()"), -1, "We should use os.getcwdu() and not getcwd(). Fix the file '%s'" % fn)

suite = unittest.makeSuite(TestSourceCode)

