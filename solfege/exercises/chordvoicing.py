# GNU Solfege - free ear training software
# Copyright (C) 2000, 2001, 2002, 2003, 2004, 2005, 2007, 2008, 2011  Tom Cato Amundsen
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
from solfege import gu
from solfege import lessonfile
from solfege import mpd
from solfege import soundcard

class Teacher(abstract.Teacher):
    OK = 0
    ERR_PICKY = 1
    #UGH should we do this here
    def __init__(self, exname):
        abstract.Teacher.__init__(self, exname)
        self.lessonfileclass = lessonfile.QuestionsLessonfile
        for s in 'accidentals', 'key', 'semitones', 'atonal':
            self.m_lessonfile_defs[s] = s
    def new_question(self):
        """
        return 1 if the teacher has a question to ask
        UI will never call this function unless we have a usable lessonfile.
        """
        assert self.m_P
        if self.get_bool('config/picky_on_new_question') \
                 and not(self.q_status in (self.QSTATUS_VOICING_SOLVED, self.QSTATUS_NO)):
            return Teacher.ERR_PICKY

        self.m_P.select_random_question()
        self.q_status = self.QSTATUS_NEW
        return Teacher.OK
    def guess_chordtype(self, t):
        """
        return 1 if correct, None if not.
        This function will set self.q_status, and will raise an
        exception if the function is called with invalid value of
        q_status.

        Before we start: self.QSTATUS_NO
        After 'New' is clicked: self.QSTATUS_NEW

        if chordtype correct: self.QSTATUS_TYPE_SOLVED
        if chordtype wrong: self.QSTATUS_TYPE_WRONG

        if voicing correct self.QSTATUS_VOICING_SOLVED
        if voicing wrong: self.QSTATUS_VOICING_WRONG
        """
        if self.q_status in (self.QSTATUS_NEW, self.QSTATUS_TYPE_WRONG):
            if t == self.m_P.get_cname():
                self.q_status = self.QSTATUS_TYPE_SOLVED
                return 1
            else:
                self.q_status = self.QSTATUS_TYPE_WRONG
                return
    def guess_voicing(self, tones):
        """
        return 1 if correct, None if not.
        Gui should not call this function if the question is already solved.
        """
        v = self.m_P.get_music_as_notename_list('music')
        v.sort(mpd.compare_notenames)
        question_i = []
        for n in v:
            while n[-1] in ",'":
                n = n[:-1]
            question_i.append(mpd.notename_to_int(n))
        answer_i = []
        for n in tones:
            while n[-1] in ",'":
                n = n[:-1]
            answer_i.append(mpd.notename_to_int(n))
        if answer_i == question_i:
            self.q_status = self.QSTATUS_VOICING_SOLVED
            return 1
        self.q_status = self.QSTATUS_VOICING_WRONG
    def give_up(self):
        self.q_status = self.QSTATUS_VOICING_SOLVED

