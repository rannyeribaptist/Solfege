#!/usr/bin/python

import os
import sys
import re
from subprocess import *
import time

def run(cmd):
    print "run:", cmd
    os.system(cmd)

def get_image_dim(fn):
    output = Popen(["file", fn], stdout=PIPE).communicate()[0]
    r = re.compile("(\d+)\s*x+\s*(\d+)")
    m = r.search(output)
    if m:
        return int(m.groups()[0]), int(m.groups()[1])
    else:
        return None, None

def do_file(fn, width):
    time.sleep(2)
    f, ext = os.path.splitext(fn)
    run("import -frame %s" % fn)
    #x, y = get_image_dim(fn)
    run("pngnq -n 16 -f %s" % fn)
    run("mv %s-nq8.png %s" % (f, fn))
    #if not width:
    #    width = 510
    #if x > width:
    #    run("convert -scale %i %s %s-resized.png" % (width, fn, f))
    #    run("mv %s-resized.png %s" % (f, fn))
    #run("pngquant -nofs 8 %s" % fn)
    #run("mv %s-or8.png %s" % (f, fn))

help = """
Usage: ./tools/screenshot path/to/image.png [width]

Make a screenshot using "import". Run this script, and then
click on the window you want to make a screenshot of.
"""
if len(sys.argv) not in (2, 3):
    print help
    sys.exit()
if sys.argv[1] in ('-h', '--help'):
    print help
    sys.exit()

try:
    width = int(sys.argv[2])
except:
    width = None
do_file(sys.argv[1], width)
print "Remember to use the Simple (Enkelt, nb_NO) theme."
