# vim: set fileencoding=utf-8:
# GNU Solfege - free ear training software
# Copyright (C) 2000, 2001, 2002, 2003, 2004, 2007, 2008, 2011  Tom Cato Amundsen
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

import sys

from gi.repository import Gtk

from solfege import cfg
from solfege import gu
from solfege import lessonfilegui


class AbstractQuestionNameTable(Gtk.Table, cfg.ConfigUtils):
    """
    Base class for QuestionNameButtonTable and QuestionNameCheckButtonTable.
    """
    def __init__(self, exname):
        Gtk.Table.__init__(self)
        cfg.ConfigUtils.__init__(self, exname)
        self._ignore_watch = 0
        self.add_watch('ask_for_names', self.ask_for_names_changed)
    def ask_for_names_changed(self):
        pass
    def initialize(self, num, dir):
        self.m_num = num
        self.m_dir = dir
        self.m_x = 0
        self.m_y = 0
        for X in self.get_children():
            X.destroy()
        self.m_button_dict = {}
        self.m_name_list = []
    def conditional_newline(self):
        """
        Do newline if there are enough buttons on the line.
        """
        if self.m_dir == 'vertic':
            self.m_y = self.m_y + 1
            if self.m_y == self.m_num:
                self.m_y = 0
                self.m_x = self.m_x + 1
        else:
            self.m_x = self.m_x + 1
            if self.m_x == self.m_num:
                self.m_x = 0
                self.m_y = self.m_y + 1
    def newline(self):
        if self.m_dir == 'vertic':
            self.m_y = 0
            self.m_x = self.m_x + 1
        else:
            self.m_x = 0
            self.m_y = self.m_y + 1
    def grab_focus_first_button(self):
        v = self.get_children()
        v.reverse()
        for c in v:
            if c.get_property("sensitive"):
                c.grab_focus()
                return

class QuestionNameButtonTable(AbstractQuestionNameTable):
    def __init__(self, exname):
        AbstractQuestionNameTable.__init__(self, exname)
    def ask_for_names_changed(self, *v):
        """
        This method is called when the config variable 'ask_for_names' is
        changed. The watching of the method is set up in
        AbstractQuestionNameTable.__init__
        """
        if self._ignore_watch > 0:
            return
        for n, button in self.m_button_dict.items():
            button.set_sensitive(
                self.m_name_list.index(n) in self.get_list('ask_for_names'))
    def add(self, question, callback):
        """add a button and set up callback function.
        there should not be created more than one button with the same
        (c locale) name.
        return the button created.
        """
        if 'newline' in question and question.newline:
            self.newline()
        b = Gtk.Button()
        if question.name.cval in self.m_button_dict:
            print >> sys.stderr, "Warning: The lessonfile contain several questions with the same name:", question.name.cval
            print >> sys.stderr, "         This is a bug in the lesson file."
        self.m_button_dict[question.name.cval] = b
        self.m_name_list.append(question.name.cval)
        b.m_cname = question.name.cval
        b.set_sensitive(question.active)
        b.add(lessonfilegui.new_labelobject(question.name))
        b.show_all()
        self.attach(b, self.m_x, self.m_x+1, self.m_y, self.m_y+1)
        b.connect('clicked', callback)
        b.connect('button_release_event', callback)
        self.conditional_newline()
        return b

