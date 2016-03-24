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

from __future__ import absolute_import
import textwrap

from gi.repository import Gtk

from solfege import abstract
from solfege import gu
from solfege.exercises import idbyname
from solfege import mpd
from solfege import soundcard
from solfege import statisticsviewer

class Teacher(idbyname.Teacher):
    def __init__(self, exname):
        idbyname.Teacher.__init__(self, exname)
    def play_question(self):
        if self.q_status == self.QSTATUS_NO:
            return
        self.m_P.play_question()


class Gui(abstract.LessonbasedGui):
    def __init__(self, teacher):
        abstract.LessonbasedGui.__init__(self, teacher)
        ################
        # practise_box #
        ################
        # This module was marked as deprecated in solfege 3.15.
        # Let us remove it in 3.18
        self.add_module_is_deprecated_label()
        self.g_music_displayer = mpd.MusicDisplayer()
        self.practise_box.pack_start(self.g_music_displayer, True, True, 0)

        self.g_flashbar = gu.FlashBar()
        self.g_flashbar.show()
        self.practise_box.pack_start(self.g_flashbar, False)
        self.practise_box.set_spacing(gu.PAD)

        self.g_entry = Gtk.Entry()
        self.g_entry.set_activates_default(True)
        self.g_entry.connect('changed', self.on_entry_changed)
        self.practise_box.pack_start(self.g_entry, False)
        self.std_buttons_add(
            ('new', self.new_question),
            ('repeat', lambda _o, self=self: self.m_t.play_question()),
            ('play_tonic', lambda w: self.run_exception_handled(self.m_t.play_tonic)),
            ('show', self.show_answer),
            ('give_up', self.give_up),
            ('guess_answer', self.guess_answer)
        )
        self.g_guess_answer.set_can_default(True)
        self.practise_box.show_all()
        ##############
        # config_box #
        ##############
        self.add_random_transpose_gui()
        self._add_auto_new_question_gui(self.config_box)
        # ----------------------------------------------

        ###############
        # statistics
        ###############
        self.setup_statisticsviewer(statisticsviewer.StatisticsViewer,
                                   _("Harmonic progression dictation"))

    def on_entry_changed(self, w):
        self.g_guess_answer.set_sensitive(bool(self.g_entry.get_text()))
    def guess_answer(self, widget=None):
        if self.m_t.q_status == self.QSTATUS_NO:
            return
        if self.m_t.q_status == self.QSTATUS_SOLVED:
            if self.m_t.guess_answer(self.g_entry.get_text()):
                self.g_flashbar.flash(_("Correct, but you have already solved this question"))
            else:
                self.g_flashbar.flash(_("Wrong, but you have already solved this question"))
        else:
            if self.m_t.guess_answer(self.g_entry.get_text()):
                self.g_flashbar.flash(_("Correct"))
                self.std_buttons_answer_correct()
            else:
                self.g_flashbar.flash(_("Wrong"))
                self.std_buttons_answer_wrong()
    def show_answer(self, widget=None):#FIXME rename to show_music??
        if self.m_t.q_status != self.QSTATUS_NO:
            self.g_music_displayer.display(self.m_t.m_P.get_music(),
                               self.get_int('config/feta_font_size=20'))
    def new_question(self, widget=None):
        def exception_cleanup():
            soundcard.synth.stop()
            self.std_buttons_exception_cleanup()
            self.g_entry.set_text("")
            self.g_music_displayer.clear(2)
        # pop just in case there is something in the stack.
        self.g_flashbar.pop()
        try:
            g = self.m_t.new_question()
            if g == self.m_t.OK:
                self.m_t.play_question()
                self.g_music_displayer.display(self.m_t.m_P.get_music(),
                     self.get_int('config/feta_font_size=20'), mpd.Rat(0, 1))
                self.std_buttons_new_question()
                self.g_entry.set_text("")
                self.g_entry.grab_focus()
        except Exception, e:
            if not self.standard_exception_handler(e, exception_cleanup):
                raise
    def give_up(self, widget=None):
        self.m_t.give_up()
        self.std_buttons_give_up()
        self.g_guess_answer.set_sensitive(False)
        self.g_flashbar.push(self.m_t.m_P.get_cname())
        self.show_answer()
    def on_start_practise(self):
        self.m_t.m_custom_mode = self.get_bool('gui/expert_mode')
        self.m_t.m_statistics.reset_session()
        self.set_deprecation_text('harmonicprogressiondictation',
            'elembuilder', self.m_t.m_P.m_filename)
        self.g_music_displayer.clear(2)
        self.g_random_transpose.set_text(str(self.m_t.m_P.header.random_transpose))
        self.g_guess_answer.set_sensitive(False)
        self.std_buttons_start_practise()
        self.set_lesson_heading(self.m_t.m_P.header.lesson_heading)
        self.g_guess_answer.grab_default()
    def on_end_practise(self):
        self.std_buttons_end_practise()
        self.g_guess_answer.set_sensitive(False)
        self.g_music_displayer.clear(2)
        self.m_t.end_practise()

