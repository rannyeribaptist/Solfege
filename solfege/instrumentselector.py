# GNU Solfege - free ear training software
# Copyright (C) 2000, 2001, 2002, 2003, 2004, 2006, 2007, 2008, 2011  Tom Cato Amundsen
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

from gi.repository import Gtk

from solfege import cfg
from solfege import gu
from solfege import mpd
from solfege import soundcard

MAX_VOLUME = 127.0
class MidiInstrumentMenu(Gtk.Menu):
    def __init__(self, callback):
        Gtk.Menu.__init__(self)
        self.m_callback = callback
        for x in range(len(soundcard.instrument_names)):
            if x % 8 == 0:
                menuitem = Gtk.MenuItem(soundcard.instrument_sections[x/8])
                submenu = Gtk.Menu()
                self.append(menuitem)
                menuitem.set_submenu(submenu)
                menuitem.show()
            item = Gtk.MenuItem(soundcard.instrument_names[x])
            item.connect('activate', self.on_activate, x)
            submenu.append(item)
            item.show()
        self.show()
    def on_activate(self, menuitem, instrument):
        self.m_callback(instrument)


class nInstrumentSelector(Gtk.VBox, cfg.ConfigUtils):
    def __init__(self, exname, name, sizegroup):
        Gtk.VBox.__init__(self)
        cfg.ConfigUtils.__dict__['__init__'](self, exname)
        self.m_name = name
        hbox = gu.bHBox(self)
        hbox.set_spacing(gu.PAD_SMALL)

        self.g_button = Gtk.Button(
              soundcard.instrument_names[self.get_int(self.m_name)])
        self.g_button.connect('clicked', self.on_btnclick)
        hbox.pack_start(self.g_button, True, True, 0)
        g = Gtk.VolumeButton()
        g.props.value = self.get_int('%s_volume' % name) / MAX_VOLUME
        def ff(volumebutton, value):
            self.set_int('%s_volume' % name, int(value * MAX_VOLUME))
        g.connect('value-changed', ff)
        hbox.pack_start(g, False, False, 0)

        self.g_menu = MidiInstrumentMenu(self.on_instrument_selected)
        self.m_instrument = self.get_int('preferred_instrument')

        hbox = Gtk.HBox()
        hbox.set_spacing(6)
        self.pack_start(hbox, True, True, 0)

    def on_btnclick(self, *argv):
        self.g_menu.popup(None, None, None, None, 1, 0)
    def on_instrument_selected(self, instrument=None):
        self.set_int(self.m_name, instrument)
        self.g_button.get_children()[0].set_text(soundcard.instrument_names[instrument])
        self.m_instrument = instrument
        self.play_selected_instrument()
    def play_selected_instrument(self, _o=None):
        t = mpd.Track()
        t.set_patch(self.m_instrument)
        t.set_volume(self.get_int('%s_volume' % self.m_name))
        t.note(4, 60)
        soundcard.synth.play_track(t)
    def show(self):
        self.show_all()

def FramedInstrumentSelector(title, exname, varname, sizegroup):
    box = Gtk.HBox()
    box.set_spacing(6)
    label = Gtk.Label(label=title)
    label.set_alignment(0.0, 0.5)
    box.pack_start(label, False, False, 0)
    n = nInstrumentSelector(exname, varname, None)
    sizegroup.add_widget(label)
    n.show()
    box.pack_start(n, True, True, 0)
    return box


class InstrumentConfigurator(Gtk.VBox, cfg.ConfigUtils):
    def __init__(self, exname, num, labeltext):
        Gtk.VBox.__init__(self)
        #cfg.ConfigUtils.__init__(self, exname)
        cfg.ConfigUtils.__dict__['__init__'](self, exname)
        assert num in (2, 3)
        self.m_num = num
        self.g_override_default_instrument_checkbutton \
            = gu.nCheckButton(exname, 'override_default_instrument',
                labeltext,
                 callback=self.update_instrument_override)
        self.pack_start(self.g_override_default_instrument_checkbutton,
                        False, False, 0)
        hbox = gu.bVBox(self)
        hbox.set_spacing(gu.PAD_SMALL)

        sizegroup = Gtk.SizeGroup(Gtk.SizeGroupMode.HORIZONTAL)
        self.g_instrsel_high = FramedInstrumentSelector(_("Highest:"), exname, 'highest_instrument',sizegroup)
        hbox.pack_start(self.g_instrsel_high, False, False, 0)
        if num == 3:
            self.g_instrsel_middle = FramedInstrumentSelector(_("Middle:"),
                                            exname, 'middle_instrument', sizegroup)
            hbox.pack_start(self.g_instrsel_middle, False, False, 0)
        else:
            self.g_instrsel_middle = None
        self.g_instrsel_low = FramedInstrumentSelector(_("Lowest:"),
                                                exname, 'lowest_instrument', sizegroup)
        hbox.pack_start(self.g_instrsel_low, False, False, 0)
        self.update_instrument_override()
    def update(self):
        self.update_instrument_override()
        self.g_instrsel_high.update()
        if self.m_num == 3:
            self.g_instrsel_middle.update()
        self.g_instrsel_low.update()
    def update_instrument_override(self, _o=None):
        self.g_override_default_instrument_checkbutton.set_active(
                self.get_bool('override_default_instrument'))
        self.g_instrsel_high.set_sensitive(
               self.g_override_default_instrument_checkbutton.get_active())
        self.g_instrsel_low.set_sensitive(
               self.g_override_default_instrument_checkbutton.get_active())
        if self.g_instrsel_middle:
            self.g_instrsel_middle.set_sensitive(
               self.g_override_default_instrument_checkbutton.get_active())
    def show(self):
        self.show_all()

