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
from solfege.specialwidgets import QuestionNameCheckButtonTable

class Teacher(abstract.Teacher):
    OK = 0
    ERR_PICKY = 1
    # valid values for self.q_status:
    # QSTATUS_NO       at program startup
    # QSTATUS_NEW      after the new button has been pressed
    # QSTATUS_SOLVED   when all three questions have been answered
    # QSTATUS_GIVE_UP  after 'Give Up' has been pressed.
    CORRECT = 1
    ALL_CORRECT = 2
    def __init__(self, exname):
        abstract.Teacher.__init__(self, exname)
        self.lessonfileclass = lessonfile.ChordLessonfile
        for s in 'accidentals', 'key', 'semitones', 'atonal':
            self.m_lessonfile_defs[s] = s
    def new_question(self):
        """
        return OK or ERR_PICKY
        UI will never call this function unless we have a usable lessonfile.
        """
        assert self.m_P
        if self.get_bool('config/picky_on_new_question') \
           and (not self.q_status in (self.QSTATUS_NO, self.QSTATUS_SOLVED,
                                      self.QSTATUS_GIVE_UP)):
            return self.ERR_PICKY
        self.m_P.select_random_question()
        self.m_solved = {}.fromkeys(self.m_P.m_props.keys(), False)
        self.q_status = self.QSTATUS_NEW
        return self.OK
    def give_up(self):
        self.q_status = self.QSTATUS_GIVE_UP
    def guess_property(self, property_name, value):
        """
        GUI guarantees that this method will not be called after it has
        been guessed correct once.

        return 0 if this was wrong guess.
        return CORRECT if this question is correct.
        return ALL_CORRECT if all parts of the question is correct.
        """
        assert self.q_status == self.QSTATUS_NEW
        if value == self.m_P.get_question()[property_name].cval:
            self.m_solved[property_name] = True
            if False not in self.m_solved.values():
                self.q_status = self.QSTATUS_SOLVED
                return self.ALL_CORRECT
            return self.CORRECT
        else:
            return 0