class QuestionNameCheckButtonTable(AbstractQuestionNameTable):
    def __init__(self, teacher):
        AbstractQuestionNameTable.__init__(self, teacher.m_exname)
        self.m_t = teacher
    def ask_for_names_changed(self, *v):
        self.m_t.m_P.m_random.reset()
        if not self.m_name_list:
            # If m_name_list is empty, it means that no lesson file is
            # yet loaded. Just return.
            return
        if self._ignore_watch > 0:
            return
        for question in self.m_t.m_P.m_questions:
            question.active = self.m_name_list.index(question.name.cval) in self.get_list('ask_for_names')
    def add(self, question):
        """add a button and set up callback function.
        there should not be created more than one button with the same
        (c locale) name.
        return the button created.
        """
        if 'newline' in question and question.newline:
            self.newline()
        b = Gtk.CheckButton()
        if question.name.cval in self.m_button_dict:
            print >> sys.stderr, "Warning: The lessonfile contain several questions with the same name:", question.name.cval
            print >> sys.stderr, "         Things will not work as normal after this."
        self.m_button_dict[question.name.cval] = b
        self.m_name_list.append(question.name.cval)
        b.set_active(question.active)
        b.connect('toggled', self.on_checkbutton_toggled)
        b.m_cname = question.name.cval
        b.add(lessonfilegui.new_labelobject(question.name))
        b.show_all()
        self.attach(b, self.m_x, self.m_x+1, self.m_y, self.m_y+1)
        self.conditional_newline()
        return b
    def on_checkbutton_toggled(self, button):
        """
        Set the content of the 'ask_for_names' config variable based on
        the active status of the check buttons.
        """
        v= []
        for i in range(len(self.m_name_list)):
            if self.m_button_dict[self.m_name_list[i]].get_active():
                v.append(i)
        self.set_list('ask_for_names', v)
    def select_all(self):
        for button in self.m_button_dict.values():
            button.set_active(True)

