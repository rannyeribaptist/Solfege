# GNU Solfege - free ear training software
# Copyright (C) 2006, 2007, 2008, 2011  Tom Cato Amundsen
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

from solfege import abstract
from solfege import gu
from solfege import lessonfile
from solfege import lessonfilegui
from solfege import mpd
from solfege import statistics
from solfege import statisticsviewer

import solfege

class Teacher(abstract.Teacher):
    OK = 0
    ERR_NO_QUESTION = 2
    def __init__(self, exname):
        abstract.Teacher.__init__(self, exname)
        self.lessonfileclass = lessonfile.ElembuilderLessonfile
        self.m_statistics = statistics.LessonStatistics(self)
        # statistics viewer need this set because the statistics keys used
        # by this exercise module is a string of element names separated
        # by "-".
        self.m_statistics.m_key_is_list = True
        for s in 'auto', 'show', 'play':
            self.m_lessonfile_defs[s] = s
    def new_question(self):
        self.m_P.select_random_question()
        self.q_status = self.QSTATUS_NEW
        return self.OK
    def guess_answer(self, answer):
        """
        elembuilder statistics will use a list of the names of the answered
        elements when saving statistics.
        """
        fasit = [q['name'] for q in self.m_P.get_question()['elements']]
        if [e['name'] for e in self.m_P.get_question().elements] == answer:
            if self.q_status == self.QSTATUS_NEW \
                    and not self.m_custom_mode:
                self.m_statistics.add_correct(fasit)
            self.q_status = self.QSTATUS_SOLVED
            return True
        else:
            if self.q_status == self.QSTATUS_NEW:
                if not self.m_custom_mode:
                    self.m_statistics.add_wrong(fasit, answer)
                self.q_status = self.QSTATUS_WRONG
            return False
    def give_up(self):
        self.q_status = self.QSTATUS_GIVE_UP

class MultiButton(Gtk.Button):
    def __init__(self, label):
        Gtk.Button.__init__(self)
        l = lessonfilegui.new_labelobject(label)
        self.add(l)
        self.m_marked_wrong = False
    def mark_wrong(self):
        if self.m_marked_wrong:
            return
        self.m_marked_wrong = True
        vbox = Gtk.VBox()
        assert len(self.get_children()) == 1
        self.get_children()[0].reparent(vbox)
        self.add(vbox)
        label = Gtk.Label()
        label.set_markup("<span size='small'>%s</span>" % gu.escape(_("Wrong")))
        label.show()
        vbox.pack_start(label, True, True, 0)
        vbox.show()

