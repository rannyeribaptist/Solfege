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

from gi.repository import Gtk

from solfege import abstract
from solfege import cfg
from solfege import gu
from solfege import lessonfile
from solfege import mpd
from solfege import soundcard
from solfege import utils
from solfege.mpd import Rat

import solfege

class Teacher(abstract.Teacher):
    """
    The Teacher and Gui for dictation abuses q_status a little.
    QSTATUS_NEW mean that the lessonfile is ok.
    QSTATUS_NO mean that the question is corrupt and unusable. Other
               questions in the same file might be useable.
    """
    def __init__(self, exname):
        abstract.Teacher.__init__(self, exname)
        self.lessonfileclass = lessonfile.DictationLessonfile

class Gui(abstract.LessonbasedGui):
    def __init__(self, teacher):
        abstract.LessonbasedGui.__init__(self, teacher, no_notebook=False)
        ################
        # practise_box #
        ################
        self.g_question_title = gu.bLabel(self.practise_box, "", False, False)

        self.g_music_displayer = mpd.MusicDisplayer()
        self.set_size_request(500, -1)
        self.g_music_displayer.show()
        self.practise_box.pack_start(self.g_music_displayer, True, True, 0)
        ###############
        # action_area #
        ###############
        self.g_partbox = gu.bHBox(self.practise_box, False)
        self.g_go_back = Gtk.Button(stock='gtk-go-back')
        self.g_go_back.connect('clicked', self.select_previous)
        self.g_go_back.show()
        self.action_area.pack_start(self.g_go_back, False, False, 0)
        self.g_go_forward = Gtk.Button(stock='gtk-go-forward')
        self.g_go_forward.show()
        self.g_go_forward.connect('clicked', self.select_next)
        self.action_area.pack_start(self.g_go_forward, False, False, 0)
        self.g_play = gu.bButton(self.action_area, _("_Play the whole music"),
                                 self.play)
        self.g_show = gu.bButton(self.action_area, _("_Show"), self.show_answer)
    def exception_cleanup(self):
        """ cleanup function after exception caught in select_previous
        and select_next
        """
        soundcard.synth.stop()
        self.m_t.q_status = self.QSTATUS_NO
        self.g_play.set_sensitive(False)
        self.g_show.set_sensitive(False)
        self.g_music_displayer.clear()
    def select_previous(self, widget):
        self.m_t.m_P.select_previous()
        try:
            self.display_start_of_music()
        except Exception, e:
            if not self.standard_exception_handler(e, self.exception_cleanup):
                raise
        else:
            self.m_t.q_status = self.QSTATUS_NEW
            self.g_play.set_sensitive(True)
            self.g_show.set_sensitive(True)
        self._update()
    def select_next(self, widget):
        self.m_t.m_P.select_next()
        try:
            self.display_start_of_music()
        except Exception, e:
            if not self.standard_exception_handler(e, self.exception_cleanup):
                raise
        else:
            self.m_t.q_status = self.QSTATUS_NEW
            self.g_play.set_sensitive(True)
            self.g_show.set_sensitive(True)
        self._update()
    def play(self, widget=None):
        # see Teacher docstring.
        if self.m_t.q_status != self.QSTATUS_NEW:
            return
        try:
            self.m_t.m_P.play_question()
        except Exception, e:
            if not self.standard_exception_handler(e, soundcard.synth.stop):
                raise
    def on_end_practise(self):
        self.m_t.end_practise()
    def show_answer(self, widget=None):
        # see Teacher docstring.
        if self.m_t.q_status != self.QSTATUS_NEW:
            return
        try:
            self.g_music_displayer.display(self.m_t.m_P.get_music(),
                            self.get_int('config/feta_font_size=20'))
        except Exception, e:
            if not self.standard_exception_handler(e):
                raise
    def _update(self):
        """
        Updates the buttons above the action_area where you have
        one or more buttons with a small note pixmap on. Each of the
        buttons will play one part of the music in the question.
        """
        # tmp func used as callback function
        def f(w, start, end, self=self):
            try:
                utils.play_music(self.m_t.m_P.get_music(),
                    self.m_t.m_P.get_tempo(),
                    cfg.get_int('config/preferred_instrument'),
                    cfg.get_int('config/preferred_instrument_volume'),
                    start, end)
            except Exception, e:
                if not self.standard_exception_handler(e, soundcard.synth.stop):
                    raise
        for i in self.g_partbox.get_children():
            i.destroy()
        # if the lessonfile was invalid, m_P could be None
        if self.m_t.m_P and self.m_t.m_P.m_questions:
            if 'name' in self.m_t.m_P.get_question():
                self.g_question_title.set_text(self.m_t.m_P.get_name())
            else:
                self.g_question_title.set_text("")
            v = self.m_t.m_P.get_breakpoints()
            if v == []:
                # we display one button that will play the whole music if
                # there are not breakpoints in the music
                btn = self.create_pixmap_button()
                btn.connect('clicked', f, None, None)
                btn.show()
                self.g_partbox.pack_start(btn, True, True, 0)
                return
            tmp = [Rat(0, 1)] + v + [Rat(2**30, 1)]
            for i in range(len(tmp) - 1):
                btn = self.create_pixmap_button()
                btn.show()
                btn.connect('clicked', f, tmp[i], tmp[i+1])
                self.g_partbox.pack_start(btn, True, True, 0)
        # q_status is QSTATUS_NO if the question is invalid (from the lessonfile)
        if self.m_t.q_status == self.QSTATUS_NO:
            self.g_partbox.set_sensitive(False)
        else:
            self.g_partbox.set_sensitive(True)
    def display_start_of_music(self):
        """
        Callers must catch exceptions.
        """
        fontsize = self.get_int('config/feta_font_size=20')
        try:
            if self.m_t.m_P.get_clue_music():
                self.g_music_displayer.display(self.m_t.m_P.get_clue_music().get_mpd_music_string(self.m_t.m_P), fontsize)
            elif self.m_t.m_P.get_clue_end():
                self.g_music_displayer.display(self.m_t.m_P.get_music(),
                            fontsize, self.m_t.m_P.get_clue_end())
            else:
                self.g_music_displayer.display(self.m_t.m_P.get_music(),
                            fontsize, Rat(0, 1))
        except mpd.MpdException, e:
            if self.m_t.m_P.get_clue_music():
                e.m_mpd_varname = 'clue_music'
            else:
                e.m_mpd_varname = 'music'
            self.m_t.m_P.get_question()['music'].complete_to_musicdata_coords(self.m_t.m_P, e)
            if 'm_mpd_badcode' not in dir(e):
                e.m_mpd_badcode = self.m_t.m_P.get_question()[e.m_mpd_varname].get_err_context(e, self.m_t.m_P)
            raise
    def update_gui_after_lessonfile_change(self):
        self.m_t.q_status = self.QSTATUS_NEW
        if not self.m_t.m_P.m_questions:
            solfege.win.display_error_message(_("The lesson file '%s' contains no questions.") % self.m_t.m_lessonfile)
            self.g_play.set_sensitive(False)
            self.g_show.set_sensitive(False)
            self.g_go_back.set_sensitive(False)
            self.g_go_forward.set_sensitive(False)
            self._update()
            return
        else:
            self.g_go_forward.set_sensitive(True)
            self.g_go_back.set_sensitive(True)
        self.m_t.m_P.select_first()
        self.action_area.set_sensitive(True)
        try:
            self.display_start_of_music()
        except Exception, e:
            def cleanup_function():
                self.m_t.q_status = self.QSTATUS_NO
                self.g_play.set_sensitive(False)
                self.g_show.set_sensitive(False)
                self.g_music_displayer.clear()
            if not self.standard_exception_handler(e, cleanup_function):
                raise
        else:
            self.g_play.set_sensitive(True)
            self.g_show.set_sensitive(True)
        self._update()
    def create_pixmap_button(self):
        im = Gtk.Image()
        im.set_from_stock("solfege-rhythm-c4", Gtk.IconSize.LARGE_TOOLBAR)
        im.show()
        btn = Gtk.Button()
        btn.add(im)
        return btn
    def on_start_practise(self):
        super(Gui, self).on_start_practise()
        self.update_gui_after_lessonfile_change()
        self.g_play.grab_focus()

