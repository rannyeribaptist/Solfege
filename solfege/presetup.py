#!/usr/bin/python
# GNU Solfege - free ear training software
# Copyright (C) 2007, 2008, 2011  Tom Cato Amundsen
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


import os.path
import sys

from gi.repository import Gtk

from solfege import cfg
from solfege import filesystem
from solfege import i18n

def presetup(app_defaults_filename, system_filename, user_filename):
    if not os.path.exists(filesystem.app_data()):
        os.makedirs(filesystem.app_data())
    if not os.path.exists(filesystem.user_data()):
        os.makedirs(filesystem.user_data())
    try:
        cfg.initialise(app_defaults_filename, system_filename, user_filename)
    except UnicodeDecodeError, e:
        traceback.print_exc()
        print >> sys.stderr
        print >> sys.stderr, "\n".join(textwrap.wrap(
              "Your %s file is not properly utf8 encoded. Most likely"
              " it is the path to some external program that contain non-ascii"
              " characters. Please edit or delete the file. Or email it to"
              " tca@gnu.org, and he will tell you what the problem is." % filesystem.rcfile().encode("ascii", "backslashreplace")))
        print >> sys.stderr
        sys.exit("I give up (solfege.py)")
    except cfg.CfgParseException, e:
        i18n.setup(".")
        a, b = os.path.split(user_filename)
        renamed_fn = os.path.join(a, "BAD-"+b)
        m = Gtk.MessageDialog(None, Gtk.DialogFlags.MODAL, Gtk.MessageType.ERROR,
                Gtk.ButtonsType.NONE,
                _("Parsing %s failed") % filesystem.rcfile())
        m.format_secondary_text(str(e) + "\n\n" + _("We cannot recover from this, we can rename the corrupt file to %s and then start the program." % renamed_fn))
        m.add_buttons("Rename", 10)
        m.add_buttons(Gtk.STOCK_QUIT, 11)
        m.set_default_response(11)
        ret = m.run()
        if ret == 10:
            os.rename(user_filename, renamed_fn)
            m.destroy()
            cfg.initialise(app_defaults_filename, system_filename, user_filename)
        else:
            sys.exit(1)
    # MIGRATION from 2.9.2 to 2.9.3
    if cfg.get_string("app/lc_messages") == 'C (english)':
        cfg.set_string("app/lc_messages", "C")

