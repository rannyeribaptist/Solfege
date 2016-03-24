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

from solfege import abstract
from solfege import lessonfile
from solfege import mpd
from solfege.exercises import rhythmtapping

from solfege.mpd.requests import MusicRequest

class Teacher(abstract.RhythmAddOnClass, rhythmtapping.Teacher):
    def __init__(self, exname):
        rhythmtapping.Teacher.__init__(self, exname)
        self.lessonfileclass = lessonfile.HeaderLessonfile
    def play_question(self):
        self.play_rhythm(self.get_music_string())
    def get_timedelta_list(self):
        """
        Return a list of the number of seconds between it should be between
        each tap.
        """
        lexer = mpd.parser.Lexer(self.get_music_notenames(False))
        x = len(lexer.m_string)
        retval = []
        for toc, toc_data in lexer:
            if isinstance(toc_data, mpd.requests.MusicRequest):
                retval.append(float(toc_data.m_duration.get_rat_value()) * 4 / self.m_P.header.bpm * 60)
            else:
                retval[-1] += float(toc_data.m_duration.get_rat_value()) * 4 / self.m_P.header.bpm * 60
        return retval

class Gui(rhythmtapping.Gui, abstract.RhythmAddOnGuiClass):
    please_tap_str = _("Please tap the rhythm.")
    def __init__(self, teacher):
        rhythmtapping.Gui.__init__(self, teacher)
        self.add_select_elements_gui()
        self.add_select_num_beats_gui()
    def do_at_question_start_show_play(self):
        """
        It will show and/or play music based on
        the header.at_question_start  variable.

        The Teacher class of all exercises that use this method must
        have a .play_question method.
        """
        if self.m_t.m_P.header.at_question_start == 'show':
            self.show_answer()
        elif self.m_t.m_P.header.at_question_start == 'play':
            self.m_t.play_question()
            #if 'cuemusic' in self.m_t.m_P.get_question():
            #    self.display_music('cuemusic')
        else:
            # Have to do it this way because both lesson files with question
            # blocks and lesson files with only a lesson file header use
            # this method. And only lesson files based on QuestionsLessonfile
            # implement .play_question.
            self.m_t.play_question()
            if 'show' in self.m_t.m_P.header.at_question_start \
                and 'play' in self.m_t.m_P.header.at_question_start:
                self.show_answer()
    def on_repeat(self, widget):
        self.m_t.play_question()
        self.g_tap.grab_focus()
    def on_start_practise(self):
        self.m_t.m_custom_mode = bool(self.m_t.m_P.header.configurable_rhythm_elements)
        super(Gui, self).on_start_practise()
        self.m_t.set_elements_variables()
        if self.m_t.m_custom_mode:
            self.update_select_elements_buttons()
            self.g_element_frame.show()
        else:
            self.g_element_frame.hide()
        self.m_t.set_default_header_values()
