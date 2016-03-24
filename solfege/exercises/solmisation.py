# GNU Solfege - free ear training software
# Copyright (C) 2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2011,
# 2013  Tom Cato Amundsen
# Copyright (C) 2013 Jan Baumgart (Folkwang Universitaet der Kuenste)
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
from __future__ import division

from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Gdk

from solfege import abstract
from solfege import abstract_solmisation_addon
from solfege import gu
from solfege import lessonfile
from solfege import mpd

from solfege.const import solmisation_syllables, solmisation_notenames


class Teacher(abstract.Teacher, abstract_solmisation_addon.SolmisationAddOnClass):
    OK = 0
    ERR_PICKY = 1
    ERR_NO_ELEMS = 2
    def __init__(self, exname):
        abstract.Teacher.__init__(self, exname)
        self.lessonfileclass = lessonfile.HeaderLessonfile

    def play_question(self):
        if self.q_status == self.QSTATUS_NO:
            return
        self.play(self.get_music_string())

    def guess_answer(self, a):
        assert self.q_status in [self.QSTATUS_NEW, self.QSTATUS_WRONG]
        v = []
        for idx in range(len(self.m_question)):
            v.append(self.m_question[idx] == a[idx])
        if not [x for x in v if x == 0]:
            self.q_status = self.QSTATUS_SOLVED
            self.maybe_auto_new_question()
            return 1
        else:
            self.q_status = self.QSTATUS_WRONG


class RhythmViewer(Gtk.Frame):
    def __init__(self, parent):
        Gtk.Frame.__init__(self)
        self.set_shadow_type(Gtk.ShadowType.IN)
        self.g_parent = parent
        self.g_box = Gtk.HBox()
        self.g_box.show()
        self.g_box.set_spacing(gu.PAD_SMALL)
        self.g_box.set_border_width(gu.PAD)
        self.add(self.g_box)
        self.m_data = []
        # the number of rhythm elements the viewer is supposed to show
        self.m_num_notes = 0
        self.g_face = None
        self.__timeout = None
    def set_num_notes(self, i):
        self.m_num_notes = i
    def clear(self):
        for child in self.g_box.get_children():
            child.destroy()
        self.m_data = []
    def create_holders(self):
        """
        create those |__| that represents one beat
        """
        if self.__timeout:
            GObject.source_remove(self.__timeout)
        self.clear()
        for x in range(self.m_num_notes):
            self.g_box.pack_start(gu.create_png_image('holder'), False, False, 0)
        self.m_data = []
    def clear_wrong_part(self):
        """When the user have answered the question, this method is used
        to clear all but the first correct elements."""
        # this assert is always true because if there is no rhythm element,
        # then there is a rhythm holder ( |__| )
        assert self.m_num_notes == len(self.g_parent.m_t.m_question)
        self.g_face.destroy()
        self.g_face = None
        for n in range(self.m_num_notes):
            if self.m_data[n] != self.g_parent.m_t.m_question[n]:
                break
        for x in range(n, len(self.g_box.get_children())):
            self.g_box.get_children()[n].destroy()
        self.m_data = self.m_data[:n]
        for x in range(n, self.m_num_notes):
            self.g_box.pack_start(gu.create_png_image('holder'), False, False, 0)
    def add_rhythm_element(self, i):
        assert len(self.m_data) <= self.m_num_notes
        if len(self.g_box.get_children()) >= self.m_num_notes:
            self.g_box.get_children()[self.m_num_notes-1].destroy()
        vbox = Gtk.VBox()
        vbox.show()
