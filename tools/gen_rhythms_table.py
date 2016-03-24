#!/usr/bin/python

import os
import sys
# We need to do this on the build server. For some reason, it is not
# necessary on my workstation.
sys.path.insert(0, os.getcwdu())

import solfege.const

img_str = """%i:<inlinemediaobject>
      <imageobject>
        <imagedata fileref="../../graphics/rhythm-%s.png" format="PNG"/>
      </imageobject>
      <textobject>
       <phrase>%s</phrase>
      </textobject>
    </inlinemediaobject>"""
f = open("help/C/rhythmtable.xml", "w")
print >> f, "<para>"
for i, r in enumerate(solfege.const.RHYTHMS):
    print >> f, img_str % (i, r.replace(" ", ""), r),
    if i != len(solfege.const.RHYTHMS) - 1:
        print >> f, ", "
print >> f, "</para>"
f.close()
