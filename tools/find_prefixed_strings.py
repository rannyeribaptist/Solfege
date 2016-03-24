#!/usr/bin/python
"""
Used to sanity check prefixes used in lesson files.
"""

import os
import sys
import re
import glob
import optparse

parser = optparse.OptionParser()
parser.add_option("-l", action="store_true", dest="list_strings",
    help="List the strings we find.")
parser.add_option("-v", action="store_true", dest="list_prefixes",
    help="List all prefixes")
parser.add_option("-p", dest="string_prefix",
    help="The 'PREFIX|xxx' to seach for.")
parser.add_option("-f", action="store_true", dest="display_filename",
    help="Show the name of the files the PREFIX is found in.")

(options, args) = parser.parse_args()

r = re.compile("\"%s\|(?P<prefix>.*?)\"" % options.string_prefix)
prefix_re = re.compile("\s*name\s*=\s*.*?\"(?P<prefix>.*?)\|.*?\"")
db = {}
def list_name_prefixes():
    prefixes = set()
    for fn in glob.glob("lesson-files/*"):
        if os.path.isfile(fn):
            s = open(fn, 'r').read()
            for match in prefix_re.finditer(s):
                if match.group('prefix') not in prefixes:
                    print match.group('prefix')
                    prefixes.add(match.group('prefix'))

if options.list_prefixes:
    list_name_prefixes()
    sys.exit()

for fn in glob.glob("lesson-files/*"):
    if os.path.isfile(fn):
        s = open(fn, 'r').read()
        for match in r.finditer(s):
            if match.group('prefix') not in db:
                print "Found prefix:", match.group('prefix')
                db[match.group('prefix')] = [fn]
            else:
                if db[match.group('prefix')][-1] != fn:
                    db[match.group('prefix')].append(fn)
if options.list_strings:
    for s in db.keys():
        print s
        if options.display_filename:
            for fn in db[s]:
                print "\t", fn

print "Skal vi bruke dim eller diminished?"
