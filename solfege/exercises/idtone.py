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
import os

from gi.repository import GObject
from gi.repository import Gtk

from solfege import abstract
from solfege import gu
from solfege import inputwidgets
from solfege import lessonfile
from solfege import mpd
from solfege import soundcard
from solfege import statistics, statisticsviewer
from solfege import utils

import solfege

class Teacher(abstract.Teacher):
    #FIXME the following lines
    OK, ERR_PICKY, ERR_TONES = range(3)
    ERR_PICKY = 1
    ERR_CONFIG = 2
    OCTAVES = [-2, -1, 0, 1, 2, 3]
    def __init__(self, exname):
        abstract.Teacher.__init__(self, exname)
        self.lessonfileclass = lessonfile.HeaderLessonfile
        self.m_statistics = statistics.IdToneStatistics(self)
        self.m_ask_tones =   {}
        self.m_question = None
        self.m_custom_mode = False
    def new_question(self):
        """
        Return values:
        OK: sucess, new random tone selected
        ERR_PICKY: fail, you are not allowed to select a new tone before you
                   can identify the one you have now.
        ERR_CONFIG: fail, all notes have zero weight or no octaves selected
        """
        if self.m_timeout_handle:
            GObject.source_remove(self.m_timeout_handle)
            self.m_timeout_handle = None

        if self.get_bool('config/picky_on_new_question') \
                and self.q_status in (self.QSTATUS_NEW, self.QSTATUS_WRONG):
            return Teacher.ERR_PICKY

        self.m_is_first_question = self.q_status == self.QSTATUS_NO

        v = []
        for n in mpd.MusicalPitch.notenames:
            v.extend([n] * self.get_int(n+"_weight"))
        if not v:
            return self.ERR_CONFIG
        self.m_question = random.choice(v)
        v = []
        for n in self.OCTAVES:
            if self.get_bool("octave"+str(n)):
                v.append(n)
        if not v:
            return self.ERR_CONFIG
        self.m_octave = random.choice(v)
        self.q_status = self.QSTATUS_NEW
        return self.OK
    def guess_answer(self, notename):
        if notename == self.m_question:
            if self.q_status == self.QSTATUS_NEW:
                self.m_statistics.add_correct(notename)
            self.maybe_auto_new_question()
            self.q_status = self.QSTATUS_SOLVED
            return 1
        else:
            if self.q_status == self.QSTATUS_NEW:
                self.m_statistics.add_wrong(self.m_question, notename)
                self.q_status = self.QSTATUS_WRONG
    def play_question(self):
        if self.q_status == self.QSTATUS_NO:
            return
        utils.play_note(4,
            mpd.notename_to_int(self.m_question) + self.m_octave * 12)
    def give_up(self):
        self.q_status = self.QSTATUS_GIVE_UP
    def spank_me_play_question(self):
        t1 = utils.new_percussion_track()
        t1.note(8, 71)
        t2 = utils.new_track()
        t2.notelen_time(4)
        t2.note(4, mpd.notename_to_int(self.m_question)+self.m_octave*12)
        soundcard.synth.play_track(t1, t2)
    def spank_me(self):
        utils.play_perc(4, 71)

