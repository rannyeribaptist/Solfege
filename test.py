#!/usr/bin/python
# Solfege - free ear training software
# Copyright (C) 2007, 2008, 2011 Tom Cato Amundsen
# License is GPL, see file COPYING

from __future__ import absolute_import
import unittest
import sys
import os
import shutil
import atexit

# we need this hack because doctest messes with _
def f(s):
    if type(s) == type(""):
        print "'%s'" % s
    elif s is None:
        return
    else:
        print s

sys.__displayhook__ = f

from solfege import testlib
import solfege.i18n
solfege.i18n.setup(".")

from solfege import lessonfile
lessonfile.infocache = lessonfile.InfoCache()
import solfege.statistics
solfege.db = solfege.statistics.DB(None)

import tempfile
lessonfile.MusicBaseClass.temp_dir = tempfile.mkdtemp(prefix="solfege-")

from solfege import cfg
cfg.initialise("default.config", None, "")
cfg.set_int('config/preferred_instrument', 0)
cfg.set_int('config/lowest_instrument', 1)
cfg.set_int('config/middle_instrument', 2)
cfg.set_int('config/highest_instrument', 3)
cfg.set_int('config/lowest_instrument_volume', 121)
cfg.set_int('config/middle_instrument_volume', 122)
cfg.set_int('config/highest_instrument_volume', 123)
cfg.set_bool('config/override_default_instrument', False)
cfg.set_bool('testing/may_play_sound', False)

if os.path.exists(testlib.outdir):
    shutil.rmtree(testlib.outdir)
os.mkdir(testlib.outdir)

from solfege import soundcard
from solfege.osutils import *
soundcard.initialise_external_midiplayer()

soundcard.synth.start_testmode()


import solfege.mpd.tests
import solfege.soundcard.tests
import solfege.tests
import solfege.tests.test_cfg

# test_cfg has to be called last because it changes the cfg database.
suite = unittest.TestSuite((
    solfege.mpd.tests.suite,
    solfege.soundcard.tests.suite,
    solfege.tests.suite,
    solfege.tests.test_cfg.suite,
))

class MyProg(unittest.TestProgram):
    USAGE = """\
Usage: %(progName)s [options] [test] [...]

Options:
  -h, --help       Show this message
  -v, --verbose    Verbose output
  -q, --quiet      Minimal output

Examples:
  %(progName)s             - run default set of tests
  %(progName)s substring   - run any tests that contains substring it its
                             name or module name
"""


def iter_suite(suite):
    for t in suite:
        if isinstance(t, unittest.TestSuite):
            for xx in iter_suite(t):
                yield xx
        else:
            yield t

def rmtemp():
    shutil.rmtree(testlib.outdir)
    if os.path.exists(testlib.TmpFileBase.tmpdir):
        os.rmdir(testlib.TmpFileBase.tmpdir)

atexit.register(rmtemp)

testlib.TmpFileBase.tmpdir
if not os.path.exists(testlib.TmpFileBase.tmpdir):
    os.makedirs(testlib.TmpFileBase.tmpdir)

args = [x for x in sys.argv[1:] if x not in ('-v', '-q', '-h')]
if args and '-h' not in sys.argv:
    new_suite = unittest.TestSuite()
    r = unittest.TestResult()
    for test in iter_suite(suite):
        for a in args:
            if a in test.id():
                new_suite.addTest(unittest.defaultTestLoader.loadTestsFromName(test.id()))
    result = unittest.TextTestRunner(verbosity=1 + int('-v' in sys.argv) - int('-q' in sys.argv)).run(new_suite)
    sys.exit(not result.wasSuccessful())


sys.argv.append("suite")

MyProg()

