# vim: set fileencoding=utf-8:
# GNU Solfege - free ear training software
# Copyright (C) 2011  Tom Cato Amundsen
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
from __future__ import division

import logging
import random

from gi.repository import Gtk

import solfege
from solfege import abstract
from solfege import cfg
from solfege import gu
from solfege import lessonfile
from solfege import mpd
from solfege import soundcard
from solfege import statistics
from solfege import statisticsviewer
from solfege.mpd import elems

labels = [u'1', u'♯1/♭2', u'2', u'♯2/♭3', u'3', u'4', u'♯4/♭5',
          u'5', u'♯5/6♭', u'6', u'♯6/♭7', u'7', u'1']

class ToneInKeyStatistics(statistics.LessonStatistics):
    def key_to_pretty_name(self, key):
        return labels[int(key)]


class Teacher(abstract.Teacher):
    OK = 0
    ERR_NO_CADENCES = 1
    ERR_NO_CADENCES_IN_FILE = 2
    def __init__(self, exname):
        abstract.Teacher.__init__(self, exname)
        self.lessonfileclass = lessonfile.HeaderLessonfile
        self.m_transpose = mpd.MusicalPitch()
        self.m_statistics = ToneInKeyStatistics(self)
    def new_question(self):
        """
        Return OK or ERR_NO_CADENCES
        """
        self.m_tone = random.choice(self.get_list("tones"))
        self.q_status = self.QSTATUS_NEW
        if self.get_bool('random_tonic'):
            self.m_transpose.randomize("c", "b")
        if self.m_custom_mode:
            cadence_list = [k for k in self.m_cadences.keys() if self.m_cadences[k]]
            if not cadence_list:
                return self.ERR_NO_CADENCES
            self.m_cadence = self.m_P.blocklists['cadence'][random.choice(cadence_list)]
        else:
            if 'cadence' not in self.m_P.blocklists:
                return self.ERR_NO_CADENCES_IN_FILE
            self.m_cadence = random.choice(self.m_P.blocklists['cadence'])
        return self.OK
    def play_question(self):
        cadence = self.m_cadence['music'][:]
        p = mpd.MusicalPitch.new_from_notename("c'") + self.m_tone
        if self.get_bool('random_tonic'):
            cadence = cadence.replace("\\staff", "\\staff\\transpose %s" % self.m_transpose.get_octave_notename())
            p.transpose_by_musicalpitch(self.m_transpose)
        m = mpd.parse_to_score_object(cadence)
        # Here we assume that we can check the first voice of the first
        # staff when finding the timepos and the duration of the last
        # tone in the cadence. But it is ok to have more staffs or voices
        # in the cadence, as long as the first assumption is true.
        staff = m.add_staff()
        voice = staff.add_voice()
        if 'tone_instrument' in self.m_cadence:
            try:
                instr = soundcard.find_midi_instrument_number(
                    self.m_cadence.get("tone_instrument"))
            except KeyError:
                logging.warning("WARNING: Bad MIDI instrument name in «%s»"
                                % self.m_P.m_filename)
                instr = cfg.get_int("config/preferred_instrument")
        else:
            instr = cfg.get_int("config/preferred_instrument")

        if self.get_bool('tone_in_cadence'):
            timepos = m.m_staffs[0].get_timeposes()[-1]
            last_len = m.m_staffs[0].m_voices[0].m_length - timepos
        else:
            timepos = m.m_staffs[0].m_voices[0].m_length
            last_len = mpd.Rat(1, 4)
        voice.set_elem([elems.Note(p, elems.Duration.new_from_rat(last_len))],
                       timepos)
        tr = mpd.score_to_tracks(m)
        t = self.m_cadence.get('tempo', (60, 4))
        tr[0].prepend_bpm(t[0], t[1])
        tr[-1].prepend_patch(instr)
        soundcard.synth.play_track(*tr)
    def guess_answer(self, answer):
        if answer == 12:
            answer = 0
        assert self.q_status not in (self.QSTATUS_NO, self.QSTATUS_GIVE_UP)
        if self.m_tone == answer or (answer == 0 and self.m_tone == 12):
            if self.q_status == self.QSTATUS_NEW \
                    and not self.m_custom_mode:
                self.m_statistics.add_correct(answer)
            self.maybe_auto_new_question()
            self.q_status = self.QSTATUS_SOLVED
            return 1
        else:
            if self.q_status == self.QSTATUS_NEW:
                if not self.m_custom_mode:
                    self.m_statistics.add_wrong(self.m_tone, answer)
                self.q_status = self.QSTATUS_WRONG
            #if solfege.app.m_test_mode:
            #    self.maybe_auto_new_question()
    def give_up(self):
        self.m_qstatus = self.QSTATUS_GIVE_UP
    def start_practise(self):
        self.m_custom_mode = bool(not self.m_P.header.tones)
        if not self.m_custom_mode:
            self.m_statistics.reset_session()
        if self.m_P.header.tones:
            self.set_list("tones", self.m_P.header.tones)
        # The default value for header.random_tonic is True.
        if self.m_P.header.random_tonic == False:
            self.set_bool('random_tonic', False)
        else:
            self.set_bool('random_tonic', True)


