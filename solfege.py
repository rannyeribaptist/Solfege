#!/usr/bin/python
# vim: set fileencoding=utf8:
# GNU Solfege - free ear training software
# Copyright (C) 2000, 2001, 2002, 2003, 2004, 2005, 2007, 2008, 2011  Tom Cato Amundsen
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

# This script is used to launch Solfege when running
# it from the source dir without installing.
from __future__ import absolute_import
import __builtin__
import time
__builtin__.start_time = time.time()

import sys
import os
import os.path
import shutil

from solfege import cfg
from solfege import filesystem

if sys.platform == 'win32':
    # Migration added in solfege 3.9.0.
    try:
        if not os.path.exists(filesystem.app_data()):
            if os.path.exists(os.path.join(filesystem.get_home_dir(), ".solfege")):
                shutil.copytree(os.path.join(filesystem.get_home_dir(), ".solfege"),
                                filesystem.app_data())
            else:
                os.mkdir(filesystem.app_data())
        if not os.path.exists(filesystem.rcfile()):
            if os.path.exists(os.path.join(filesystem.get_home_dir(), ".solfegerc")):
                shutil.copy(os.path.join(filesystem.get_home_dir(), ".solfegerc"),
                            filesystem.rcfile())
    except (IOError, os.error), e:
        print "Migration failed:", e

from solfege import presetup
presetup.presetup("default.config", None, filesystem.rcfile())

# i18n should be imported very early in program init because it setup
# the _ and _i functions for the whole program.

from solfege import i18n
i18n.setup(".", cfg.get_string("app/lc_messages"))
import solfege.startup
solfege.startup.start_app(".")
