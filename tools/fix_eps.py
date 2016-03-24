#!/usr/bin/python2.4

import sys

f = file(sys.argv[1], 'r')
s = f.read()
f.close()
v = s.split("\n")
for x,line in enumerate(v):
    if line.startswith("%%BoundingBox:") or line.startswith("%%HiResBoundingBox:"):
        lv = line.split()
        lv[2] = '0'
        v[x] = " ".join(lv)
f = file(sys.argv[1], 'w')
f.write("\n".join(v))
f.close()
