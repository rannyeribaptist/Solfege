# GNU Solfege - free ear training software
# Copyright (C) 2010, 2011  Tom Cato Amundsen
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

from solfege import gu
from solfege import abstract
from solfege import lessonfile
from solfege import mpd
from solfege import soundcard

from solfege.mpd import Duration
from solfege.mpd import elems
from solfege.mpd import RhythmWidget, RhythmWidgetController


class Teacher(abstract.Teacher):
    ERR_PICKY = 1
    OK = 2
    def __init__(self, exname):
        abstract.Teacher.__init__(self, exname)
        self.lessonfileclass = lessonfile.RhythmDictation2Lessonfile
    def new_question(self):
        """
        We will create a timelist of the question when we create the
        question, and compare it to the RhythmStaff.get_timelist.
        We will also create a  PercussionTrack that will be used when
        we play the question.
        """
        if self.get_bool('config/picky_on_new_question') \
                and self.q_status in [self.QSTATUS_NEW, self.QSTATUS_WRONG]:
            return self.ERR_PICKY
        self.q_status = self.QSTATUS_NEW
        self.m_P.generate_random_question()
        self.m_score = self.m_P.m_answer_score
        return self.OK
    def play_question(self):
        score = self.m_P.m_question_score
        countin = self.m_P.m_globals.get('countin')
        countin = self.m_P.m_questions[self.m_P._idx].get('countin', countin)
        if countin:
            score = elems.Score.concat2(countin.get_score(self.m_P, as_name='countin'), score)
        tracks = mpd.score_to_tracks(score)
        tracks[0].prepend_bpm(*self.m_P.get_tempo())
        soundcard.synth.play_track(*tracks)
    def guess_answer(self, staff):
        assert self.q_status not in (self.QSTATUS_NO, self.QSTATUS_GIVE_UP)
        if self.m_P.m_question_score.get_timelist() == self.m_P.m_answer_score.get_timelist():
            self.q_status = self.QSTATUS_SOLVED
            return True
        else:
            self.q_status = self.QSTATUS_WRONG
            return False
    def give_up(self):
        self.q_status = self.QSTATUS_GIVE_UP


class Gui(abstract.LessonbasedGui):
    def __init__(self, teacher):
        abstract.LessonbasedGui.__init__(self, teacher)
        self.g_w = RhythmWidget()
        self.g_w.connect('score-updated', self.on_score_updated)
        self.practise_box.pack_start(self.g_w, False, False, 0)
        self.g_c = RhythmWidgetController(self.g_w)
        self.practise_box.pack_start(self.g_c, False, False, 0)
        self.g_flashbar = gu.FlashBar()
        self.practise_box.pack_start(self.g_flashbar, False, False, 0)
        self.g_flashbar.show()
        self.std_buttons_add(
            ('new', self.new_question),
            ('guess_answer', self.guess_answer),
            ('repeat', self.repeat_question),
            ('give_up', self.give_up))
        self.g_w.show()
    def on_score_updated(self, w):
        self.g_guess_answer.set_sensitive(bool(self.g_w.m_score.get_timelist()))
    def new_question(self, *w):
        def exception_cleanup():
            self.m_t.q_status = self.m_t.QSTATUS_NO
            self.std_buttons_exception_cleanup()
        try:
            g = self.m_t.new_question()
            if g == self.m_t.OK:
                self.m_t.play_question()
                self.std_buttons_new_question()
                self.g_w.grab_focus()
                self.g_w.set_score(self.m_t.m_score)
                self.g_c.set_editable(True)
        except Duration.BadStringException, e:
            gu.dialog_ok("Lesson file error", secondary_text=u"Bad rhythm string in the elements variable of the lessonfile. Only digits and dots expected: %s" % unicode(e))
            exception_cleanup()
        except Exception, e:
            if not self.standard_exception_handler(e, exception_cleanup):
                raise
    def guess_answer(self, *w):
        if self.m_t.q_status == Teacher.QSTATUS_SOLVED:
            if self.m_t.guess_answer(self.g_w.m_score):
                self.g_flashbar.flash(_("Correct, but you have already solved this question"))
            else:
                self.g_flashbar.flash(_("Wrong, but you have already solved this question"))
        else:
            if self.m_t.guess_answer(self.g_w.m_score):
                self.g_flashbar.flash(_("Correct"))
                self.std_buttons_answer_correct()
            else:
                self.g_flashbar.flash(_("Wrong"))
                self.std_buttons_answer_wrong()
                self.g_w.grab_focus()
    def repeat_question(self, *w):
        self.g_w.grab_focus()
        self.m_t.play_question()
    def give_up(self, *w):
        # Make a copy of the question asked. Then attach the staff
        # the user entered below, set some labels and display it.
        score_copy = self.m_t.m_P.m_question_score.copy()
        score_copy.m_staffs.append(self.g_w.m_score.m_staffs[0])
        score_copy.m_staffs[-1].set_parent(self.m_t.m_P.m_question_score)
        score_copy.m_staffs[0].m_label = _("The music played:")
        score_copy.m_staffs[-1].m_label = _("The rhythm you entered:")
        score_copy.create_shortcuts()
        self.g_w.set_score(score_copy, cursor=None)
        self.m_t.give_up()
        self.g_c.set_editable(False)
        self.std_buttons_give_up()
    def on_start_practise(self):
        super(Gui, self).on_start_practise()
        self.std_buttons_start_practise()
        self.g_c.set_editable(False)
        self.g_w.set_score(elems.Score())
        self.g_flashbar.delayed_flash(self.short_delay,
            _("Click 'New' to begin."))
    def on_end_practise(self):
        super(Gui, self).on_end_practise()
        self.g_w.set_score(elems.Score())