def fill_table(button_class, table):
    buttons = {}
    for p, x in ((0, 1), (1, 3), (3, 6), (4, 8), (5, 10)):
        b = button_class(labels[x])
        buttons[x] = b
        table.attach(b, p*4+2, (p+1)*4+2, 0, 1)
    for p, x in enumerate((0, 2, 4, 5, 7, 9, 11, 12)):
        b = button_class(labels[x])
        buttons[x] = b
        table.attach(b, p*4, (p+1)*4, 1, 2)
    return buttons


class nConfigButtons(Gtk.Table, cfg.ConfigUtils):
    def __init__(self, exname, name):
        Gtk.Table.__init__(self)
        cfg.ConfigUtils.__init__(self, exname)
        self.m_varname = name
        self.g_buttons = fill_table(Gtk.CheckButton, self)
        for key, button in self.g_buttons.items():
            button.connect('toggled', self.on_toggled)
        for key in self.get_list('tones'):
            self.g_buttons[key].set_active(True)
    def on_toggled(self, *w):
        self.set_list(self.m_varname,
            [k for k in self.g_buttons.keys() if self.g_buttons[k].get_active()])


class Gui(abstract.Gui):
    lesson_heading = _("Tone in context")
    def __init__(self, teacher):
        abstract.Gui.__init__(self, teacher)
        t = Gtk.Table()
        self.g_buttons = fill_table(Gtk.Button, t)
        for key, button in self.g_buttons.items():
            button.connect('clicked', self.on_left_click, key)
        self.practise_box.pack_start(t, False, False, 0)
        self.g_flashbar = gu.FlashBar()
        self.g_flashbar.show()
        self.practise_box.pack_start(self.g_flashbar, False, False, 0)
        self.std_buttons_add(
            ('new', self.new_question),
            ('repeat', lambda _o, self=self: self.m_t.play_question()),
            ('give_up', self.give_up))
        self.practise_box.show_all()
        ##############
        # config_box #
        ##############
        self.config_box.set_spacing(gu.hig.SPACE_MEDIUM)
        self.g_random = gu.nCheckButton(self.m_exname, 'random_tonic', _("Random transpose"))
        self.config_box.pack_start(self.g_random, False, False, 0)
        self._add_auto_new_question_gui(self.config_box)
        #
        self.g_tones_category, box = gu.hig_category_vbox(_("Tones"))
        self.config_box.pack_start(self.g_tones_category, False, False, 0)
        self.g_tone_selector = nConfigButtons(self.m_exname, 'tones')
        self.g_tone_selector.show_all()
        box.pack_start(self.g_tone_selector, False, False, 0)
        # Cadences
        self.g_cadences_category, self.g_cadences = gu.hig_category_vbox(_("Cadences"))
        self.g_cadences.show()
        self.config_box.pack_start(self.g_cadences_category, False, False, 0)
        #
        def _ff(var):
            if self.m_t.m_custom_mode:
                # If we are running in custom mode, then the user can
                # select himself what intervals to practise. And then
                # we have to reset the exercise.
                #self.on_end_practise()
                #self.on_start_practise()
                self.cancel_question()
        self.add_watch('tones', _ff)
        self.setup_statisticsviewer(statisticsviewer.StatisticsViewer,
                                   _("Tone in cadence"))
    def cancel_question(self):
        self.m_t.end_practise()
        self.std_buttons_end_practise()
    def new_question(self, *w):
        i = self.m_t.new_question()
        if i == Teacher.OK:
            self.std_buttons_new_question()
            self.m_t.play_question()
            for key, button in self.g_buttons.items():
                button.set_sensitive(key in self.get_list("tones"))
        elif i == Teacher.ERR_NO_CADENCES:
            self.g_flashbar.flash(_("No cadences selected"))
        elif i == Teacher.ERR_NO_CADENCES_IN_FILE:
            solfege.win.display_error_message2("No cadences in file",
                self.m_t.m_P.m_filename)
    def give_up(self, *w):
        if self.m_t.q_status == self.QSTATUS_WRONG:
            self.g_flashbar.push(_("The answer is: %s")
                 % labels[self.m_t.m_tone])
            self.m_t.give_up()
            self.std_buttons_give_up()
    def on_left_click(self, button, tone_int):
        if self.m_t.q_status == self.QSTATUS_SOLVED:
            if self.m_t.guess_answer(tone_int):
                self.g_flashbar.flash(_("Correct, but you have already solved this question"))
            else:
                self.g_flashbar.flash(_("Wrong, but you have already solved this question"))
        elif self.m_t.q_status in (self.QSTATUS_NEW, self.QSTATUS_WRONG):
            if self.m_t.guess_answer(tone_int):
                self.g_flashbar.flash(_("Correct"))
                self.std_buttons_answer_correct()
            else:
                self.g_flashbar.flash(("Wrong"))
                self.std_buttons_answer_wrong()
                if self.get_bool("config/auto_repeat_question_if_wrong_answer"):
                    self.m_t.play_question()
    def on_start_practise(self):
        self.m_t.start_practise()
        super(Gui, self).on_start_practise()
        if self.m_t.m_custom_mode:
            self.g_tone_selector.show()
            #self.g_random.show()
            self.g_tones_category.show()
            for w in self.g_cadences.get_children():
                w.destroy()
            self.g_cadences_category.show()
            self.g_cadences.show()
            self.m_t.m_cadences = {}
            if 'cadence' in self.m_t.m_P.blocklists:
                for idx, c in enumerate(self.m_t.m_P.blocklists['cadence']):
                    name = c.get('name', _("Unnamed"))
                    btn = Gtk.CheckButton(name)
                    btn.show()
                    btn.set_active(True)
                    self.m_t.m_cadences[idx] = True
                    btn.connect('toggled', self.on_cadences_toggled, idx)
                    self.g_cadences.pack_start(btn, False, False, 0)
        else:
            self.g_tone_selector.hide()
            self.g_tones_category.hide()
            self.g_cadences_category.hide()
            #self.g_random.hide()
        for key, button in self.g_buttons.items():
            button.set_sensitive(False)
        self.set_bool('tone_in_cadence', self.m_t.m_P.header.tone_in_cadence)
        self.std_buttons_start_practise()
        self.g_flashbar.delayed_flash(self.short_delay,
            _("Click 'New' to begin."))
        self.g_flashbar.require_size([
                _("Correct, but you have already solved this question"),
                _("Wrong, but you have already solved this question")])
    def on_cadences_toggled(self, btn, key):
        self.cancel_question()
        self.m_t.m_cadences[key] = btn.get_active()
