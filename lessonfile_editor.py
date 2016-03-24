#!/usr/bin/python
# GNU Solfege - free ear training software
# Copyright (C) 2004, 2005, 2006, 2011  Tom Cato Amundsen
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
TODO/BUGS
=========

The program only runs from sourcedir. It cannot be installed.

If you open a file that includes other files, the questions from all
files will be edited as a single file, and when you save, the include
statement will be missing, and all questions are saved in one file.
The included files are un-touched.

"""

print "The lessonfile editor is broken now."
# We use this variable because debian/rules will replace it when
# building the debian package.
solfege_version = buildinfo.VERSION_STRING

import os
import sys
prefix =  os.path.split(os.path.dirname(os.path.abspath(sys.argv[0])))[0]

if sys.argv[0] == './lessonfile_editor.py':
        datadir = "."
else:
    datadir = os.path.join("@prefix@", "share", "solfege")
    sys.path.append(datadir)

import src.i18n
src.i18n.setup(prefix)

import src.lessonfile_editor_main
src.lessonfile_editor_main.main(datadir)