#        im = gu.create_rhythm_image(const.RHYTHMS[i])
        im = self.g_parent.solbutton(i, False)
        vbox.pack_start(im, True, True, 0)
        vbox.pack_start(gu.create_png_image('rhythm-wrong'), False, False, 0)
        vbox.get_children()[-1].hide()
        self.g_box.pack_start(vbox, False, False, 0)
        self.g_box.reorder_child(vbox, len(self.m_data))
        self.m_data.append(i)
    def backspace(self):
        if len(self.m_data) > 0:
            if self.g_face:
                self.g_box.get_children()[-2].destroy()
                self.g_face.destroy()
                self.g_face = None
            self.g_box.get_children()[len(self.m_data)-1].destroy()
            self.g_box.pack_start(gu.create_png_image('holder'), False, False, 0)
            del self.m_data[-1]
    def mark_wrong(self, idx):
        """
        Mark the rhythm elements that was wrong by putting the content of
        graphics/rhythm-wrong.png (normally a red line) under the element.
        """
        self.g_box.get_children()[idx].get_children()[1].show()
    def len(self):
        "return the number of rhythm elements currently viewed"
        return len(self.m_data)
    def sad_face(self):
        l = gu.HarmonicProgressionLabel(_("Wrong"))
        l.show()
        self.g_box.pack_start(l, False, False, 0)
        self.g_face = Gtk.EventBox()
        self.g_face.connect('button_press_event', self.on_sadface_event)
        self.g_face.show()
        im = Gtk.Image()
        im.set_from_stock('solfege-sadface', Gtk.IconSize.LARGE_TOOLBAR)
        im.show()
        self.g_face.add(im)
        self.g_box.pack_start(self.g_face, False, False, 0)
    def happy_face(self):
        l = gu.HarmonicProgressionLabel(_("Correct"))
        l.show()
        self.g_box.pack_start(l, False, False, 0)
        self.g_face = Gtk.EventBox()
        self.g_face.connect('button_press_event', self.on_happyface_event)
        self.g_face.show()
        im = Gtk.Image()
        im.set_from_stock('solfege-happyface', Gtk.IconSize.LARGE_TOOLBAR)
        im.show()
        self.g_face.add(im)
        self.g_box.pack_start(self.g_face, False, False, 0)
    def on_happyface_event(self, obj, event):
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 1:
            self.g_parent.new_question()
    def on_sadface_event(self, obj, event):
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 1:
            self.clear_wrong_part()
    def flash(self, s):
        self.clear()
        l = Gtk.Label(label=s)
        l.set_name("Feedback")
        l.set_alignment(0.0, 0.5)
        l.show()
        self.g_box.pack_start(l, True, True, 0)
        self.g_box.set_size_request(
            max(l.size_request().width + gu.PAD * 2, self.g_box.size_request().width),
            max(l.size_request().height + gu.PAD * 2, self.g_box.size_request().height))
        self.__timeout = GObject.timeout_add(2000, self.unflash)
    def unflash(self, *v):
        self.__timeout = None
        self.clear()