class Gui(abstract.Gui):
    def __init__(self, teacher):
        abstract.Gui.__init__(self, teacher)

        self.g_percentage = gu.bLabel(self.practise_box, "")
        self.g_percentage.set_name("Heading1")
        self.g_piano = inputwidgets.PianoOctaveWithAccelName(
                       self.on_answer_from_user, self.get_accel_key_list())
        self.g_piano.m_visible_accels = not self.get_bool('hide_piano_accels')
        def update_accels(*ignore):
            self.g_piano.m_keys = self.get_accel_key_list()
            self.g_piano.queue_draw()
        for notename in mpd.MusicalPitch.notenames:
            self.add_watch('tone_%s_ak' % notename, update_accels)
        self.practise_box.pack_start(self.g_piano, True, True, 0)

        self.g_flashbar = gu.FlashBar()
        self.g_flashbar.show()
        self.practise_box.pack_start(self.g_flashbar, False, False, 0)
        self.practise_box.set_spacing(gu.PAD)

        self.std_buttons_add(
            ('new-tone', self.new_question),
            ('repeat', lambda _o, self=self: self.m_t.play_question()),
            ('give_up', self.give_up))
        self.practise_box.show_all()
        ##############
        # config_box #
        ##############
        self.config_box.set_spacing(gu.PAD_SMALL)
        self.g_config_elems = gu.bVBox(self.config_box, False)
        table = Gtk.Table()
        table.set_border_width(gu.PAD_SMALL)
        frame = Gtk.Frame(label=_("Weight"))
        self.g_config_elems.pack_start(frame, False, False, 0)
        frame.add(table)
        for x, n in [(1, 'cis'), (3, 'dis'), (7, 'fis'),
                     (9, 'gis'), (11, 'ais')]:
            label = Gtk.Label(label=mpd.MusicalPitch.new_from_notename(n).get_user_notename())
            label.set_name("Heading2")
            label.set_alignment(0.2, 1.0)
            table.attach(label, x, x+2, 0, 1, xoptions=Gtk.AttachOptions.FILL)
            b = gu.nSpinButton(self.m_exname, n+"_weight",
                      Gtk.Adjustment(1, 0, 1000, 1, 10), digits=0)
            table.attach(b, x, x+2, 1, 2, xoptions=Gtk.AttachOptions.FILL)
        for x, n in [(0, 'c'), (2, 'd'), (4, 'e'), (6, 'f'),
                      (8, 'g'), (10, 'a'), (12, 'b')]:
            label = Gtk.Label(label=mpd.MusicalPitch.new_from_notename(n).get_user_notename())
            label.set_name("Heading2")
            label.set_alignment(0.35, 1.0)
            table.attach(label, x, x+2, 2, 3, xoptions=Gtk.AttachOptions.FILL)
            b = gu.nSpinButton(self.m_exname, n+"_weight",
                   Gtk.Adjustment(1, 0, 1000, 1, 10), digits=0)
            table.attach(b, x, x+2, 3, 4, xoptions=Gtk.AttachOptions.FILL)

        hbox = gu.bHBox(self.g_config_elems, False)
        hbox.pack_start(Gtk.Label(_("Octave:")), False, False, padding=4)
        for oct in self.m_t.OCTAVES:
            b = gu.nCheckButton(self.m_exname, "octave"+str(oct), str(oct),
                                default_value=1)
            hbox.pack_start(b, False, False, 0)
        #############
        self._add_auto_new_question_gui(self.config_box)
        #############
        b = gu.nCheckButton('idtone', 'hide_piano_accels', _("Hide _piano keyboard shortcuts"), False)
        def show_hide_accels(checkbutton):
            self.g_piano.m_visible_accels = not b.get_active()
        b.connect('clicked', show_hide_accels)
        self.config_box.pack_start(b, False, False, 0)
        #
        frame = Gtk.Frame(label=_("When you guess wrong"))
        vbox = Gtk.VBox()
        vbox.set_border_width(gu.PAD_SMALL)
        frame.add(vbox)
        vbox.pack_start(gu.nCheckButton(self.m_exname,
                    "warning_sound", _("Play warning sound")), False, False, 0)
        self.config_box.pack_start(frame, False, False, 0)
        self.config_box.show_all()
        ##############
        # statistics #
        ##############
        self.setup_statisticsviewer(statisticsviewer.StatisticsViewer,
                                   _("Identify tone"))
    def get_accel_key_list(self):
        v = []
        for k in mpd.MusicalPitch.notenames:
            self.m_key_bindings['tone_%s_ak' % k] \
                = lambda self=self, k=k: self.on_answer_from_user(k)
            v.append(self.get_string('tone_%s_ak' % k))
        return v
    def new_question(self, widget=None):
        s = self.m_t.q_status
        g = self.m_t.new_question()
        if g == Teacher.ERR_CONFIG:
            solfege.win.display_error_message(
_("""You have to select some tones practise. Do this on the config page by setting the weight of tones to a value greater than zero."""))
            return
        elif g == Teacher.OK:
            self.std_buttons_new_question()
            try:
                if self.m_t.m_is_first_question:
                    self.flash_and_play_first_tone()
                else:
                    self.g_flashbar.clear()
                    self.m_t.play_question()
            except Exception,e:
                def cleanup():
                    self.std_buttons_exception_cleanup()
                if not self.standard_exception_handler(e, cleanup):
                    raise
        self.set_percentage_label()
    def flash_and_play_first_tone(self):
        self.g_flashbar.flash(_("First tone is %s") % mpd.MusicalPitch.new_from_notename(self.m_t.m_question).get_user_notename())
        self.m_t.play_question()
    def on_answer_from_user(self, notename):
        if self.m_t.q_status == self.QSTATUS_NO:
            self.g_flashbar.flash(_("Click 'New tone' to begin."))
            return
        elif self.m_t.q_status == self.QSTATUS_SOLVED:
            if self.m_t.guess_answer(notename):
                self.g_flashbar.flash(_("Correct, but you have already solved this question"))
            else:
                self.g_flashbar.flash(_("Wrong, but you have already solved this question"))
        elif self.m_t.q_status in (self.QSTATUS_NEW, self.QSTATUS_WRONG):
            if self.m_t.guess_answer(notename):
                self.g_flashbar.flash(_("Correct"))
                self.std_buttons_answer_correct()
            else:
                try:
                    if self.m_t.m_is_first_question:
                        self.flash_and_play_first_tone()
                        return
                    self.g_flashbar.flash(_("Wrong"))
                    self.std_buttons_answer_wrong()
                    if self.get_bool("warning_sound"):
                        if self.get_bool("config/auto_repeat_question_if_wrong_answer"):
                            self.m_t.spank_me_play_question()
                        else:
                            self.m_t.spank_me()
                    else:
                        if self.get_bool("config/auto_repeat_question_if_wrong_answer"):
                            self.m_t.play_question()
                except Exception, e:
                    if not self.standard_exception_handler(e):
                        raise
        self.set_percentage_label()
    def give_up(self, _o=None):
        if self.m_t.q_status == self.QSTATUS_WRONG:
            self.g_flashbar.push(_("The answer is: %s")
                % mpd.MusicalPitch.new_from_notename(self.m_t.m_question).get_user_notename())
            self.m_t.give_up()
            self.std_buttons_give_up()
    def set_percentage_label(self):
        self.g_percentage.set_text("%.1f %%" % (self.m_t.m_statistics.get_percentage_correct()))
    def on_start_practise(self):
        self.m_t.m_custom_mode = not (
                ('white_keys_weight' in self.m_t.m_P.header)
                 or ('black_keys_weight' in self.m_t.m_P.header))
        super(Gui, self).on_start_practise()
        self.g_flashbar.require_size([
            _("Click 'New tone' to begin."),
            _("Correct, but you have already solved this question"),
            _("Wrong, but you have already solved this question"),
        ])
        if self.m_t.m_custom_mode:
            for notename, value in zip(mpd.MusicalPitch.notenames,
                                       self.get_list('custom_mode_cfg')):
                try:
                    value = float(value)
                except ValueError:
                    value = 0.0
                self.set_float('%s_weight' % notename, value)
        else:
            if 'white_keys_weight' in self.m_t.m_P.header:
                if type(self.m_t.m_P.header.white_keys_weight) == list \
                        and len(self.m_t.m_P.header.white_keys_weight) == 7:
                    for idx, n in enumerate(mpd.MusicalPitch.natural_notenames):
                        try:
                            weight = float(self.m_t.m_P.header.white_keys_weight[idx])
                        except ValueError:
                            weight = 0.0
                        self.set_float('%s_weight' % n, weight)
                else:
                    gu.dialog_ok("The white_keys_weight variable in the lesson file '%s' had wrong type" % os.path.abspath(self.m_t.m_P.m_filename), msgtype=Gtk.MessageType.WARNING)
            else:
                for idx, n in enumerate(mpd.MusicalPitch.notenames):
                    self.set_float('%s_weight' % n, 0.0)
            if 'black_keys_weight' in self.m_t.m_P.header:
                if type(self.m_t.m_P.header.black_keys_weight) == list \
                        and len(self.m_t.m_P.header.black_keys_weight) == 5:
                    for idx, n in enumerate(mpd.MusicalPitch.sharp_notenames):
                        try:
                            weight = float(self.m_t.m_P.header.black_keys_weight[idx])
                        except ValueError:
                            weight = 0.0
                        self.set_float('%s_weight' % n, weight)
                else:
                    gu.dialog_ok("The black_keys_weight variable in the lesson file '%s' had wrong type" % os.path.abspath(self.m_t.m_P.m_filename), msgtype=Gtk.MessageType.WARNING)
            else:
                for idx, n in enumerate(('cis', 'dis', 'fis', 'gis', 'ais')):
                    self.set_float('%s_weight' % n, 0.0)
        if self.m_t.m_custom_mode:
            self.g_config_elems.show()
            self.m_t.m_statistics.reset_custom_mode_session(self.m_t.m_P.m_filename)
        else:
            self.g_config_elems.hide()
            self.m_t.m_statistics.reset_session()
        self.g_statview.g_heading.set_text("%s - %s" % (_("Identify tone"), self.m_t.m_P.header.title))
        self.set_percentage_label()
        self.g_flashbar.delayed_flash(self.short_delay,
            _("Click 'New tone' to begin."))
        self.std_buttons_start_practise()
        self.m_t.q_status = self.QSTATUS_NO
    def on_end_practise(self):
        if self.m_t.m_custom_mode:
            self.set_list('custom_mode_cfg', [self.get_float('%s_weight' % x)
                         for x in mpd.MusicalPitch.notenames])
        self.m_t.end_practise()
        self.std_buttons_end_practise()

