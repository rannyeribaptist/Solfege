# vim: set fileencoding=utf-8:
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

from solfege import abstract
from solfege.mpd import elems
from solfege import gu
from solfege import lessonfile
from solfege import mpd
from solfege import soundcard

class Teacher(abstract.Teacher):
    def __init__(self, exname):
        abstract.Teacher.__init__(self, exname)
        self.lessonfileclass = lessonfile.QuestionsLessonfile
    def new_question(self):
        if self.get_bool('config/picky_on_new_question') \
                and self.q_status in [self.QSTATUS_NEW, self.QSTATUS_WRONG]:
            return self.ERR_PICKY
        self.q_status = self.QSTATUS_NEW
        self.m_P.select_random_question()
    def play_question(self):
        # We can only create countin for questions that are generated using
        # the mpd module
        music = self.m_P.get_question()['music']
        if isinstance(music, lessonfile.MpdParsable):
            score = self.m_P.get_score('music')
            countin = self.m_P.m_globals.get('countin')
            countin = self.m_P.get_question().get('countin', countin)
            if countin:
                score = elems.Score.concat2(countin.get_score(self.m_P, as_name='countin'), score)
            tracks = mpd.score_to_tracks(score)
            tracks[0].prepend_bpm(*self.m_P.get_tempo())
            soundcard.synth.play_track(*tracks)
        else:
            self.m_P.play_question()
    def get_empty_staff(self):
        """
        Return a score with and empty staff with the correct numbers of bars
        required to answer the current question.
        """
        score = elems.Score()
        score.add_staff(staff_class=elems.RhythmStaff)
        if 'rhythm' in self.m_P.get_question():
            music_obj = self.m_P.get_question()['rhythm']
            if not isinstance(music_obj, lessonfile.MpdParsable):
                raise lessonfile.LessonfileException(_(u"The music object named «rhythm» is not a subclass of MpdParsable"),
                _(u'Read about the «rhythm» variable in the section «Question block» in the chapter named «Extending GNU Solfege» in the user manual.'))
            music = music_obj.get_mpd_music_string(self.m_P)
        else:
            music_obj = self.m_P.get_question()['music']
            if not isinstance(music_obj, lessonfile.MpdParsable):
                raise lessonfile.LessonfileException(_("The music object named «music» is not a subclass of MpdParsable"),
                _('Read about the «rhythm» variable in the section «Question block» in the chapter named «Extending GNU Solfege» in the user manual.'))
            music = music_obj.get_mpd_music_string(self.m_P)
        for bar in mpd.parser.parse_to_score_object(music).m_bars:
            if isinstance(bar, elems.PartialBar):
                score.add_partial_bar(bar.m_duration, bar.m_timesig)
            else:
                score.add_bar(bar.m_timesig)
        score.voice11.fill_with_skips()
        return score
    def guess_answer(self, score):
        assert self.q_status not in (self.QSTATUS_NO, self.QSTATUS_GIVE_UP)
        q = self.m_P.get_question()
        if 'rhythm' in q:
            qvar = 'rhythm'
        else:
            qvar = 'music'
        qscore = mpd.parser.parse_to_score_object(
            q[qvar].get_mpd_music_string(self.m_P))
        if qscore.get_timelist() == score.get_timelist():
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
        self.g_w = mpd.RhythmWidget()
        self.g_w.connect('score-updated', self.on_score_updated)
        self.practise_box.pack_start(self.g_w, False)
        self.g_c = mpd.RhythmWidgetController(self.g_w)
        self.practise_box.pack_start(self.g_c, False)
        self.g_flashbar = gu.FlashBar()
        self.practise_box.pack_start(self.g_flashbar, False)
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
            self.m_t.q_status = self.QSTATUS_NO
            soundcard.synth.stop()
            self.std_buttons_exception_cleanup()
        self.m_t.new_question()
        try:
            self.m_t.play_question()
            self.std_buttons_new_question()
            self.g_w.grab_focus()
            self.g_w.set_score(self.m_t.get_empty_staff())
            self.g_c.set_editable(True)
        except Exception, e:
            if isinstance(e, mpd.MpdException):
                if 'm_mpd_badcode' not in dir(e):
                    e.m_mpd_badcode = self.m_t.m_P.get_question()[e.m_mpd_varname].get_err_context(e, self.m_t.m_P)
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
        if 'rhythm' in self.m_t.m_P.get_question():
            varname = 'rhythm'
        else:
            varname = 'music'
        answer = mpd.parser.parse_to_score_object(
                self.m_t.m_P.get_question()[varname].get_mpd_music_string(
                    self.m_t.m_P))
        answer.m_staffs.append(self.g_w.m_score.m_staffs[0])
        answer.m_staffs[-1].set_parent(answer)
        answer.m_staffs[0].m_label = _("The music played:")
        answer.m_staffs[-1].m_label = _("The rhythm you entered:")
        answer.create_shortcuts()
        self.g_w.set_score(answer, cursor=None)
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

