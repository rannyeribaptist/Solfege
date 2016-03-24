# GNU Solfege - free ear training software
# Copyright (C) 2006, 2007, 2008, 2011 Tom Cato Amundsen
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

import random

from gi.repository import Gtk

from solfege import abstract
from solfege import gu
from solfege import lessonfile
from solfege import mpd

import solfege

class Teacher(abstract.Teacher):
    def __init__(self, exname):
        abstract.Teacher.__init__(self, exname)
        self.lessonfileclass = lessonfile.NameIntervalLessonfile
        self.m_answered_quality = None
        self.m_answered_number = None
        for s in ('d1', 'p1', 'a1',
                  'd2', 'm2', 'M2', 'a2',
                  'd3', 'm3', 'M3', 'a3',
                  'd4', 'p4', 'a4',
                  'd5', 'p5', 'a5',
                  'd6', 'm6', 'M6', 'a6',
                  'd7', 'm7', 'M7', 'a7',
                  'd8', 'p8', 'a8',
                  'd9', 'm9', 'M9', 'a9',
                  'd10', 'm10', 'M10', 'a10',
                  'violin', 'treble', 'subbass', 'bass', 'baritone',
                  'varbaritone', 'tenor', 'alto', 'mezzosoprano', 'french',
                  ):
            self.m_lessonfile_defs[s] = s
    def new_question(self):
        """
        Return True if a new question was created.
        Return False if the variables in the lesson file made it impossible
        to create a question.
        """
        self.m_interval = random.choice(self.m_P.header.intervals)
        c = 0
        while 1:
            c += 1
            if self.m_P.header.tones[1] - self.m_P.header.tones[0] < self.m_interval.get_intvalue():
                return False
            self.m_low_pitch = mpd.MusicalPitch().randomize(
                self.m_P.header.tones[0],
                self.m_P.header.tones[1] - self.m_interval.get_intvalue())
            #
            if self.m_interval.steps() == (self.m_low_pitch + self.m_interval).steps() - self.m_low_pitch.steps():
                # this can happen for cases like d# + aug 3
                continue
            if abs(self.m_low_pitch.m_accidental_i) <= self.m_P.header.accidentals and\
                    abs((self.m_low_pitch + self.m_interval).m_accidental_i) <= self.m_P.header.accidentals:
                break
            if c > 1000:
                return False
        self.m_answered_quality = None
        self.m_answered_number = None
        self.q_status = self.QSTATUS_NEW
        return True
    def get_music_string(self):
        return r"\staff{ \clef %(clef)s \stemUp %(low)s %(high)s"% {
            'clef': self.m_P.header.clef,
            'high': (self.m_low_pitch + self.m_interval).get_octave_notename(),
            'low': self.m_low_pitch.get_octave_notename(),
        }
    def _check_answer(self):
        """
        Set qstatus and return
        """
        assert self.q_status in (self.QSTATUS_NEW, self.QSTATUS_WRONG)
        if self.answer_complete():
            if self.answered_correctly():
                self.q_status = self.QSTATUS_SOLVED
            else:
                self.q_status = self.QSTATUS_WRONG
    def answer_complete(self):
        """
        Return True if both interval quality and interval number
        has been guessed. If there is only one choice, then we don't
        have to guess it.
        """
        return ((self.m_answered_quality is not None
                 or len(self.m_P.header.interval_quality) == 1)
            and (self.m_answered_number is not None
                 or (len(self.m_P.header.interval_number) == 1)))
    def answer_quality(self, n):
        """
        Set q_status according to how we answer.
        """
        assert self.q_status in (self.QSTATUS_NEW, self.QSTATUS_WRONG)
        self.m_answered_quality = n
        self._check_answer()
    def answer_number(self, n):
        """
        Set q_status according to how we answer.
        """
        assert self.q_status in (self.QSTATUS_NEW, self.QSTATUS_WRONG)
        self.m_answered_number = n
        self._check_answer()
    def answered_correctly(self):
        """
        Return true if the question is answered correctly.
        """
        if self.m_answered_quality:
            q = self.m_answered_quality
        else:
            assert len(self.m_P.header.interval_quality) == 1
            q = self.m_P.header.interval_quality[0]
        if self.m_answered_number:
            n = self.m_answered_number
        else:
            assert len(self.m_P.header.interval_number) == 1
            n = self.m_P.header.interval_number[0]
        try:
            i = mpd.Interval("%s%s" % (q, n))
        except mpd.interval.InvalidIntervalnameException:
            return False
        return i == self.m_interval


