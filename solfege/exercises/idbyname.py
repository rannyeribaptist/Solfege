# GNU Solfege - free ear training software
# Copyright (C) 2000, 2001, 2002, 2003, 2004, 2005, 2007, 2008, 2011 Tom Cato Amundsen
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

from gi.repository import GObject

from solfege import abstract
from solfege import gu
from solfege import lessonfile
from solfege import mpd
from solfege import soundcard
from solfege import statistics
from solfege import statisticsviewer
from solfege.specialwidgets import QuestionNameButtonTable, QuestionNameCheckButtonTable

import solfege

class Teacher(abstract.Teacher):
    OK = 0
    ERR_PICKY = 1
    ERR_NO_QUESTION = 2
    def __init__(self, exname):
        abstract.Teacher.__init__(self, exname)
        self.lessonfileclass = lessonfile.IdByNameLessonfile
        self.m_statistics = statistics.LessonStatistics(self)
        for s in ('vertic', 'horiz',
                  'progression', # depcrecated, used to set labelformat
                  'show', 'play', # at_music_start = show, play
                  'accidentals', 'key', 'semitones', 'atonal',
            ):
            self.m_lessonfile_defs[s] = s
    def enter_test_mode(self):
        self.m_custom_mode = False
        self.m_statistics.enter_test_mode()
        self.m_P.enter_test_mode()
    def exit_test_mode(self):
        self.m_statistics.exit_test_mode()
        self.m_custom_mode = self.get_bool('gui/expert_mode')
    def give_up(self):
        self.q_status = self.QSTATUS_GIVE_UP
    def new_question(self):
        """
        UI will never call this function unless we have a usable lessonfile.
        """
        if self.m_timeout_handle:
            GObject.source_remove(self.m_timeout_handle)
            self.m_timeout_handle = None

        if solfege.app.m_test_mode:
            self.m_P.next_test_question()
            self.q_status = self.QSTATUS_NEW
            return self.OK

        if self.get_bool('config/picky_on_new_question') \
                 and self.q_status in [self.QSTATUS_NEW, self.QSTATUS_WRONG]:
            return Teacher.ERR_PICKY

        self.q_status = self.QSTATUS_NO

        assert self.m_P
        self.m_P.select_random_question()
        self.q_status = self.QSTATUS_NEW
        return self.OK
    def guess_answer(self, answer):
        """
        Return: 1 if correct, None if wrong
        """
        if answer == self.m_P.get_cname():
            if self.q_status == self.QSTATUS_NEW \
                    and not self.m_custom_mode:
                self.m_statistics.add_correct(answer)
            self.maybe_auto_new_question()
            self.q_status = self.QSTATUS_SOLVED
            return 1
        else:
            if self.q_status == self.QSTATUS_NEW:
                if not self.m_custom_mode:
                    self.m_statistics.add_wrong(self.m_P.get_cname(), answer)
                self.q_status = self.QSTATUS_WRONG
            if solfege.app.m_test_mode:
                self.maybe_auto_new_question()

