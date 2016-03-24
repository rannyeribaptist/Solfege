# GNU Solfege - free ear training software
# Copyright (C) 2004, 2005, 2007, 2008, 2011 Tom Cato Amundsen
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

import os
import sys

from gi.repository import Gtk
from gi.repository import GdkPixbuf

class BaseIconFactory(Gtk.IconFactory):
    def __init__(self, widget, datadir):
        Gtk.IconFactory.__init__(self)
        self.datadir = datadir
        self.add_default()

    def add_icons(self, icons):
        for stock_id, filename in icons.items():
            if os.path.isfile(os.path.join(self.datadir, filename)):
                iconset = Gtk.IconSet(GdkPixbuf.Pixbuf.new_from_file(os.path.join(self.datadir, filename)))
                self.add(stock_id, iconset)
            else:
                print >> sys.stderr, "File not found: %s" % filename

class EditorIconFactory(BaseIconFactory):
    """
    This class is used by lessonfile_editor.py
    """
    def __init__(self, widget, datadir):
        BaseIconFactory.__init__(self, widget, datadir)
        icons = {'solfege-icon': "graphics/solfege.svg",
            'solfege-sharp': "graphics/sharp.png",
            'solfege-double-sharp': "graphics/double-sharp.png",
            'solfege-flat': "graphics/flat.png",
            'solfege-double-flat': "graphics/double-flat.png",
            'solfege-natural': "graphics/natural.png",
            'solfege-erase': "graphics/erase.png",
            'solfege-notehead': "graphics/notehead.png"}
        self.add_icons(icons)


class SolfegeIconFactory(BaseIconFactory):
    def __init__(self, widget, datadir):
        BaseIconFactory.__init__(self, widget, datadir)
        icon_list = ['happyface', 'sadface',
            'rhythm-c12c12c12', 'rhythm-c12c12r12', 'rhythm-c12r12c12',
            'rhythm-c16c16c16c16', 'rhythm-c16c16c8', 'rhythm-c16c8c16',
            'rhythm-c16c8.', 'rhythm-c4', 'rhythm-c8c16c16', 'rhythm-c8.c16',
            'rhythm-c8c8', 'rhythm-r12c12c12', 'rhythm-r12c12r12',
            'rhythm-r12r12c12', 'rhythm-r16c16c16c16', 'rhythm-r16c16c8',
            'rhythm-r16c8c16', 'rhythm-r16c8.', 'rhythm-r4',
            'rhythm-r8c16c16', 'rhythm-r8c8', 'rhythm-r8r16c16',
            'rhythm-wrong']
        d = {}
        d['solfege-icon'] = 'graphics/solfege.svg'
        for iname in icon_list:
            d['solfege-%s' % iname] = os.path.join(u"graphics", iname) + ".png"
        self.add_icons(d)

