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

import logging
import time

from gi.repository import Gtk

from solfege import abstract
from solfege import gu
from solfege import lessonfile
from solfege import mpd

from solfege.mpd.requests import MusicRequest

class Teacher(abstract.Teacher):
    OK = 0
    ERR_PICKY = 1
    ERR_NO_ELEMS = 2
    def __init__(self, exname):
        abstract.Teacher.__init__(self, exname)
        self.lessonfileclass = lessonfile.QuestionsLessonfile
        for s in 'show', 'play':
            self.m_lessonfile_defs[s] = s
    def new_question(self):
        self.m_P.select_random_question()
        return self.OK
    def get_timedelta_list(self):
        """
        Return a list of the number of seconds between it should be between
        each tap. Ignore "count-in" tones.
        """
        if 'rhythm' in self.m_P.get_question():
            qvar = 'rhythm'
        else:
            qvar = 'music'
        is_rhythm = isinstance(self.m_P.get_question().music,
                               lessonfile.Rhythm)
        lexer = mpd.parser.Lexer(self.m_P.get_question()[qvar].m_musicdata)
        x = len(lexer.m_string)
        retval = []
        try:
            for toc, toc_data in lexer:
                if is_rhythm == 'rhythm':
                    if toc_data.m_pitch.get_octave_notename() == 'd':
                        continue
                    if toc_data.m_pitch.get_octave_notename() != 'c':
                        logging.warning("rhythmtapping: warning: Use only c and d for rhythm music objects")
                if isinstance(toc_data, mpd.requests.MusicRequest):
                    retval.append(float(lexer.m_notelen.get_rat_value()) * self.m_P.get_tempo()[1] / self.m_P.get_tempo()[0] * 60)
                else:
                    retval[-1] += float(lexer.m_notelen.get_rat_value()) * self.m_P.get_tempo()[1] / self.m_P.get_tempo()[0] * 60
        except mpd.MpdException, e:
            e.m_obj_lineno, e.m_linepos1, e.m_linepos2 = lexer.get_error_location()
            e.m_mpd_varname = qvar
            e.m_mpd_badcode = self.m_P.get_question()[qvar].get_err_context(e, self.m_P)
            raise
        return retval
    def start_tapping(self):
        self.m_taps = []
    def tap(self):
        self.m_taps.append(time.time())
    def is_tap_complete(self):
        """
        Return True if the user has tapped as many times as the
        question requires.
        """
        # A little abuse of get_timedelta_list, but this makes it simple.
        return len(self.m_taps) == len(self.get_timedelta_list())
    def get_score(self):
        """
        Return a list of floats telling us how close the users answer was.
        Each float is the timedelta of the question divided by the
        timedelta of the answer.

        If at_question_start == show, then the time between the first
        and the second tap will set the tempo, and all the timedeltas will
        be compared
        """
        retval = []
        question = self.get_timedelta_list()
        if self.m_P.header.at_question_start == 'show':
            # The user can tap in any tempo since he will only se the music.
            # First we change the lists so that the time between the
            # first two taps are 1.0, and the other proportionally to this.
            question = [q/question[0] for q in question]
            answer = []
            for x, i in enumerate(self.m_taps[1:]):
                answer.append(self.m_taps[x+1] - self.m_taps[x])
            answer = [a/answer[0] for a in answer]
            for idx in range(len(answer)):
                retval.append(question[idx] / answer[idx])
        else:
            # Has to tap in the same tempo as the music played.
            for x, i in enumerate(self.m_taps[1:]):
                a = self.m_taps[x+1] - self.m_taps[x]
                retval.append(a / question[x])
        return retval
    def get_answer_status(self):
        """
        Will return a tuple (bool, string) where the bool is True if the
        exercises is answered correctly enough. The string is a message
        to the user describing how acourately the rhythm was tapped.
        """
        score = self.get_score()
        max_diff = max([abs(1.0-f) for f in score])
        limit = self.get_float("accuracy")
        if max_diff < limit:
            s = "OK: %.2f < %.2f" % (max_diff, limit)
        else:
            s = "Not good enough: %.2f > %.2f" % (max_diff, limit)
        return (max_diff < limit, s)