class Gui(abstract.LessonbasedGui):
    def __init__(self, teacher):
        abstract.LessonbasedGui.__init__(self, teacher)
        ################
        # practise_box #
        ################
        self.g_music_displayer = mpd.MusicDisplayer()
        self.practise_box.pack_start(self.g_music_displayer, False, False, 0)
        self.g_bb = QuestionNameButtonTable(self.m_t.m_exname)
        self.practise_box.pack_start(self.g_bb, False, False, 0)

        self.g_flashbar = gu.FlashBar()
        self.g_flashbar.show()
        self.practise_box.pack_start(self.g_flashbar, False, False, 0)
        self.practise_box.set_spacing(gu.PAD)

        self.std_buttons_add(
            ('new', self.new_question),
            ('play_music', lambda w: self.run_exception_handled(self.m_t.m_P.play_question)),
            ('repeat', lambda w: self.run_exception_handled(self.m_t.m_P.play_question)),
            ('repeat_arpeggio', lambda w: self.run_exception_handled(self.m_t.m_P.play_question_arpeggio)),
            ('repeat_slowly', lambda w: self.run_exception_handled(self.m_t.m_P.play_question_slowly)),
            ('play_tonic', lambda w: self.run_exception_handled(self.m_t.play_tonic)),
            ('display_music', self.show_answer),
            ('show', self.show_answer),
            ('give_up', self.give_up),
        )

        self.practise_box.show_all()
        ##############
        # config_box #
        ##############
        self.config_box.set_border_width(12)
        self.config_box.set_spacing(18)
        self.add_random_transpose_gui()
        # -----------------------------------------
        self.g_select_questions_category_box, category_box= gu.hig_category_vbox(
            _("Questions to ask"))
        self.config_box.pack_start(self.g_select_questions_category_box, False, False, 0)
        self.g_select_questions = QuestionNameCheckButtonTable(self.m_t)
        self.g_select_questions.initialize(4, 0)
        category_box.pack_start(self.g_select_questions, False, False, 0)
        self.g_select_questions.show()
        # ------------------------------------------
        self._add_auto_new_question_gui(self.config_box)
        # ----------------------------------------------
        ##############
        # statistics #
        ##############
        self.setup_statisticsviewer(statisticsviewer.StatisticsViewer,
                                   _("Identify by name"))
        def _f(varname):
            self.m_t.q_status = self.QSTATUS_NO
            self.setup_action_area_buttons()
        self.add_watch('ask_for_names', _f)
    def update_answer_buttons(self):
        self.g_bb.initialize(self.m_t.m_P.header.fillnum,
                             self.m_t.m_P.header.filldir)
        for question in self.m_t.m_P.iterate_questions_with_unique_names():
            self.g_bb.add(question, self.on_click)
        if self.m_t.m_custom_mode:
            self.g_bb.ask_for_names_changed()
    def update_select_question_buttons(self):
        #FIXME duplicate code in src/chord.py
        if self.m_t.m_custom_mode:
            self.g_select_questions_category_box.show()
            self.g_select_questions.initialize(self.m_t.m_P.header.fillnum,
                                 self.m_t.m_P.header.filldir)
            self.m_t.check_askfor()
            for question in self.m_t.m_P.iterate_questions_with_unique_names():
                self.g_select_questions.add(question)
        else:
            self.g_select_questions_category_box.hide()
            self.g_select_questions.initialize(0, 0)
    def setup_action_area_buttons(self):
        """
        Make the buttons visible or invisible depending
        on the lesson file, and make the right set of buttons
        sensitive for the first question.
        """
        self.std_buttons_start_practise()
        if [q for q in self.m_t.m_P.m_questions if isinstance(q.music, lessonfile.MpdTransposable)]:
            self.g_random_transpose_box.show()
        else:
            self.g_random_transpose_box.hide()
        self.show_hide_at_question_start_buttons()
        if self.m_t.m_P.header.have_music_displayer:
            self.g_music_displayer.show()
            self.g_music_displayer.clear(self.m_t.m_P.header.music_displayer_stafflines)
        else:
            self.g_music_displayer.hide()
    def give_up(self, _o=None):
        if self.m_t.q_status == self.QSTATUS_WRONG:
            self.g_flashbar.push(_("The answer is: {answer}"), answer=self.m_t.m_P.get_name())
            self.m_t.give_up()
            self.std_buttons_give_up()
            if self.m_t.m_P.header.have_music_displayer:
                self.run_exception_handled(self.show_answer)
    def on_click(self, button, event=None):
        if not event:
            self.on_left_click(button)
        elif event.button == 3:
            if self.m_t.m_P and self.m_t.m_P.header.enable_right_click:
                self.on_right_click(button)
            else:
                self.g_flashbar.flash(_("Right click is not allowed for this lesson file."))
    def on_right_click(self, button):
        if solfege.app.m_test_mode:
            return
        if self.m_t.q_status == self.QSTATUS_NO:
            self.g_flashbar.flash(_("Click 'New' to begin."))
            return
        if self.m_t.q_status == self.QSTATUS_NEW:
            self.g_flashbar.flash(_("You should try to guess before right-clicking."))
            return
        if self.m_t.q_status not in (self.QSTATUS_GIVE_UP, self.QSTATUS_WRONG,
                    self.QSTATUS_SOLVED):
            self.g_flashbar.flash(_("You should try to guess before right-clicking."))
            return
        try:
            if 'set' in self.m_t.m_P.get_question():
                for idx, question in enumerate(self.m_t.m_P.m_questions):
                    if question.set == self.m_t.m_P.get_question().set \
                        and question.name.cval == button.m_cname:
                        self.m_t.m_P.play_question(question)
                        return
            for idx, question in enumerate(self.m_t.m_P.m_questions):
                if question.name.cval == button.m_cname:
                    self.m_t.m_P.play_question(question)
                    return
        except Exception, e:
            if not self.standard_exception_handler(e):
                raise
    def on_left_click(self, button):
        if self.m_t.q_status == self.QSTATUS_NO:
            if solfege.app.m_test_mode:
                self.g_flashbar.flash(_("Click 'Start test' to begin."))
            else:
                self.g_flashbar.flash(_("Click 'New' to begin."))
            return
        try:
            if self.m_t.q_status == self.QSTATUS_SOLVED:
                if self.m_t.guess_answer(button.m_cname):
                    self.g_flashbar.flash(_("Correct, but you have already solved this question"))
                else:
                    self.g_flashbar.flash(_("Wrong, but you have already solved this question"))
            elif self.m_t.q_status in (self.QSTATUS_NEW, self.QSTATUS_WRONG):
                if self.m_t.guess_answer(button.m_cname):
                    self.g_flashbar.flash(_("Correct"))
                    self.std_buttons_answer_correct()
                    if self.m_t.m_P.header.have_music_displayer:
                        self.show_answer()
                else:
                    self.g_flashbar.flash(_("Wrong"))
                    if self.get_bool("config/auto_repeat_question_if_wrong_answer"):
                        self.m_t.m_P.play_question()
                    self.std_buttons_answer_wrong()
        except Exception, e:
            if not self.standard_exception_handler(e):
                raise
    def new_question(self, widget=None):
        """
        The new button should be insensitive if we have no lesson file.
        """
        if solfege.app.m_test_mode and self.m_t.m_P.is_test_complete():
            self.do_test_complete()
            return
        if solfege.app.m_test_mode:
            self.g_new.hide()
        def exception_cleanup():
            self.m_t.q_status = self.QSTATUS_NO
            soundcard.synth.stop()
            self.std_buttons_exception_cleanup()
        if self.m_t.m_P.header.have_music_displayer:
            self.g_music_displayer.clear(self.m_t.m_P.header.music_displayer_stafflines)
        try:
            g = self.m_t.new_question()
            if g == self.m_t.OK:
                self.do_at_question_start_show_play()
                self.std_buttons_new_question()
                self.g_bb.grab_focus_first_button()
                self.g_flashbar.clear()
        except Exception, e:
            if isinstance(e, mpd.MpdException):
                if 'm_mpd_badcode' not in dir(e):
                    e.m_mpd_badcode = self.m_t.m_P.get_question()['music'].get_err_context(e, self.m_t.m_P)
            if not self.standard_exception_handler(e, exception_cleanup):
                raise
    def on_start_practise(self):
        self.m_t.m_custom_mode = self.get_bool('gui/expert_mode')
        super(Gui, self).on_start_practise()
        for question in self.m_t.m_P.m_questions:
            question.active = 1
        self.setup_action_area_buttons()
        self.update_answer_buttons()
        self.update_select_question_buttons()
        self.g_random_transpose.set_text(str(self.m_t.m_P.header.random_transpose))
        self.g_flashbar.require_size([
            _("Right click is not allowed for this lesson file."),
            _("You should try to guess before right-clicking."),
            _("You should try to guess before right-clicking."),
            _("Correct, but you have already solved this question"),
            _("Wrong, but you have already solved this question"),
            _("You have to select some questions to practise."),
        ])
        if (not self.m_t.m_custom_mode) or solfege.app.m_test_mode:
            self.m_t.m_statistics.reset_session()
        self.g_statview.g_heading.set_text(self.m_t.m_P.header.title)
        self.g_music_displayer.clear(self.m_t.m_P.header.music_displayer_stafflines)
        if solfege.app.m_test_mode:
            self.g_flashbar.delayed_flash(self.short_delay,
                _("Click 'Start test' to begin."))
        else:
            self.g_flashbar.delayed_flash(self.short_delay,
                _("Click 'New' to begin."))
    def on_end_practise(self):
        self.m_t.end_practise()
        self.std_buttons_end_practise()
        if self.m_t.m_P and self.m_t.m_P.header.have_music_displayer:
            self.g_music_displayer.clear(self.m_t.m_P.header.music_displayer_stafflines)
        self.g_flashbar.clear()
    def enter_test_mode(self):
        self.m_saved_q_auto = self.get_bool('new_question_automatically')
        self.m_saved_s_new = self.get_float('seconds_before_new_question')
        self.set_bool('new_question_automatically', True)
        self.set_float('seconds_before_new_question', 0.5)
        self.m_t.enter_test_mode()
        self.g_give_up.hide()
        self.g_new.set_label(_("_Start test"))
        self.g_show.hide()
        self.g_repeat_arpeggio.hide()
        self.g_repeat_slowly.hide()
        self.g_cancel_test.show()
    def exit_test_mode(self):
        self.set_bool('new_question_automatically', self.m_saved_q_auto)
        self.set_float('seconds_before_new_question', self.m_saved_s_new)
        self.m_t.exit_test_mode()
        self.g_new.set_label(_("_New"))
        self.g_new.show()
        self.g_repeat_slowly.show()
