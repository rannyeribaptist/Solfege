# GNU Solfege - free ear training software
# Copyright (C) 2005, 2007, 2008, 2011  Tom Cato Amundsen
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

from __future__ import absolute_import
"""
This file does the checking for optional features that depend on
python modules the user can have installed.

It also does sanity check on the python and gtk versions and some
other initial setup tasks.
"""

import sys
import os
import textwrap

def assert_python_version(required_version):
    if sys.version_info < required_version:
        sys.exit("Solfege need Python %s or newer. The configure script told you so.\nThis is Python %s" % (".".join([str(i) for i in required_version]), sys.version))

def init(options):
    # this is needed for py2exe
    if sys.platform == 'win32':
        os.environ['PATH'] += ";lib;bin;"
    from gi.repository import Gtk
    assert_python_version((2, 7))
    Gtk.check_version(3, 4, 0)