class Gui(abstract.LessonbasedGui):
    please_tap_str = _("Please tap the rhythm.")
    def __init__(self, teacher):
        abstract.Gui.__init__(self, teacher)
        #
        self.g_music_displayer = mpd.MusicDisplayer()
        self.practise_box.pack_start(self.g_music_displayer, False, False, 0)
        #
        self.g_tap = gu.bButton(self.practise_box, _("Tap here"), self.on_tap)
        self.std_buttons_add(
            ('new', self.on_new_question),
            ('play_music', lambda w: self.run_exception_handled(self.m_t.m_P.play_question)),
            ('display_music', self.show_answer),
            ('repeat', self.on_repeat),
            ('give_up', self.on_give_up))
        # Flashbar
        self.g_flashbar = gu.FlashBar()
        self.g_flashbar.show()
        self.practise_box.pack_start(self.g_flashbar, False, False, 0)
        # Config box
        label = Gtk.Label(label=_("Accuracy required:"))
        self.config_box_sizegroup.add_widget(label)
        label.set_alignment(1.0, 0.5)
        spin = gu.nSpinButton(self.m_exname, 'accuracy',
                              Gtk.Adjustment(0, 0, 2, 0.01, 0.05))
        spin.set_tooltip_text("See bug report #93 (http://bugs.solfege.org/93) and add suggested values to the bug report.")
        spin.set_digits(2)
        hbox = Gtk.HBox()
        hbox.set_spacing(gu.hig.SPACE_SMALL)
        hbox.pack_start(label, False, False, 0)
        hbox.pack_start(spin, False, False, 0)
        self.config_box.pack_start(hbox, False, False, 0)
        hbox.show_all()
    def on_new_question(self, widget=None):
        def exception_cleanup():
            self.m_t.end_practise()
            self.g_tap.set_sensitive(False)
            self.std_buttons_exception_cleanup()
        try:
            g = self.m_t.new_question()
        except Exception, e:
            if not self.standard_exception_handler(e, exception_cleanup):
                raise
            return
        if g == self.m_t.OK:
            if self.m_t.m_P.header.have_music_displayer:
                self.g_music_displayer.clear()
            try:
                self.do_at_question_start_show_play()
            except Exception, e:
                if not self.standard_exception_handler(e, exception_cleanup):
                    raise
            else:
                self.m_start_time = time.time()
                self.g_flashbar.push(self.please_tap_str)
                self.m_t.start_tapping()
                self.std_buttons_new_question()
                self.g_tap.set_sensitive(True)
                self.g_tap.grab_focus()
        elif g == self.m_t.ERR_PICKY:
            self.g_flashbar.flash(_("You have to solve this question first."))
        else:
            assert g == self.m_t.ERR_NO_ELEMS
            self.g_repeat.set_sensitive(False)
            self.g_flashbar.flash(_("You have to configure this exercise properly"))
    def on_give_up(self, widget):
        self.std_buttons_give_up()
        self.g_flashbar.clear()
        self.g_tap.set_sensitive(False)
        self.m_t.q_status = self.QSTATUS_GIVE_UP
    def on_repeat(self, widget):
        self.m_t.m_P.play_question()
        self.g_tap.grab_focus()
    def on_tap(self, widget=None):
        self.g_flashbar.set(_("Tapping in progress..."))
        self.m_t.tap()
        try:
            if self.m_t.is_tap_complete():
                solved, msg = self.m_t.get_answer_status()
                self.g_flashbar.pop()
                if solved:
                    self.std_buttons_answer_correct()
                    self.g_tap.set_sensitive(False)
                    self.m_t.q_status = self.QSTATUS_SOLVED
                else:
                    self.std_buttons_answer_wrong()
                    self.g_tap.grab_focus()
                    self.m_t.start_tapping()
                    self.g_flashbar.set(self.please_tap_str)
                self.g_flashbar.flash(msg)
        except Exception, e:
            # We need to check for exceptions here because for each
            # tap, solfege will parse a music string and compare the rhythm
            # the user has tapped so far.
            if not self.standard_exception_handler(e):
                raise
    def on_start_practise(self):
        super(Gui, self).on_start_practise()
        self.std_buttons_start_practise()
        self.g_tap.set_sensitive(False)
        self.show_hide_at_question_start_buttons()
        if self.m_t.m_P.header.have_music_displayer:
            self.g_music_displayer.show()
            self.g_music_displayer.clear()
        else:
            self.g_music_displayer.hide()
        self.g_flashbar.require_size([
         self.please_tap_str,
         ])