class Gui(abstract.Gui, abstract_solmisation_addon.SolmisationAddOnGuiClass):
    lesson_heading = _("Solmisation Diktat")
    def __init__(self, teacher):
        abstract.Gui.__init__(self, teacher)
        self.m_key_bindings = {'backspace_ak': self.on_backspace}
        self.g_answer_box = Gtk.VBox()
        self.answer_buttons = []
        self.m_answer_buttons = {}

        #-------
        hbox = gu.bHBox(self.practise_box)
        b = Gtk.Button(_("Play"))
        b.show()
        b.connect('clicked', self.play_users_answer)
        hbox.pack_start(b, False, True, 0)
        self.practise_box.pack_start(Gtk.HBox(), False, False,
                                     padding=gu.PAD_SMALL)
        self.g_rhythm_viewer = RhythmViewer(self)
        self.g_rhythm_viewer.create_holders()
        hbox.pack_start(self.g_rhythm_viewer, True, True, 0)

        self.practise_box.pack_start(self.g_answer_box, False, False, 0)

        # action area
        self.std_buttons_add(
            ('new', self.new_question),
            ('repeat', self.repeat_question),
            #('play_answer', self.play_users_answer),
            ('give_up', self.give_up),
            ('backspace', self.on_backspace))

        self.practise_box.show_all()
        ##############
        # config_box #
        ##############
        self.add_select_elements_gui()
        #--------
        self.config_box.pack_start(Gtk.HBox(), False, False,
                                   padding=gu.PAD_SMALL)
        self.add_select_num_notes_gui()
        #-----
        self.config_box.pack_start(Gtk.HBox(), False, False,
                                   padding=gu.PAD_SMALL)
        #------
        hbox = gu.bHBox(self.config_box, False)
        hbox.set_spacing(gu.PAD_SMALL)
        hbox.pack_start(Gtk.Label(_("Beats per minute:")), False, False, 0)
        spin = gu.nSpinButton(self.m_exname, 'bpm',
                 Gtk.Adjustment(60, 20, 240, 1, 10))
        hbox.pack_start(spin, False, False, 0)
        hbox = gu.bHBox(self.config_box, False)
        hbox.set_spacing(gu.PAD_SMALL)
        hbox.pack_start(gu.nCheckButton(self.m_exname,
                                        "show_first_note",
                                        _("Show the first tone")), False, False, 0)
        hbox.pack_start(gu.nCheckButton(self.m_exname,
                                        "play_cadence",
                                        _("Play cadence")), False, False, 0)
        self._add_auto_new_question_gui(self.config_box)
        self.config_box.show_all()

    def solbutton(self, i, connect):
        if i > len(solmisation_syllables) or i < 0:
            btn = Gtk.Button()
        else:
            btn = Gtk.Button(solmisation_syllables[i])
        btn.show()
        if connect:
            btn.connect('clicked', self.guess_element, i)
        return btn

    def select_element_cb(self, button, element_num):
        super(Gui, self).select_element_cb(button, element_num)
        self.m_answer_buttons[element_num].set_sensitive(button.get_active())
        #self.update_answer_buttons()

    def on_backspace(self, widget=None):
        if self.m_t.q_status == self.QSTATUS_SOLVED:
            return
        self.g_rhythm_viewer.backspace()
        if not self.g_rhythm_viewer.m_data:
            self.g_backspace.set_sensitive(False)

    def play_users_answer(self, widget):
        if self.g_rhythm_viewer.m_data:
            melody = ""
            p = mpd.MusicalPitch()
            for k in self.g_rhythm_viewer.m_data:
                melody += " " + mpd.transpose_notename(solmisation_notenames[k], self.m_t.m_transp) + "4"

            self.m_t.play(r"\staff{ \time 1000000/4 %s }" % melody)

    def guess_element(self, sender, i):
        if self.m_t.q_status == self.QSTATUS_NO:
            self.g_rhythm_viewer.flash(_("Click 'New' to begin."))
            return
        if self.m_t.q_status == self.QSTATUS_SOLVED:
            return
        if self.g_rhythm_viewer.len() == len(self.m_t.m_question):
            self.g_rhythm_viewer.clear_wrong_part()
        self.g_backspace.set_sensitive(True)
        self.g_rhythm_viewer.add_rhythm_element(i)
        if self.g_rhythm_viewer.len() == len(self.m_t.m_question):
            if self.m_t.guess_answer(self.g_rhythm_viewer.m_data):
                self.g_rhythm_viewer.happy_face()
                self.std_buttons_answer_correct()
            else:
                v = []
                for idx in range(len(self.m_t.m_question)):
                    v.append(self.m_t.m_question[idx] == self.g_rhythm_viewer.m_data[idx])
                for x in range(len(v)):
                    if not v[x]:
                        self.g_rhythm_viewer.mark_wrong(x)
                self.g_rhythm_viewer.sad_face()
                self.std_buttons_answer_wrong()

    def new_question(self, widget=None):
        g = self.m_t.new_question()
        if g == self.m_t.OK:
            self.g_first_rhythm_button.grab_focus()
            self.g_rhythm_viewer.set_num_notes(self.get_int('num_notes'))
            self.g_rhythm_viewer.create_holders()
            self.std_buttons_new_question()
            if self.m_t.get_bool('show_first_note'):
                self.g_rhythm_viewer.add_rhythm_element(self.m_t.m_question[0])
            try:
                self.m_t.play_question()
            except Exception, e:
                if not self.standard_exception_handler(e, self.on_end_practise):
                    raise
                return
        elif g == self.m_t.ERR_PICKY:
            self.g_rhythm_viewer.flash(_("You have to solve this question first."))
        else:
            assert g == self.m_t.ERR_NO_ELEMS
            self.g_repeat.set_sensitive(False)
            self.g_rhythm_viewer.flash(_("You have to configure this exercise properly"))

    def repeat_question(self, *w):
        self.m_t.play_question()
        self.g_first_rhythm_button.grab_focus()

    def update_answer_buttons(self):
        """
        (Re)create the buttons needed to answer the questions.
        We recreate the buttons for each lesson file because the
        header may specify a different set of rhythm elements to use.
        """
        for but in self.answer_buttons:
            but.destroy()
        self.answer_buttons = []
        self.g_first_rhythm_button = None

        gs = Gtk.SizeGroup(Gtk.SizeGroupMode.HORIZONTAL)

        for i, v in enumerate((
                    [1, 4, -1, 8, 11, -1, 15, 18, 21, -1, 25, 28, -1, 32],
                    [0, 3, 6, 7, 10, 13, 14, 17, 20, 23, 24, 27, 30, 31, 34],
                    [2, 5, -1, 9, 12, -1, 16, 19, 22, -1, 26, 29, -1, 33])):
            hbox = Gtk.HBox(True, 0)
            for k in v:
                b = self.solbutton(k, True)
                gs.add_widget(b)
                b.set_sensitive(False)
                for n in self.m_t.m_P.header.solmisation_elements:
                    if k == n:
                        b.set_sensitive(True)
                        if not self.g_first_rhythm_button:
                            self.g_first_rhythm_button = b
                hbox.pack_start(b, True, True, 0)
                self.answer_buttons.append(b)
                if k != -1:
                    self.m_answer_buttons[k] = b
            spacing = Gtk.Alignment()
            if i in (0, 2):
                spacing.set_property('left-padding', 16)
                spacing.set_property('right-padding', 16)
            spacing.add(hbox)
            self.g_answer_box.pack_start(spacing, True, True, 0)
            spacing.show_all()

    def on_start_practise(self):
        # FIXME for now, we run in custom_mode all the time, so we don't
        # have to add lots of lesson files. We can change this later.
        #self.m_t.m_custom_mode = self.get_bool('gui/expert_mode')
        self.m_t.m_custom_mode = True
        super(Gui, self).on_start_practise()
        if not self.m_t.m_P.header.solmisation_elements:
            self.m_t.m_P.header.solmisation_elements = self.m_t.elements[:]
        self.update_answer_buttons()
        self.std_buttons_start_practise()
        if self.m_t.m_custom_mode:
            self.update_select_elements_buttons()
            self.g_element_frame.show()
        else:
            self.g_element_frame.hide()
        self.m_t.set_default_header_values()
        if 'show_first_note' in self.m_t.m_P.header:
            self.m_t.set_bool('show_first_note', self.m_t.m_P.header.show_first_note)
        if 'play_cadence' in self.m_t.m_P.header:
            self.m_t.set_bool('play_cadence', self.m_t.m_P.header.play_cadence)
        self.g_rhythm_viewer.flash(_("Click 'New' to begin."))

    def on_end_practise(self):
        self.m_t.end_practise()
        self.std_buttons_end_practise()
        self.g_rhythm_viewer.create_holders()

    def give_up(self, widget=None):
        if self.m_t.q_status == self.QSTATUS_NO:
            return
        self.g_rhythm_viewer.clear()
        for i in self.m_t.m_question:
            self.g_rhythm_viewer.add_rhythm_element(i)
        self.m_t.q_status = self.QSTATUS_SOLVED
        self.std_buttons_give_up()