class Gui(abstract.LessonbasedGui):
    lesson_heading = _("Name the interval")
    def __init__(self, teacher):
        abstract.LessonbasedGui.__init__(self, teacher, True)
        self.g_music_displayer = mpd.MusicDisplayer()
        self.g_music_displayer.show()
        self.practise_box.pack_start(self.g_music_displayer, False, False, 0)
        self.g_flashbar = gu.FlashBar()
        self.g_flashbar.show()
        self.practise_box.pack_start(self.g_flashbar, False, False, 0)
        self.g_quality_box = gu.bHBox(self.practise_box)
        self.g_quality_box.show()
        self.g_number_box = gu.bHBox(self.practise_box)
        self.g_number_box.show()
        gu.bButton(self.action_area, _("_New"), self.new_question)
    def unbold_interval(self):
        for b in self.g_number_box.get_children():
            b.get_child().set_name('')
    def unbold_quality(self):
        for b in self.g_quality_box.get_children():
            b.get_child().set_name('')
    def new_question(self, widget=None):
        self.unbold_interval()
        self.unbold_quality()
        try:
            if self.m_t.new_question():
                self.g_music_displayer.display(self.m_t.get_music_string(),
                    self.get_int('config/feta_font_size=20'))
            else:
                solfege.win.display_error_message2(_("Could not satisfy the constraints in the lesson header."), 'You must make more tones available by adjusting the "tones" variable in the lesson file header of the lesson file "%s".' % self.m_t.m_P.m_filename)
        except lessonfile.LessonfileException, e:
            if not self.standard_exception_handler(e):
                raise
    def on_interval_quality_clicked(self, button, n):
        if self.m_t.q_status == self.QSTATUS_NO:
            self.g_flashbar.flash(_("Click 'New' to begin."))
            return
        if self.m_t.q_status == self.QSTATUS_SOLVED:
            if self.m_t.m_answered_quality == n:
                self.g_flashbar.flash(_("Correct, but you have already solved this question"))
            else:
                self.g_flashbar.flash(_("Wrong, but you have already solved this question"))
            return
        self.m_t.answer_quality(n)
        self.unbold_quality()
        b = [b for b in self.g_quality_box.get_children() if b.m_interval_quality == n][0]
        b.get_child().set_name("BoldText")
        if self.m_t.answer_complete():
            self.handle_do_answer()
    def on_interval_number_clicked(self, button, n):
        if self.m_t.q_status == self.QSTATUS_NO:
            self.g_flashbar.flash(_("Click 'New' to begin."))
            return
        if self.m_t.q_status == self.QSTATUS_SOLVED:
            if self.m_t.m_answered_number == n:
                self.g_flashbar.flash(_("Correct, but you have already solved this question"))
            else:
                self.g_flashbar.flash(_("Wrong, but you have already solved this question"))
            return
        self.m_t.answer_number(n)
        self.unbold_interval()
        b = [b for b in self.g_number_box.get_children() if b.m_interval_number == n][0]
        b.get_child().set_name("BoldText")
        if self.m_t.answer_complete():
            self.handle_do_answer()
    def handle_do_answer(self):
        self.g_flashbar.clear()
        if self.m_t.answered_correctly():
            self.g_flashbar.flash(_("Correct"))
        else:
            self.g_flashbar.flash(_("Wrong"))
    def on_start_practise(self):
        super(Gui, self).on_start_practise()
        self.g_music_displayer.clear()
        [btn.destroy() for btn in self.g_number_box.get_children()]
        for n in self.m_t.m_P.header.interval_number:
            xgettext_ignore = _i
            b = Gtk.Button(xgettext_ignore("interval|%s" % mpd.interval.number_name(n)))
            b.m_interval_number = n
            b.connect('clicked', self.on_interval_number_clicked, n)
            self.g_number_box.pack_start(b, True, True, 0)
            b.show()
        [btn.destroy() for btn in self.g_quality_box.get_children()]
        for n in self.m_t.m_P.header.interval_quality:
            b = Gtk.Button(mpd.Interval.nn_to_translated_quality(n))
            b.m_interval_quality = n
            b.connect('clicked', self.on_interval_quality_clicked, n)
            self.g_quality_box.pack_start(b, True, True, 0)
            b.show()
            self.g_flashbar.require_size([
                _("Correct, but you have already solved this question"),
                _("Wrong, but you have already solved this question"),
            ])
            self.g_flashbar.delayed_flash(self.short_delay,
                _("Click 'New' to begin."))
    def on_end_practise(self):
        [btn.destroy() for btn in self.g_number_box.get_children()]
        [btn.destroy() for btn in self.g_quality_box.get_children()]
        self.g_music_displayer.clear()
