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

from gi.repository import GObject
from gi.repository import Gtk

from solfege import abstract
from solfege import gu
from solfege import lessonfile
from solfege import mpd
from solfege import soundcard
from solfege import utils
from solfege.multipleintervalconfigwidget import nIntervalCheckBox

class Teacher(abstract.Teacher):
    OK = 0
    ERR_PICKY = 1
    ERR_CONFIGURE = 2
    def __init__(self, exname):
        abstract.Teacher.__init__(self, exname)
        self.lessonfileclass = lessonfile.HeaderLessonfile
        for s in 'harmonic', 'melodic':
            self.m_lessonfile_defs[s] = s
        self.m_custom_mode = False
    def give_up(self):
        self.q_status = self.QSTATUS_GIVE_UP
    def new_question(self):
        """
        Return a true value if a new question was created otherwise false.
        """
        if self.m_timeout_handle:
            GObject.source_remove(self.m_timeout_handle)
            self.m_timeout_handle = None

        if self.get_bool('config/picky_on_new_question') \
                 and self.q_status in [self.QSTATUS_NEW, self.QSTATUS_WRONG]:
            return Teacher.ERR_PICKY

        first = self.get_list('first_interval_up')
        if self.get_string('first_interval_type') == 'melodic':
            first = first + map(lambda a: -a, self.get_list('first_interval_down'))
        last = self.get_list('last_interval_up')
        if self.get_string('last_interval_type') == 'melodic':
            last = last + map(lambda a: -a, self.get_list('last_interval_down'))
        if not (first and last):
            return self.ERR_CONFIGURE
        self.m_intervals = [random.choice(first), random.choice(last)]
        self.m_tonikas = [mpd.MusicalPitch().randomize("f", "f'"),
                          mpd.MusicalPitch().randomize("f", "f'")]
        self.q_status = self.QSTATUS_NEW
        return self.OK
    def play_question(self):
        if self.q_status == self.QSTATUS_NO:
            return
        t1, t2 = utils.new_2_tracks()
        if self.get_string('first_interval_type') == 'harmonic':
            t1.note(4, self.m_tonikas[0])
            t2.note(4, self.m_tonikas[0] + self.m_intervals[0])
        else:
            t1.note(4, self.m_tonikas[0])
            t1.notelen_time(4)
            t2.notelen_time(4)
            t2.note(4, self.m_tonikas[0] + self.m_intervals[0])
        if self.get_string('last_interval_type') == 'harmonic':
            t1.note(4, self.m_tonikas[1])
            t2.note(4, self.m_tonikas[1] + self.m_intervals[1])
        else:
            t1.note(4, self.m_tonikas[1])
            t1.notelen_time(4)
            t2.notelen_time(4)
            t2.note(4, self.m_tonikas[1] + self.m_intervals[1])
        soundcard.synth.play_track(t1, t2)
    def play_first_interval(self, w):
        if self.q_status == self.QSTATUS_NO:
            return
        t1, t2 = utils.new_2_tracks()
        if self.get_string('first_interval_type') == 'harmonic':
            t1.note(4, self.m_tonikas[0])
            t2.note(4, self.m_tonikas[0] + self.m_intervals[0])
        else:
            t1.note(4, self.m_tonikas[0])
            t1.notelen_time(4)
            t2.notelen_time(4)
            t2.note(4, self.m_tonikas[0] + self.m_intervals[0])
        soundcard.synth.play_track(t1, t2)
    def play_last_interval(self, w):
        if self.q_status == self.QSTATUS_NO:
            return
        t1, t2 = utils.new_2_tracks()
        if self.get_string('last_interval_type') == 'harmonic':
            t1.note(4, self.m_tonikas[1])
            t2.note(4, self.m_tonikas[1] + self.m_intervals[1])
        else:
            t1.note(4, self.m_tonikas[1])
            t1.notelen_time(4)
            t2.notelen_time(4)
            t2.note(4, self.m_tonikas[1] + self.m_intervals[1])
        soundcard.synth.play_track(t1, t2)
    def guess_answer(self, c):
        """
        argument c:
        -1 : first is largest
         0 : equal
         1 : last is largest
        Return: 1 if correct, 0 if wrong
        """
        a = cmp(abs(self.m_intervals[1]), abs(self.m_intervals[0])) == c
        if a:
            self.maybe_auto_new_question()
            self.q_status = self.QSTATUS_SOLVED
        else:
            self.q_status = self.QSTATUS_WRONG
        return a