class RandomTransposeDialog(Gtk.Dialog):
    def __init__(self, initial_value, parent):
        Gtk.Dialog.__init__(self, _("Set transposition"), parent, 0,
           (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OK, Gtk.ResponseType.OK,
            ))
        dlg_vbox = gu.hig_dlg_vbox()
        self.vbox.pack_start(dlg_vbox, True, True, 0)
        xbox, vbox = gu.hig_category_vbox(_("Select how to do random transposition"))
        dlg_vbox.pack_start(xbox, True, True, 0)
        label = Gtk.Label(label=_("""You can read about the different types of transposition in the lesson file documentation available on the Help menu."""))
        spin_sg = Gtk.SizeGroup(Gtk.SizeGroupMode.HORIZONTAL)
        label.set_line_wrap(True)
        vbox.pack_start(label, True, True, 0)
        sizegroup = Gtk.SizeGroup(Gtk.SizeGroupMode.HORIZONTAL)
        self.m_buttons = {}
        self.m_spins = {}
        self.m_buttons['no'] = b1 = Gtk.RadioButton.new_with_label(None, _("No"))
        self.m_spins['no'] = []
        vbox.pack_start(b1, True, True, 0)
        self.m_buttons['yes'] = b2 = Gtk.RadioButton.new_with_label_from_widget(b1, _("Yes"))
        self.m_spins['yes'] = []
        hbox = gu.bHBox(vbox)
        label_b = Gtk.Label()
        label_b.set_alignment(0.4, 0.5)
        label_b.set_markup('<span size="xx-large">♭</span>')
        label_x = Gtk.Label()
        label_x.set_alignment(0.4, 0.5)
        label_x.set_markup('<span size="xx-large">♯</span>')
        spin_sg.add_widget(label_b)
        spin_sg.add_widget(label_x)
        hbox.pack_start(b2, True, True, 0)
        hbox.pack_start(label_b, True, True, 0)
        hbox.pack_start(label_x, True, True, 0)

        self.m_buttons['accidentals'] = Gtk.RadioButton.new_with_label_from_widget(
            b1, _("Fifths relative to C major/a minor"))
        hbox = gu.bHBox(vbox)
        hbox.pack_start(self.m_buttons['accidentals'], True, True, 0)
        self.m_spins['accidentals'] = [
            Gtk.SpinButton(adjustment=Gtk.Adjustment(0, -7, 7, 1, 1)),# 0.0, 0),
            Gtk.SpinButton(adjustment=Gtk.Adjustment(0, -7, 7, 1, 1))]#, 0.0, 0)]
        spin_sg.add_widget(self.m_spins['accidentals'][0])
        spin_sg.add_widget(self.m_spins['accidentals'][1])
        hbox.pack_start(self.m_spins['accidentals'][0], True, True, 0)
        hbox.pack_start(self.m_spins['accidentals'][1], True, True, 0)
        gu.SpinButtonRangeController(self.m_spins['accidentals'][0],
                                     self.m_spins['accidentals'][1],
                                     -7, 7)

        self.m_buttons['key'] = Gtk.RadioButton.new_with_label_from_widget(
            b1, _i("Fifths relative to current key"))
        hbox = gu.bHBox(vbox)
        hbox.pack_start(self.m_buttons['key'], True, True, 0)
        self.m_spins['key'] = [
            Gtk.SpinButton(adjustment=Gtk.Adjustment(0, -10, 10, 1, 1)),# 0.0, 0),
            Gtk.SpinButton(adjustment=Gtk.Adjustment(0, -10, 10, 1, 1))]#, 0.0, 0)]
        hbox.pack_start(self.m_spins['key'][0], True, True, 0)
        hbox.pack_start(self.m_spins['key'][1], True, True, 0)
        gu.SpinButtonRangeController(self.m_spins['key'][0],
                                     self.m_spins['key'][1],
                                     -10, 10)

        self.m_buttons['atonal'] = Gtk.RadioButton.new_with_label_from_widget(
            b1, _i("Transpose notes without changing key"))
        hbox = gu.bHBox(vbox)
        hbox.pack_start(self.m_buttons['atonal'], True, True, 0)
        self.m_spins['atonal'] = [
            Gtk.SpinButton(adjustment=Gtk.Adjustment(0, -10, 10, 1, 1)),# 0.0, 0),
            Gtk.SpinButton(adjustment=Gtk.Adjustment(0, -10, 10, 1, 1))]#, 0.0, 0)]
        hbox.pack_start(self.m_spins['atonal'][0], True, True, 0)
        hbox.pack_start(self.m_spins['atonal'][1], True, True, 0)
        gu.SpinButtonRangeController(self.m_spins['atonal'][0],
                                     self.m_spins['atonal'][1],
                                     -10, 10)

        self.m_buttons['semitones'] = Gtk.RadioButton.new_with_label_from_widget(
            b1, _("Semitones"))
        hbox = gu.bHBox(vbox)
        hbox.pack_start(self.m_buttons['semitones'], True, True, 0)
        self.m_spins['semitones'] = [
            Gtk.SpinButton(adjustment=Gtk.Adjustment(0, -100, 100, 1, 1)),#, 0.0, 0),
            Gtk.SpinButton(adjustment=Gtk.Adjustment(0, -100, 100, 1, 1))]#, 0.0, 0)]
        hbox.pack_start(self.m_spins['semitones'][0], True, True, 0)
        hbox.pack_start(self.m_spins['semitones'][1], True, True, 0)
        gu.SpinButtonRangeController(self.m_spins['semitones'][0],
                                     self.m_spins['semitones'][1],
                                     -100, 100)
        for n, w in self.m_buttons.items():
            sizegroup.add_widget(w)
            for ww in self.m_spins[n]:
                ww.set_sensitive(False)
            w.connect('clicked', self.on_spins_clicked, n)
        if initial_value[0] == False:
            k = 'no'
        elif initial_value[0] == True:
            k = 'yes'
        else:
            k = initial_value[0]
        self.m_buttons[k].set_active(True)
        if k in ('accidentals', 'key', 'semitones', 'atonal'):
            t, v1, v2 = initial_value
            # FIXME Because of the RangeController, we have to do this
            # twice to be sure both values are set properly.
            self.m_spins[t][1].set_value(v2)
            self.m_spins[t][0].set_value(v1)
            self.m_spins[t][1].set_value(v2)
            self.m_spins[t][0].set_value(v1)
        self.show_all()
    def on_spins_clicked(self, w, n):
        for w in self.m_spins[n]:
            w.set_sensitive(self.m_buttons[n].get_active())
    def get_value(self):
        for n, btn in self.m_buttons.items():
            if btn.get_active():
                s = n
        if s == 'yes':
            return (True, )
        elif s == 'no':
            return (False, )
        return [s, self.m_spins[s][0].get_value_as_int(), self.m_spins[s][1].get_value_as_int()]


