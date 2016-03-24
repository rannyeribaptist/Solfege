# GNU Solfege - free ear training software
# Copyright (C) 2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2011  Tom Cato Amundsen
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
from solfege import utils

class Teacher(abstract.Teacher):
    def __init__(self, exname):
        abstract.Teacher.__init__(self, exname)
        self.lessonfileclass = lessonfile.SingChordLessonfile
        for s in 'accidentals', 'key', 'semitones', 'atonal':
            self.m_lessonfile_defs[s] = s
    def new_question(self):
        self.q_status = self.QSTATUS_NEW
        self.m_P.select_random_question()
    def play_440hz(self):
        utils.play_note(4, mpd.notename_to_int("a'"))

class Gui(abstract.LessonbasedGui):
    def __init__(self, teacher):
        abstract.LessonbasedGui.__init__(self, teacher)
        ################
        # practise_box #
        ################
        self.g_music_displayer = mpd.MusicDisplayer()
        self.practise_box.pack_start(self.g_music_displayer, True, True, 0)

        self.g_new = gu.bButton(self.action_area, _("_New"), self.new_question)
        gu.bButton(self.action_area, _("440h_z"), self.play_440hz)
        self.g_play_answer = gu.bButton(self.action_area, _("_Play answer"),
            lambda w: self.run_exception_handled(self.m_t.m_P.play_question_arpeggio))
        self.practise_box.show_all()
        ##############
        # config_box #
        ##############
        self.add_random_transpose_gui()
    def new_question(self, widget=None):
        def exception_cleanup():
            soundcard.synth.stop()
            self.g_play_answer.set_sensitive(False)
            self.g_music_displayer.clear(2)
        try:
            self.m_t.new_question()
            fontsize = self.get_int('config/feta_font_size=20')
            self.g_music_displayer.display(self.m_t.m_P.get_music(), fontsize)
            self.g_play_answer.set_sensitive(True)
            self.m_t.play_440hz()
        except Exception, e:
            if isinstance(e, mpd.MpdException):
                e.m_mpd_varname = 'music'
                e.m_mpd_badcode = self.m_t.m_P.get_question().music.get_err_context(e, self.m_t.m_P)
            if not self.standard_exception_handler(e, exception_cleanup):
                raise
    def on_start_practise(self):
        super(Gui, self).on_start_practise()
        self.g_music_displayer.clear(2)
        self.g_random_transpose.set_text(str(self.m_t.m_P.header.random_transpose))
        self.g_new.set_sensitive(True)
        self.g_new.grab_focus()
        self.g_play_answer.set_sensitive(False)
    def on_end_practise(self):
        self.m_t.end_practise()
        self.g_play_answer.set_sensitive(False)
        self.g_music_displayer.clear(2)
    def play_440hz(self, widget):
        try:
            self.m_t.play_440hz()
        except Exception, e:
            if not self.standard_exception_handler(e):
                raise

