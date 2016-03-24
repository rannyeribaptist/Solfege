# Solfege - free ear training software
# Copyright (C) 2007, 2008, 2011 Tom Cato Amundsen
# License is GPL, see file COPYING

from __future__ import absolute_import
import unittest

import glob
import os.path
modules = [os.path.splitext(os.path.basename(x))[0] \
           for x in glob.glob("solfege/mpd/tests/test_*.py")]

for m in modules:
    exec "import solfege.mpd.tests.%s" % m
suite = unittest.TestSuite([globals()[m].suite for m in modules])
