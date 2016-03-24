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

import random

from gi.repository import Gtk

from solfege import abstract
from solfege import gu
from solfege import lessonfile
from solfege import mpd
from solfege import utils

class Teacher(abstract.Teacher):
    def __init__(self, exname):
        abstract.Teacher.__init__(self, exname)
        self.lessonfileclass = lessonfile.HeaderLessonfile
        self.m_question = None
    def new_question(self):
        self.q_status = self.QSTATUS_NEW
        self.m_question = ["c'", "cis'", "d'", "dis'", "e'", "f'", "fis'", "g'", "gis'", "a'", "ais'", "b'"]
        for x in range(100):
            a = random.randint(0, 11)
            b = random.randint(0, 11)
            self.m_question[a], self.m_question[b] = self.m_question[b], self.m_question[a]
    def play_question(self):
        if self.q_status == self.QSTATUS_NO:
            return
        utils.play_note(4, mpd.notename_to_int(self.m_question[0]))
    def play_last_note(self):
        if self.q_status == self.QSTATUS_NO:
            return
        utils.play_note(4, mpd.notename_to_int(self.m_question[-1]))
    def play_all_notes(self):
        if self.q_status == self.QSTATUS_NO:
            return
        s = r"\staff{"
        for n in self.m_question:
            s = s + " " + n
        s = s + "}"
        utils.play_music(s, self.get_int('config/default_bpm'),
            self.get_int('config/preferred_instrument'),
            self.get_int('config/preferred_instrument_volume'))

class Gui(abstract.Gui):
    lesson_heading = _("Sing twelve random tones")
    def __init__(self, teacher):
        abstract.Gui.__init__(self, teacher, no_notebook=True)
        self.g_music_displayer = mpd.MusicDisplayer()
        self.g_music_displayer.clear()
        self.g_music_displayer.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.NEVER)
        self.practise_box.pack_start(self.g_music_displayer, True, True, 0)

        self.g_new = gu.bButton(self.action_area, _("_New"), self.new_question)
        self.g_play_first_note = gu.bButton(self.action_area, _("_Play first note"), lambda f, s=self: s.m_t.play_question())
        self.g_play_first_note.set_sensitive(False)
        self.g_play_last_note = gu.bButton(self.action_area, _("Play _last note"), lambda f, s=self: s.m_t.play_last_note())
        self.g_play_last_note.set_sensitive(False)
        self.g_play_all = gu.bButton(self.action_area, _("Play _all"), lambda f, s=self: s.m_t.play_all_notes())
        self.g_play_all.set_sensitive(False)
        self.practise_box.show_all()
    def new_question(self, widget=None):
        self.m_t.new_question()
        self.g_play_first_note.set_sensitive(True)
        self.g_play_last_note.set_sensitive(True)
        self.g_play_all.set_sensitive(True)
        try:
            self.m_t.play_question()
        except Exception,e:
            def cleanup():
                self.g_play_first_note.set_sensitive(False)
                self.g_play_last_note.set_sensitive(False)
                self.g_play_all.set_sensitive(False)
            if not self.standard_exception_handler(e, cleanup):
                raise
        s = r"\staff{"
        for n in self.m_t.m_question:
            s =  s + " " + n
        s = s + "}"
        self.g_music_displayer.display(s,
                                 self.get_int('config/feta_font_size=20'))
    def on_start_practise(self):
        super(Gui, self).on_start_practise()
        self.g_new.grab_focus()
        self.g_music_displayer.clear()
        self.handle_config_box_visibility()
    def on_end_practise(self):
        self.m_t.end_practise()
        self.g_play_first_note.set_sensitive(False)
        self.g_play_last_note.set_sensitive(False)
        self.g_play_all.set_sensitive(False)