class Gui(abstract.LessonbasedGui):
    def __init__(self, teacher):
        abstract.LessonbasedGui.__init__(self, teacher)
        self.m_key_bindings = {'backspace_ak': self.on_backspace}
        self.g_music_displayer = mpd.MusicDisplayer()
        self.practise_box.pack_start(self.g_music_displayer, False, False, 0)

        self.g_answer_button_box = gu.NewLineBox()
        self.practise_box.pack_start(self.g_answer_button_box, False, False, 0)
        # The user fill the answer in this box
        self.g_answer_frame = Gtk.Frame()
        self.g_answer_frame.set_shadow_type(Gtk.ShadowType.IN)
        self.practise_box.pack_start(self.g_answer_frame, False, False, 0)
        self.g_answer = Gtk.HBox()
        self.g_answer_frame.add(self.g_answer)
        self.g_answer_frame.show_all()
        # Flashbar
        self.g_flashbar = gu.FlashBar()
        self.g_flashbar.show()
        self.practise_box.pack_start(self.g_flashbar, False, False, 0)
        # action area
        self.std_buttons_add(
            ('new', self.new_question),
            ('play_music', lambda w: self.run_exception_handled(self.m_t.m_P.play_question)),
            ('display_music', self.show_answer),
            ('repeat', self.repeat_question),
            ('guess_answer', self.guess_answer),
            ('play_tonic', lambda w: self.run_exception_handled(self.m_t.play_tonic)),
            ('give_up', self.give_up),
            ('backspace', self.on_backspace),
        )
        ##############
        # statistics #
        ##############
        self.setup_statisticsviewer(statisticsviewer.StatisticsViewer, "")
    def new_question(self, widget):
        self.g_answer_button_box.set_sensitive(True)
        for w in self.g_answer.get_children():
                w.destroy()
        self.m_users_answer = []
        self.m_t.new_question()
        #if 'show' in self.m_t.m_P.header.at_question_start \
        #    and 'play' in self.m_t.m_P.header.at_question_start:
        if self.m_t.m_P.header.have_music_displayer:
            self.g_music_displayer.clear(self.m_t.m_P.header.music_displayer_stafflines)
        try:
            self.do_at_question_start_show_play()
        except Exception, e:
            # Setup buttons when we have an exception. We have to do this
            # before we call standard_exception_handler because we wan't
            # the buttons in this state, even if standard_exception_handler
            # can not handle it.
            self.std_buttons_exception_cleanup()
            if not self.standard_exception_handler(e):
                raise
        else:
            self.std_buttons_new_question()
    def repeat_question(self, widget):
        self.m_t.m_P.play_question()
    def guess_answer(self, widget):
        if self.m_t.q_status == self.QSTATUS_NO:
            if solfege.app.m_test_mode:
                self.g_flashbar.flash(_("Click 'Start test' to begin."))
            else:
                self.g_flashbar.flash(_("Click 'New' to begin."))
            return
        elif self.m_t.q_status in (self.QSTATUS_NEW, self.QSTATUS_WRONG):
            if self.m_t.guess_answer(self.m_users_answer):
                self.g_flashbar.flash(_("Correct"))
                self.std_buttons_answer_correct()
                if self.m_t.m_P.header.have_music_displayer:
                    self.run_exception_handled(self.show_answer)
                self.g_answer_button_box.set_sensitive(True)
            else:
                self.std_buttons_answer_wrong()
                self.g_flashbar.flash(_("Wrong"))
                max_button_height = 0
                for idx, a in enumerate(self.m_users_answer):
                    if idx + 1 > len(self.m_t.m_P.get_question().elements):
                        break
                    if idx + 1 > len(self.m_users_answer):
                        break
                    if self.m_users_answer[idx] != self.m_t.m_P.get_question().elements[idx]['name']:
                        self.g_answer.get_children()[idx].mark_wrong()
                if len(self.m_users_answer) > len(self.m_t.m_P.get_question().elements):
                    for btn in self.g_answer.get_children()[len(self.m_t.m_P.get_question().elements):]:
                        btn.mark_wrong()

                # We only recalculate the height of the answer frame
                # if there are any buttons in it. This to avoid the frame
                # disappearing.
                if self.g_answer.get_children():
                    for btn in self.g_answer.get_children():
                        max_button_height = max(max_button_height, btn.size_request().height)
                    self.g_answer_frame.set_size_request(-1, max_button_height)
    def on_backspace(self, widget=None):
        if self.m_t.q_status in (self.m_t.QSTATUS_SOLVED,
                                 self.m_t.QSTATUS_GIVE_UP):
            return
        if self.m_users_answer:
            del self.m_users_answer[-1]
            self.g_answer.get_children()[-1].destroy()
        if not self.m_users_answer:
            self.g_guess_answer.set_sensitive(False)
            self.g_backspace.set_sensitive(False)
    def add_element(self, widget, element):
        """
        Called when the user clicks a button to add another element.
        Calling this methods several times builds then answer the user
        will give.
        """
        self.m_users_answer.append(element['name'])
        b = MultiButton(element['label'])
        b.show()
        self.g_answer.pack_start(b, False, False, 0)
        self.g_backspace.set_sensitive(True)
        self.g_guess_answer.set_sensitive(True)
    def give_up(self, widget):
        for w in self.g_answer.get_children():
            w.destroy()
        self.m_t.give_up()
        self.std_buttons_give_up()
        for elem in self.m_t.m_P.get_question().elements:
            b = MultiButton(elem['label'])
            b.show()
            self.g_answer.pack_start(b, False, False, 0)
        if self.m_t.m_P.header.have_music_displayer:
            self.run_exception_handled(self.show_answer)
        self.g_answer_button_box.set_sensitive(False)
    def on_start_practise(self):
        self.m_t.m_custom_mode = False # FIXME
        super(Gui, self).on_start_practise()
        if self.m_t.m_P.header.elements == 'auto':
            v = []
            for question in self.m_t.m_P.m_questions:
                for elem in question['elements']:
                    if elem not in v:
                        v.append(elem)
            def xcmp(a, b):
                try:
                    try:
                        return cmp(a['sort'], b['sort'])
                    except KeyError:
                        return cmp(a['name'], b['name'])
                except ValueError:
                    return cmp(a, b)
            v.sort(xcmp)
            self.m_t.m_P.header.elements = v
        self.g_answer_button_box.empty()
        for c in self.g_answer.get_children():
            c.destroy()
        #
        if self.m_t.m_P.header.have_music_displayer:
            self.g_music_displayer.show()
            self.g_music_displayer.clear(self.m_t.m_P.header.music_displayer_stafflines)
        else:
            self.g_music_displayer.hide()
        #
        if not self.m_t.m_custom_mode:
            self.m_t.m_statistics.reset_session()
        self.g_statview.g_heading.set_text(self.m_t.m_P.header.title)
        self.m_elem_button_max_height = 0
        for elem in self.m_t.m_P.header.elements:
            b = MultiButton(elem['label'])
            b.connect('clicked', self.add_element, elem)
            b.show()
            self.g_answer_button_box.add_widget(b)
        self.g_answer_button_box.show_widgets()
        self.g_answer.set_size_request(-1, self.g_answer_button_box.get_max_child_height())
        self.set_lesson_heading(self.m_t.m_P.header.lesson_heading)
        self.m_users_answer = []
        self.std_buttons_start_practise()
        self.show_hide_at_question_start_buttons()
        self.g_flashbar.flash(_("Click 'New' to begin."))
        self.g_answer_button_box.set_sensitive(False)
    def on_end_practise(self):
        self.m_t.end_practise()
        self.std_buttons_end_practise()
