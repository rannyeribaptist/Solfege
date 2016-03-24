# GNU Solfege - free ear training software
# Copyright (C) 2004, 2005, 2007, 2008, 2011  Tom Cato Amundsen
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

from solfege import abstract
from solfege import gu
from solfege import lessonfile
from solfege import mpd
from solfege import soundcard

class Teacher(abstract.Teacher):
    OK = 1
    ERR_NO_QUESTION = 2
    def __init__(self, exname):
        abstract.Teacher.__init__(self, exname)
        self.lessonfileclass = lessonfile.SingAnswerLessonfile
        for s in 'accidentals', 'key', 'semitones', 'atonal':
            self.m_lessonfile_defs[s] = s
    def new_question(self):
        assert self.m_P
        self.m_P.select_random_question()
        self.q_status = self.QSTATUS_NEW
        return self.OK

class Gui(abstract.LessonbasedGui):
    def __init__(self, teacher):
        abstract.Gui.__init__(self, teacher)
        self.g_music_displayer = mpd.MusicDisplayer()
        self.practise_box.pack_start(self.g_music_displayer, True, True, 0)
        self.g_flashbar = gu.FlashBar()
        self.practise_box.pack_start(self.g_flashbar, False, False, 0)
        self.g_music_displayer.clear()
        self.g_new = gu.bButton(self.action_area, _("_New"), self.new_question)
        self.g_repeat = gu.bButton(self.action_area, _("_Repeat"),
            lambda w: self.run_exception_handled(self.m_t.m_P.play_question))
        self.g_repeat_arpeggio = gu.bButton(self.action_area,
            _("Repeat _arpeggio"),
            lambda w: self.run_exception_handled(self.m_t.m_P.play_question_arpeggio))
        self.g_play_answer = gu.bButton(self.action_area,
                    _("_Play answer"), self.hear_answer)
        ##############
        # config_box #
        ##############
        self.add_random_transpose_gui()
        self.practise_box.show_all()
    def new_question(self, widget):
        def exception_cleanup():
            soundcard.synth.stop()
            self.g_music_displayer.clear()
            self.g_repeat.set_sensitive(False)
            self.g_repeat_arpeggio.set_sensitive(False)
            self.g_play_answer.set_sensitive(False)
        if self.m_t.m_P.header.have_music_displayer:
            self.g_music_displayer.clear()
        try:
            g = self.m_t.new_question()
            self.g_flashbar.push(self.m_t.m_P.get_question().question_text)
            if isinstance(self.m_t.m_P.get_question().music, lessonfile.MpdDisplayable):
                self.g_music_displayer.display(self.m_t.m_P.get_music(), 20)
            else:
                self.g_music_displayer.clear()
            self.m_t.m_P.play_question()
            self.g_repeat.set_sensitive(True)
            self.g_repeat_arpeggio.set_sensitive(True)
            self.g_play_answer.set_sensitive(True)
            self.g_play_answer.grab_focus()
        except Exception, e:
            if isinstance(e, mpd.MpdException):
                self.m_t.m_P.get_question()['music'].complete_to_musicdata_coords(self.m_t.m_P, e)
                e.m_mpd_varname = 'music'
                e.m_mpd_badcode = self.m_t.m_P.get_question().music.get_err_context(e, self.m_t.m_P)
            if not self.standard_exception_handler(e, exception_cleanup):
                raise
    def hear_answer(self, widget):
        try:
            self.m_t.m_P.play_question(varname='answer')
        except Exception, e:
            if not self.standard_exception_handler(e):
                raise
        self.g_new.grab_focus()
    def update_gui_after_lessonfile_change(self):
        self.g_random_transpose.set_text(str(self.m_t.m_P.header.random_transpose))
        if self.m_t.m_P.header.have_repeat_arpeggio_button:
            self.g_repeat_arpeggio.show()
        else:
            self.g_repeat_arpeggio.hide()
        if self.m_t.m_P.header.have_music_displayer:
            self.g_music_displayer.show()
        else:
            self.g_music_displayer.hide()
        self.g_repeat.set_sensitive(False)
        self.g_repeat_arpeggio.set_sensitive(False)
        self.g_play_answer.set_sensitive(False)
        self.g_flashbar.clear()
        self.g_new.set_sensitive(bool(self.m_t.m_P))
    def on_start_practise(self):
        super(Gui, self).on_start_practise()
        self.update_gui_after_lessonfile_change()
        self.g_new.grab_focus()
        self.g_flashbar.delayed_flash(self.short_delay,
            _("Click 'New' to begin."))
        self.g_flashbar.require_size(
            [q['question_text'] for q in self.m_t.m_P.m_questions]
            + [_("Click 'New' to begin.")])