class Gui(abstract.Gui):
    lesson_heading = _("Compare intervals")
    def __init__(self, teacher):
        abstract.Gui.__init__(self, teacher)
        self._ignore_events = 0
        ##############
        # practise_box
        ##############
        self.practise_box.set_spacing(gu.PAD)
        hbox = gu.bHBox(self.practise_box)
        self.g_music_displayer = mpd.MusicDisplayer()
        self.g_music_displayer.clear()
        hbox.pack_start(self.g_music_displayer, True, True, 0)

        self.g_flashbar = gu.FlashBar()
        self.g_flashbar.show()
        self.practise_box.pack_start(self.g_flashbar, False, False, 0)

        hbox = gu.bHBox(self.practise_box, False)
        hbox.set_homogeneous(True)
        self.g_first_is_largest = gu.bButton(hbox, _("F_irst interval\nis largest"), lambda f, self=self: self.guess_answer(-1))
        self.g_first_is_largest.get_child().set_justify(Gtk.Justification.CENTER)
        self.g_first_is_largest.set_sensitive(False)
        self.g_equal_size = gu.bButton(hbox, _("The intervals\nare _equal"), lambda f, self=self: self.guess_answer(0))
        self.g_equal_size.get_child().set_justify(Gtk.Justification.CENTER)
        self.g_equal_size.set_sensitive(False)
        self.g_last_is_largest = gu.bButton(hbox, _("_Last interval\nis largest"), lambda f, self=self: self.guess_answer(1))
        self.g_last_is_largest.set_sensitive(False)
        self.g_last_is_largest.get_child().set_justify(Gtk.Justification.CENTER)
        self.std_buttons_add(
                ('new', self.new_question),
                ('repeat', lambda w, self=self: self.m_t.play_question()),
                ('repeat_first', self.m_t.play_first_interval),
                ('repeat_last', self.m_t.play_last_interval),
                ('give_up', self.give_up),
        )
        self.action_area.set_homogeneous(True)
        self.practise_box.show_all()
        ##############
        # config_box #
        ##############
        self._add_auto_new_question_gui(self.config_box)
        # ----------------------------------------------

        def pack_rdbs(box, callback):
            D = {}
            D['harmonic'] = b = gu.RadioButton(None, _("Harmonic"), callback)
            b.m_idir = 'harmonic'
            box.pack_start(b, False, False, 0)
            D['melodic'] = b = gu.RadioButton(b, _("Melodic"), callback)
            b.m_idir = 'melodic'
            box.pack_start(b, False, False, 0)
            return D
        #---------
        self.g_intervalconfig_box = gu.bVBox(self.config_box, False)
        hbox = gu.bHBox(self.g_intervalconfig_box, False)
        hbox.pack_start(Gtk.Label(_("First interval:")), False, False,
                        padding=gu.PAD_SMALL)
        self.g_rdbs = [pack_rdbs(hbox, self.update_first)]
        self.g_first_interval_up = nIntervalCheckBox(self.m_exname,
                                                     'first_interval_up')
        self.g_intervalconfig_box.pack_start(self.g_first_interval_up, False, False, 0)
        self.g_first_interval_down = nIntervalCheckBox(
            self.m_exname, 'first_interval_down')
        self.g_intervalconfig_box.pack_start(self.g_first_interval_down, False, False, 0)
        #----------
        hbox = gu.bHBox(self.g_intervalconfig_box, False)
        hbox.pack_start(Gtk.Label(_("Last interval:")), False, False,
                        padding=gu.PAD_SMALL)
        self.g_rdbs.append (pack_rdbs(hbox, self.update_last))
        self.g_last_interval_up = nIntervalCheckBox(self.m_exname,
                     'last_interval_up')
        self.g_intervalconfig_box.pack_start(self.g_last_interval_up, False, False, 0)
        self.g_last_interval_down = nIntervalCheckBox(self.m_exname,
                        'last_interval_down')
        self.g_intervalconfig_box.pack_start(self.g_last_interval_down, False, False, 0)
        #------------
        s = self.get_string('first_interval_type')
        if not s in ('harmonic', 'melodic'):
            self.set_string('first_interval_type', 'harmonic')
        self.g_rdbs[0][self.get_string('first_interval_type')].set_active(True)
        self.update_first(self.g_rdbs[0][self.get_string('first_interval_type')])
        s = self.get_string('last_interval_type')
        if not s in ('harmonic', 'melodic'):
            self.set_string('last_interval_type', 'harmonic')
        self.g_rdbs[1][self.get_string('last_interval_type')].set_active(True)
        self.update_last(self.g_rdbs[1][self.get_string('last_interval_type')])
        self.config_box.show_all()
        self.add_watch('first_interval_type', self._watch_1_cb)
        self.add_watch('last_interval_type', self._watch_2_cb)
    def _watch_1_cb(self, name):
        self._ignore_events = 1
        self.g_rdbs[0][self.get_string('first_interval_type')].set_active(1)
        self.g_first_interval_down.set_sensitive(
                self.get_string('first_interval_type') == 'melodic')
        self._ignore_events = 0
    def _watch_2_cb(self, name):
        self._ignore_events = 1
        self.g_rdbs[1][self.get_string('last_interval_type')].set_active(1)
        self.g_last_interval_down.set_sensitive(
                self.get_string('last_interval_type') == 'melodic')
        self._ignore_events = 0
    def update_first(self, button):
        """
        Called when the type of interval is changed.
        """
        if self._ignore_events:
            return
        self.set_string('first_interval_type', button.m_idir)
        self.g_first_interval_down.set_sensitive(button.m_idir == 'melodic')
    def update_last(self, button):
        """
        Called when the type of interval has changed.
        """
        if self._ignore_events:
            return
        self.set_string('last_interval_type', button.m_idir)
        self.g_last_interval_down.set_sensitive(button.m_idir == 'melodic')
    def guess_answer(self, g):
        if self.m_t.q_status == self.QSTATUS_NO:
            return
        if self.m_t.q_status == self.QSTATUS_SOLVED:
            if self.m_t.guess_answer(g):
                self.g_flashbar.flash(_("Correct, but you have already solved this question"))
            else:
                self.g_flashbar.flash(_("Wrong, but you have already solved this question"))
            return
        if self.m_t.q_status != self.QSTATUS_GIVE_UP:
            if self.m_t.guess_answer(g):
                self.std_buttons_answer_correct()
                self.show_intervals()
                self.g_flashbar.flash(_("Correct"))
                self.g_first_is_largest.set_sensitive(False)
                self.g_equal_size.set_sensitive(False)
                self.g_last_is_largest.set_sensitive(False)
            else:
                self.g_flashbar.flash(_("Wrong"))
                if self.get_bool("config/auto_repeat_question_if_wrong_answer"):
                    self.m_t.play_question()
                self.std_buttons_answer_wrong()
    def give_up(self, widget=None):
        if self.m_t.q_status == self.QSTATUS_WRONG:
            self.m_t.give_up()
            self.g_first_is_largest.set_sensitive(False)
            self.g_equal_size.set_sensitive(False)
            self.g_last_is_largest.set_sensitive(False)
            self.std_buttons_give_up()
            if self.m_t.m_intervals[0] < self.m_t.m_intervals[1]:
                s = _("Last interval is largest")
            elif self.m_t.m_intervals[0] == self.m_t.m_intervals[1]:
                s = _("The intervals are equal")
            else:
                s = _("First interval is largest")
            self.g_flashbar.push(_("The answer is: %s") % s)
            self.show_intervals()
    def show_intervals(self, widget=None):
        tv = [self.get_string('first_interval_type'),
                self.get_string('last_interval_type')]
        clefs = {}
        music = {}
        for x in range(2):
            music[x] = self.m_t.m_tonikas[x].get_octave_notename() + " " \
                + (self.m_t.m_tonikas[x] + mpd.Interval().set_from_int(self.m_t.m_intervals[x])).get_octave_notename()
            clefs[x] = mpd.select_clef(music[x])
            if tv[x] == 'harmonic':
                music[x] = "< %s >" % music[x]
        m = r"\staff{ \clef %s %s |" % (clefs[0], music[0])
        if clefs[0] != clefs[1]:
            m = m + r"\clef %s " % clefs[1]
        m = m + music[1]
        self.g_music_displayer.display(m,
              self.get_int('config/feta_font_size=20'))
    def new_question(self, widget=None):
        self.g_music_displayer.clear()
        q = self.m_t.new_question()
        if q == Teacher.OK:
            try:
                self.m_t.play_question()
            except Exception, e:
                if not self.standard_exception_handler(e, self.m_t.end_practise):
                    raise
                return
            self.g_first_is_largest.set_sensitive(True)
            self.g_first_is_largest.grab_focus()
            self.g_equal_size.set_sensitive(True)
            self.g_last_is_largest.set_sensitive(True)
            self.std_buttons_new_question()
            self.g_flashbar.clear()
        elif q == Teacher.ERR_PICKY:
            self.g_flashbar.flash(_("You have to solve this question first."))
        else:
            assert q == Teacher.ERR_CONFIGURE
            self.g_flashbar.flash(_("You have to configure the exercise properly"))
    def on_start_practise(self):
        super(Gui, self).on_start_practise()
        #
        # This for loop is for backward compatability. These four
        # variables are obsoleted!
        for n in ('first_interval_up', 'first_interval_down',
                  'last_interval_up', 'last_interval_down'):
            if n in self.m_t.m_P.header:
                self.set_list(n, self.m_t.m_P.header[n])
        if 'first_interval' in self.m_t.m_P.header:
            self.set_list('first_interval_down',
                [-n for n in self.m_t.m_P.header.first_interval if n < 0])
            self.set_list('first_interval_up',
                [n for n in self.m_t.m_P.header.first_interval if n > 0])
        if 'last_interval' in self.m_t.m_P.header:
            self.set_list('last_interval_down',
                [-n for n in self.m_t.m_P.header.last_interval if n < 0])
            self.set_list('last_interval_up',
                [n for n in self.m_t.m_P.header.last_interval if n > 0])
        self.m_t.m_custom_mode = \
            'first_interval' not in self.m_t.m_P.header and \
            'last_interval' not in self.m_t.m_P.header
        for n in ('first_interval_type', 'last_interval_type'):
            if n in self.m_t.m_P.header and \
                    self.m_t.m_P.header[n] in ('melodic', 'harmonic'):
                self.set_string(n, self.m_t.m_P.header[n])
            else:
                self.set_string(n, 'harmonic')
        self.g_flashbar.require_size([
            _("The answer is: %s") % _("Last interval is largest"),
            _("The answer is: %s") % _("First interval is largest"),
            _("You have to solve this question first."),
            _("You have to configure the exercise properly"),
        ])
        self.g_flashbar.delayed_flash(self.short_delay,
            _("Click 'New' to begin."))
        self.std_buttons_start_practise()
        if self.m_t.m_custom_mode:
            self.g_intervalconfig_box.show()
        else:
            self.g_intervalconfig_box.hide()
    def on_end_practise(self):
        self.m_t.end_practise()
        self.g_first_is_largest.set_sensitive(False)
        self.g_equal_size.set_sensitive(False)
        self.g_last_is_largest.set_sensitive(False)
        self.std_buttons_end_practise()
        self.g_music_displayer.clear()
        self.g_flashbar.clear()

