#!/usr/bin/python

"""
This is a wrapper around the pydoc script. It is necessary to use this on
most of the files in solfege because they require i18n setup.
"""

import sys
import pydoc
sys.path.insert(0, ".")
import solfege.i18n
solfege.i18n.setup(".")

pydoc.cli()

