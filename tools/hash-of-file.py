#!/usr/bin/python
# GNU Solfege - free ear training software
# Copyright (C) 2009, 2011 Tom Cato Amundsen
# Licence is GPL, see file COPYING

from __future__ import absolute_import
import sys
sys.path.insert(0, ".")

import textwrap
from solfege import i18n
i18n.setup(".")
from solfege import statistics

print 
print "\n".join(textwrap.wrap( 
 "The hash value is calculated using solfege.statistics.hash_of_lessonfile(filename). "
 "This is the sha1 hash value of the file after lines starting with # and empty "
 "lines have been removed."))

print
print "filename:", sys.argv[1]
print "    replaces = \"%s\"" % statistics.hash_of_lessonfile(unicode(sys.argv[1]))
print