class Gui(abstract.LessonbasedGui):
    def __init__(self, teacher):
        abstract.LessonbasedGui.__init__(self, teacher)
        ################
        # practise_box #
        ################
        self.add_module_is_deprecated_label()
        self.g_hbox = hbox = gu.bHBox(self.practise_box)
        hbox.set_spacing(gu.PAD)
        spacebox = Gtk.HBox()
        hbox.pack_start(spacebox, True, True, 0)

        self.g_music_displayer = mpd.MusicDisplayer()
        self.g_music_displayer.set_size_request(100, -1)
        hbox.pack_start(self.g_music_displayer, False, False, 0)
        spacebox = Gtk.HBox()
        hbox.pack_start(spacebox, True, True, 0)
        self.g_flashbar = gu.FlashBar()
        self.practise_box.pack_start(self.g_flashbar, False, False, 0)

        self.g_new = gu.bButton(self.action_area, _("_New chord"),
                                self.new_question)
        self.g_repeat = gu.bButton(self.action_area, _("_Repeat"),
              lambda w: self.run_exception_handled(self.m_t.m_P.play_question))
        self.g_repeat_arpeggio = gu.bButton(self.action_area,
              _("Repeat _arpeggio"),
              lambda w: self.run_exception_handled(self.m_t.m_P.play_question_arpeggio))
        self.g_give_up = gu.bButton(self.action_area, _("_Give up"),
                                    self.give_up)
        self.practise_box.show_all()
        ##############
        # config_box #
        ##############
        self.config_box.set_spacing(gu.PAD_SMALL)
        self.add_random_transpose_gui()
        # -----------------------------------------
        self.g_select_questions_category_box, category_box= gu.hig_category_vbox(
            _("Chord types to ask"))
        self.config_box.pack_start(self.g_select_questions_category_box, True, True, 0)
        self.g_select_questions = QuestionNameCheckButtonTable(self.m_t)
        self.g_select_questions.initialize(4, 0)
        category_box.pack_start(self.g_select_questions, False, False, 0)
        self.g_select_questions.show()
    def update_select_question_buttons(self):
        """
        The g_select_questions widget is used in m_custom_mode to select which
        questions to ask. This method will show and update the widget
        to the current lesson file if we are in m_custom_mode. If not, it
        will hide the widget.
        """
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
    def update_answer_buttons(self, obj=None):
        """
        Only columns with question properties that are actually used
        in the lesson file will be displayed. This way, we can make a default
        configuration:
         qprops = "name", "toptone", "inversion"
         qprop_labels = _("Name"), _("Toptone"), _("Inversion")
        and only lesson files that require other properties have to define
        these two variables.
        """
        # This part will create the table with the buttons used to answer.
        try:
            self.g_atable.destroy()
        except AttributeError:
            pass
        self.g_atable = Gtk.Table()
        self.g_atable.show()
        self.g_hbox.pack_start(self.g_atable, False, False, 0)
        self.g_hbox.reorder_child(self.g_atable, 1)
        # pprops say how many properties are we going to display.
        # We will not display a property if no questions use it.
        num_used_props = len(
            [x for x in self.m_t.m_P.m_props.keys() if self.m_t.m_P.m_props[x]])
        # tcols say how many columns we need. We need a column for each
        # column separator
        tcols = num_used_props * 2 - 1
        trows = max([len(x) for x in self.m_t.m_P.m_props.values()]) + 2
        # The column headings
        for idx, label in enumerate(self.m_t.m_P.header.qprop_labels):
            self.g_atable.attach(Gtk.Label(label=label), idx * 2, idx * 2 + 1, 0, 1,
                                 xoptions=Gtk.AttachOptions.FILL, yoptions=Gtk.AttachOptions.SHRINK,
                                 xpadding=gu.PAD_SMALL)
        # Then we create the buttons used to answer.
        for x, prop in enumerate(self.m_t.m_P.header.qprops):
            for y, proplabel in enumerate(self.m_t.m_P.m_props[prop]):
                button = Gtk.Button(unicode(proplabel))
                button.m_property_name = prop
                button.m_property_value = proplabel.cval
                button.connect('clicked', self.on_prop_button_clicked)
                button.connect('button_release_event', self.on_prop_button_right_clicked)
                self.g_atable.attach(button, x * 2, x * 2 + 1, y + 2, y + 3,
                    xpadding=gu.PAD_SMALL,
                    yoptions=Gtk.AttachOptions.SHRINK)
        # The separator below the column headings
        self.g_atable.attach(Gtk.HSeparator(), 0, tcols, 1, 2,
            xoptions=Gtk.AttachOptions.FILL, yoptions=Gtk.AttachOptions.FILL,
            xpadding=0, ypadding=gu.PAD_SMALL)
        # The vertical separator between columns
        for idx in range(len(self.m_t.m_P.header.qprops)-1):
            self.g_atable.attach(Gtk.VSeparator(),
            idx * 2 + 1, idx * 2 + 2, 0, trows,
            xoptions=Gtk.AttachOptions.FILL, yoptions=Gtk.AttachOptions.FILL,
            xpadding=0, ypadding=gu.PAD_SMALL)
        self.g_atable.show_all()
        #
        self.g_random_transpose.set_text(str(self.m_t.m_P.header.random_transpose))
        self.g_repeat.set_sensitive(False)
        self.g_repeat_arpeggio.set_sensitive(False)
        self.g_give_up.set_sensitive(False)
    def update_gui_after_lessonfile_change(self):
        self.g_music_displayer.clear()
        self.update_select_question_buttons()
        if self.m_t.m_P.header.lesson_heading:
            self.set_lesson_heading(self.m_t.m_P.header.lesson_heading)
        else:
            self.set_lesson_heading(_("Identify the chord"))
        self.g_new.set_sensitive(True)
        self.update_answer_buttons()
    def on_prop_button_clicked(self, button):
        if self.m_t.q_status != self.QSTATUS_NEW:
            return
        g = self.m_t.guess_property(button.m_property_name,
                                    button.m_property_value)
        if g:
            self.g_flashbar.flash(_("Correct"))
            for btn in self.g_atable.get_children():
                if isinstance(btn, Gtk.Button):
                    if btn.m_property_name == button.m_property_name \
                    and btn.m_property_value == button.m_property_value:
                        btn.get_children()[0].set_name("BoldText")
                        break
            if g == self.m_t.ALL_CORRECT:
                self.all_guessed_correct()
        else:
            self.g_flashbar.flash(_("Wrong"))
    def on_prop_button_right_clicked(self, button, event):
        """
        Search for a question in the lesson file with the same properties
        as the question being asked, but with the one property changed to
        be the property right-clicked on. Do nothing if no matching question
        is found.
        """
        if event.button != 3:
            return
        if not self.m_t.m_P.has_question():
            return
        if not self.m_t.m_P.header.enable_right_click:
            self.g_flashbar.flash(_("Right click is not allowed for this lesson file."))
            return
        d = {}
        for k in self.m_t.m_P.header.qprops:
            d[k] = self.m_t.m_P.get_question()[k].cval
        # replace one property with the one we right clicked
        d[button.m_property_name] = button.m_property_value
        for idx, question in enumerate(self.m_t.m_P.m_questions):
            match = True
            for k in d:
                if d[k] != question[k].cval:
                    match = False
            if match:
                try:
                    self.m_t.m_P.play_question(question)
                except Exception, e:
                    if not self.standard_exception_handler(e):
                        raise
                return
    def all_guessed_correct(self):
        self.run_exception_handled(self.show_answer)
        self.g_new.set_sensitive(True)
        self.g_new.grab_focus()
        self.g_give_up.set_sensitive(False)
    def new_question(self, widget=None):
        def exception_cleanup():
            soundcard.synth.stop()
            self.g_give_up.set_sensitive(False)
            self.g_repeat.set_sensitive(False)
            self.g_repeat_arpeggio.set_sensitive(False)
            self.m_t.q_status = self.QSTATUS_NO
        # make sure all buttons are sensitive.
        for x in self.g_atable.get_children():
            if isinstance(x, Gtk.Button):
                # Set name to "" to make all labels not have bold text.
                x.get_children()[0].set_name("")
        ##
        try:
            n = self.m_t.new_question()
            if n != Teacher.ERR_PICKY:
                self.g_music_displayer.clear()
                self.m_t.m_P.play_question()
                self.g_give_up.set_sensitive(True)
                self.g_repeat.set_sensitive(True)
                if self.get_bool('config/picky_on_new_question'):
                    self.g_new.set_sensitive(False)
                if isinstance(self.m_t.m_P.get_question().music, lessonfile.ChordCommon):
                    self.g_repeat_arpeggio.set_sensitive(True)
                else:
                    self.g_repeat_arpeggio.set_sensitive(False)
                [btn for btn in self.g_atable.get_children() if isinstance(btn, Gtk.Button)][-1].grab_focus()
        except Exception, e:
            if not self.standard_exception_handler(e, exception_cleanup):
                raise
    def on_start_practise(self):
        self.m_t.m_custom_mode = self.get_bool('gui/expert_mode')
        for question in self.m_t.m_P.m_questions:
            question.active = 1
        self.update_gui_after_lessonfile_change()
        self.set_deprecation_text("chord", "idproperty", self.m_t.m_P.m_filename)
        self.g_flashbar.require_size([
            _("Click 'New chord' to begin."),
            "XXXX, root position, toptone: 5",
        ])
        self.g_new.grab_focus()
        self.g_flashbar.delayed_flash(self.short_delay,
            _("Click 'New chord' to begin."))
    def on_end_practise(self):
        self.m_t.end_practise()
        self.g_music_displayer.clear()
        self.g_new.set_sensitive(True)
        self.g_repeat.set_sensitive(False)
        self.g_repeat_arpeggio.set_sensitive(False)
        self.g_give_up.set_sensitive(False)
    def give_up(self, widget=None):
        if self.m_t.q_status == self.QSTATUS_NEW:
            self.m_t.give_up()
            self.run_exception_handled(self.show_answer)
            self.g_new.set_sensitive(True)
            self.g_give_up.set_sensitive(False)
            for button in self.g_atable.get_children():
                if isinstance(button, Gtk.Button):
                    if button.m_property_value == self.m_t.m_P.get_question()[button.m_property_name].cval:
                        button.get_children()[0].set_name('BoldText')
                    else:
                        button.get_children()[0].set_name('')
    def show_answer(self):
        """
        Show the answer in the music displayer. All callers must check
        for exceptions.
        """
        fontsize = self.get_int('config/feta_font_size=20')
        if isinstance(self.m_t.m_P.get_question().music, lessonfile.Chord):
            clef = mpd.select_clef(self.m_t.m_P.get_music_as_notename_string('music'))
            # Here we don't check for exceptions since the music is always
            # tested by the code that plays the question. Maybe we should,
            # just in case this changes?
            self.g_music_displayer.display(r"\staff{\clef %s <%s>}" % (clef, self.m_t.m_P.get_music_as_notename_string('music')), fontsize)
        else:
            # Same as the comment above applies here too.
            self.g_music_displayer.display(self.m_t.m_P.get_music(), fontsize)