class Gui(abstract.LessonbasedGui):
    def __init__(self, teacher):
        abstract.LessonbasedGui.__init__(self, teacher)
        self.m_stacking_frame_min_height = 0

        ###############
        # practise_box
        ###############
        self.practise_box.set_spacing(gu.PAD)

        hbox = gu.bHBox(self.practise_box, True, True)
        hbox.set_spacing(gu.PAD)
        ##################
        # chordtype frame
        ##################
        frame = Gtk.Frame(label=_("Identify chord type"))
        hbox.pack_start(frame, True, True, 0)
        self.g_chordtype_box = Gtk.VBox()
        self.g_chordtype_box.set_border_width(gu.PAD_SMALL)
        frame.add(self.g_chordtype_box)

        #################
        # stacking frame
        #################
        self.g_stacking_frame = Gtk.Frame(label=_("Chord voicing"))
        self.g_stacking_frame.set_sensitive(False)
        hbox.pack_start(self.g_stacking_frame, True, True, 0)
        vbox = Gtk.VBox()
        vbox.set_border_width(gu.PAD_SMALL)
        self.g_stacking_frame.add(vbox)
        t = Gtk.Table(1, 1, 1)
        vbox.pack_start(t, True, True, 0)
        self.g_source = Gtk.VBox()
        t.attach(self.g_source, 0, 1, 0, 1, Gtk.AttachOptions.EXPAND|Gtk.AttachOptions.FILL)
        self.g_answer = Gtk.VBox()
        t.attach(self.g_answer, 1, 2, 0, 1, Gtk.AttachOptions.EXPAND|Gtk.AttachOptions.FILL)
        self.g_redo = Gtk.Button("<<<")
        self.g_redo.connect('clicked', lambda o, self=self: self.fill_stacking_frame())
        vbox.pack_end(self.g_redo, False, False, 0)

        self.g_flashbar = gu.FlashBar()
        self.practise_box.pack_start(self.g_flashbar, False, False, 0)

        self.std_buttons_add(('new-chord', self.new_question),
            ('repeat', lambda _o: self.m_t.m_P.play_question()),
            ('repeat_arpeggio', lambda _o: self.m_t.m_P.play_question_arpeggio()),
            ('give_up', lambda _o, self=self: self.give_up()))
        self.practise_box.show_all()
        ##############
        # config_box #
        ##############
        self.config_box.set_spacing(gu.PAD_SMALL)
        self.add_random_transpose_gui()
    def new_question(self, widget=None):
        def exception_cleanup():
            soundcard.synth.stop()
            self.std_buttons_exception_cleanup()
            self.m_t.q_status = self.QSTATUS_NO
        try:
            g = self.m_t.new_question()
            self.std_buttons_new_question()
            if g == Teacher.OK:
                self.std_buttons_new_question()
                self.clear_stacking_frame()
                self.g_stacking_frame.set_sensitive(False)
                for c in self.g_chordtype_box.get_children():
                    c.set_sensitive(True)
                self.m_t.m_P.play_question()
                self.g_flashbar.flash(_("Chord type"))
                self.g_chordtype_box.get_children()[0].grab_focus()
            elif g == Teacher.ERR_PICKY:
                self.g_flashbar.flash(_("You have to solve this question first."))
        except Exception, e:
            # This is one place where m_mpd_badcode might be set, since it will
            # be set if the exception is raisd by m_P.play_question(), but not
            # by select_random_question called by m_t.new_question()
            if isinstance(e, mpd.MpdException):
                if 'm_mpd_varname' not in dir(e):
                    e.m_mpd_varname = 'music'
                if 'm_mpd_badcode' not in dir(e):
                    e.m_mpd_badcode = self.m_t.m_P.get_question()['music'].get_err_context(e, self)
            if not self.standard_exception_handler(e, exception_cleanup):
                raise
    def clear_stacking_frame(self):
        for c in self.g_source.get_children() + self.g_answer.get_children():
            c.destroy()
    def fill_stacking_frame(self):
        """
        Create the buttons in stacking frame.
        """
        self.g_redo.set_sensitive(True)
        self.g_stacking_frame.set_sensitive(True)
        self.m_answer = []
        self.clear_stacking_frame()
        v = self.m_t.m_P.get_music_as_notename_list('music')
        v.sort()
        for n in v:
            nn = mpd.MusicalPitch.new_from_notename(n)
            b = Gtk.Button(nn.get_user_notename())
            b.connect('clicked', self.on_notebutton_clicked, nn.get_notename(), nn.get_user_notename())
            self.g_source.pack_end(b, False, False, 0)
            b.show()
        self.g_source.get_children()[0].grab_focus()
    def give_up(self, v=None):
        self.m_t.give_up()
        self.std_buttons_give_up()
        self.set_chordtype_frame_status_solved(self.m_t.m_P.get_cname())
        self.clear_stacking_frame()
        self.g_stacking_frame.set_sensitive(True)
        self.g_redo.set_sensitive(False)
        self.show_music()
    def on_chordtype_right_clicked(self, button, event, t):
        if event.button != 3:
            return
        if self.m_t.m_P and not self.m_t.m_P.header.enable_right_click:
            self.g_flashbar.flash(_("Right click is not allowed for this lesson file."))
            return
        if self.m_t.q_status == self.QSTATUS_NO:
            self.g_flashbar.flash(_("Click 'New chord' to begin."))
            return
        if self.m_t.q_status == self.QSTATUS_NEW:
            self.g_flashbar.flash(_("You should try to guess before right-clicking."))
            return
        if not self.m_t.m_P.has_question():
            return
        try:
            # We try first with the 'set' variable, as this is what is closest
            if 'set' in self.m_t.m_P.get_question():
                for idx, question in enumerate(self.m_t.m_P.m_questions):
                    if question.set == self.m_t.m_P.get_question().set \
                            and question.name.cval == t:
                        self.m_t.m_P.play_question(question)
                        return
            #
            for idx, question in enumerate(self.m_t.m_P.m_questions):
                if question.name.cval == button.m_chordtype:
                    self.m_t.m_P.play_question(question)
                    return
        except Exception, e:
            if not self.standard_exception_handler(e):
                raise
    def on_chordtype_clicked(self, btn, t):
        if self.m_t.q_status == self.QSTATUS_NO:
            self.g_flashbar.flash(_("Click 'New chord' to begin."))
        elif self.m_t.q_status in (self.QSTATUS_NEW, self.QSTATUS_TYPE_WRONG):
            g = self.m_t.guess_chordtype(t)
            if g:
                self.g_flashbar.flash(_("Correct, now stack the tones"))
                self.set_chordtype_frame_status_solved(t)
                self.fill_stacking_frame()
            else:
                self.g_flashbar.flash(_("Wrong"))
        elif self.m_t.q_status in (self.QSTATUS_TYPE_SOLVED, self.QSTATUS_VOICING_WRONG):
            self.g_flashbar.flash(_("Type is already solved, now specify voicing."))
    def on_notebutton_clicked(self, btn, n, user_notename):
        newb = Gtk.Button(user_notename)
        newb.show()
        btn.destroy()
        self.m_answer.append(n)
        self.g_answer.pack_end(newb, False, False, 0)
        if not self.g_source.get_children():
            # no children mean that the user has finished answering
            if self.m_t.guess_voicing(self.m_answer):
                self.g_flashbar.flash(_("Correct"))
                self.show_music()
                self.std_buttons_answer_correct()
                self.g_redo.set_sensitive(False)
            else:
                self.g_flashbar.flash(_("Wrong"))
                self.std_buttons_answer_wrong()
                self.g_redo.grab_focus()
        else:
            self.g_source.get_children()[0].grab_focus()
    def show_music(self):
        self.clear_stacking_frame()
        md = mpd.MusicDisplayer()
        self.g_source.pack_start(md, True, True, 0)
        md.show()
        md.display(r"\staff{ \clef %s < %s >}" % (
                mpd.select_clef(self.m_t.m_P.get_music_as_notename_string('music')),
                self.m_t.m_P.get_music_as_notename_string('music')), 20)
        # display the notenames on the buttons with octave info
        v = self.m_t.m_P.get_music_as_notename_list('music')
        v.sort(mpd.compare_notenames)
        for n in v:
            b = Gtk.Button(mpd.MusicalPitch.new_from_notename(n).get_user_octave_notename())
            b.get_children()[0].set_use_markup(1)
            b.show()
            self.g_answer.pack_end(b, False, False, 0)
    def fill_chordtype_box(self):
        for x in self.g_chordtype_box.get_children():
            x.destroy()
        for name in [q.name for q in self.m_t.m_P.iterate_questions_with_unique_names()]:
            b = Gtk.Button(name)
            b.m_chordtype = name.cval
            self.g_chordtype_box.pack_start(b, False, False, 0)
            b.connect('clicked', self.on_chordtype_clicked, name.cval)
            b.connect('button_release_event', self.on_chordtype_right_clicked, name)
            b.show()
    def set_chordtype_frame_status_solved(self, t):
        for c in self.g_chordtype_box.get_children():
            c.set_sensitive(c.m_chordtype == t)
    def on_start_practise(self):
        super(Gui, self).on_start_practise()
        self.g_random_transpose.set_text(str(self.m_t.m_P.header.random_transpose))
        self.std_buttons_start_practise()
        self.g_flashbar.require_size([
            _("You have to solve this question first."),
            _("Type is already solved, now specify voicing."),
        ])
        self.g_flashbar.delayed_flash(self.short_delay,
            _("Click 'New chord' to begin."))
        self.fill_chordtype_box()
        self.clear_stacking_frame()
        self.g_stacking_frame.set_sensitive(False)
    def on_end_practise(self):
        self.m_t.end_practise()
        self.std_buttons_end_practise()
