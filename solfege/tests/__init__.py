# Solfege - free ear training software
# Copyright (C) 2007, 2008, 2011 Tom Cato Amundsen
# License is GPL, see file COPYING

from __future__ import absolute_import
import unittest

import glob
import os.path
# We have to filter out the tests in test_cfg because it changes
modules = [os.path.splitext(os.path.basename(x))[0] \
           for x in glob.glob("solfege/tests/test_*.py") if 'test_cfg' not in x]

for m in modules:
    exec "import solfege.tests.%s" % m
suite = unittest.TestSuite([globals()[m].suite for m in modules])
