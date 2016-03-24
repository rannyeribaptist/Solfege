# vim: set fileencoding=utf8 :
# Solfege - free ear training software
# Copyright (C) 2007, 2008, 2011 Tom Cato Amundsen
# License is GPL, see file COPYING

from __future__ import absolute_import
import unittest
import codecs
import doctest
import os.path
from solfege.testlib import outdir

import solfege.cfg
from solfege.cfg import parse_file_into_dict
from solfege import cfg

class Test_parse_file_into_dict(unittest.TestCase):
    def test_parse_default_config(self):
        d = {}
        parse_file_into_dict(d, "default.config")
        self.assertEquals(d['gui']['expert_mode'], "false")
    def test_fail_on_non_utf8(self):
        filename = os.path.join(outdir, 'bad-unicode.ini')
        outfile = open(filename, 'w')
        outfile.write("# This file is not in utf8 encoding\n"
             "[sound]\n"
             "midi_player=/ABC/Us\xe9r\xa0\xff\xff\xff\x00r /bin/timidity\n")
        outfile.close()
        d = {}
        self.assertRaises(UnicodeDecodeError, parse_file_into_dict, d, filename)
        os.remove(filename)
    def test_parse_utf8(self):
        filename = os.path.join(outdir, 'ok-utf8.ini')
        outfile = codecs.open(filename, 'w', 'utf-8')
        outfile.write(u"# This file is in utf8 encoding\n"
                      u"[sound]\n"
                      u"s=/home/Usér/bin/prog\n"
                      u"f=1.1\n"
                      u"i=3\n")
        outfile.close()
        d = {}
        parse_file_into_dict(d, filename)
        self.assertEquals(d['sound']['i'], u'3')
        self.assertEquals(d['sound']['f'], u'1.1')
        self.assertEquals(d['sound']['s'], u'/home/Us\xe9r/bin/prog')
        self.assert_(isinstance(d['sound']['s'], basestring))
        self.assert_(isinstance(d['sound']['s'], unicode))
    def test_set_str(self):
        cfg.set_string("abc/def", "str string")
        cfg.set_string("abc/ghi", u"unicode string ØÆÅ")
        self.assert_(isinstance(cfg.get_string("abc/def"), unicode))
        self.assert_(isinstance(cfg.get_string("abc/ghi"), unicode))

suite = unittest.makeSuite(Test_parse_file_into_dict)
suite.addTest(doctest.DocTestSuite(solfege.cfg))
