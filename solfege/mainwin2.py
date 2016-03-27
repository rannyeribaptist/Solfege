# vim: set fileencoding=utf-8 :
# GNU Solfege - free ear training software
# Copyright (C) 2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2011  Tom Cato Amundsen
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
#
import sys
import traceback
import locale
import os
import urllib
import shutil

from solfege import winlang
from solfege import buildinfo
from solfege.esel import FrontPage, TestsView, SearchView

from gi.repository import Gtk
from gi.repository import Gdk

class SplashWin(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, Gtk.WindowType.POPUP)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_resizable(True)
        frame = Gtk.Frame()
        frame.set_shadow_type(Gtk.ShadowType.OUT)
        self.add(frame)

        image = Gtk.Image()
        image.set_from_file('/home/Rannyeri/Imagens/logo1.png')
        image.set_size_request(10,10)
        image.show()

        imagem = Gtk.Button()
        imagem.add(image)
        imagem.show()
        imagem.set_size_request(10,10)
        frame.add(imagem)

        vbox = Gtk.VBox()
        vbox.set_border_width(20)
        frame.add(vbox)
        l = Gtk.Label(label=_("Starting GNU Solfege %s") % buildinfo.VERSION_STRING)
        l.set_name("Heading1")
        vbox.pack_start(l, True, True, 0)
        l = Gtk.Label(label="http://www.solfege.org")
        vbox.pack_start(l, True, True, 0)
        self.g_infolabel = Gtk.Label(label='')
        vbox.pack_start(self.g_infolabel, True, True, 0)
        self.show_all()
    def show_progress(self, txt):
        self.g_infolabel.set_text(txt)
        i = 0
        for i in range(6):
            Gtk.main_iteration()
