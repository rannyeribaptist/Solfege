#!/usr/bin/python

import os
import glob
import sys

# ignore because they are screenshots in untranslated files:
IGNORE = ['chordname-example.png', 'progressionlabel-example-1.png', 'rnc-example.png']
exitval = 0
C_files = [os.path.split(n)[1] for n in glob.glob("help/C/figures/*.png")]
languages = [n for n in glob.glob("help/*") if os.path.isdir(n) and n != 'help/C']
for lang in languages:
    lang_files = [os.path.split(n)[1] for n in glob.glob("%s/figures/*.png" % lang)]
    missing_files = [n for n in C_files if n not in lang_files and n not in IGNORE]
    if missing_files:
        print "\nMissing screenshots for %s locale" % os.path.split(lang)[1]
        print missing_files
        exitval = -1

sys.exit(exitval)
