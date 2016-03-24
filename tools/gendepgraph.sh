#!/bin/bash

./tools/py2depgraph.py solfege.py > ut.deps
cat ut.deps | ./tools/depgraph2dot.py > ut.dot

cat ut.dot | dot -T png -o ut.png
