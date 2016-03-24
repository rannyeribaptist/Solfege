# vim: set fileencoding=utf-8 :
# GNU Solfege - free ear training software
# Copyright (C) 2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2011,
# 2013  Tom Cato Amundsen
# Copyright (C) 2013 Jan Baumgart
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
from gi.repository import GObject

from solfege import gu
from solfege import soundcard, mpd
from solfege import cfg

from solfege.const import solmisation_syllables, solmisation_notenames


class SolmisationAddOnClass:
    elements = range(35)
    def new_question(self):
        """returns:
            self.ERR_PICKY : if the question is not yet solved and the
            teacher is picky (== you have to solve the
            question before a new is asked).
            self.OK : if a new question was created.
            self.ERR_NO_ELEMS : if no elements are set to be practised.
            """
        if self.m_timeout_handle:
            GObject.source_remove(self.m_timeout_handle)
            self.m_timeout_handle = None

        if self.get_bool('config/picky_on_new_question') \
            and self.q_status in [self.QSTATUS_NEW, self.QSTATUS_WRONG]:
                return self.ERR_PICKY

        self.q_status = self.QSTATUS_NO
        if not self.m_P.header.solmisation_elements:
            return self.ERR_NO_ELEMS
        self.m_question = []
        for x in range(self.get_int("num_notes")):
            self.m_question.append(random.choice(self.m_P.header.solmisation_elements))
        self.q_status = self.QSTATUS_NEW
        self.m_transp = random.randint(-5, 6)
        return self.OK
    def get_music_notenames(self, count_in):
        """
        Return a string with the notenames of the current question.
        Include count in if count_in == True
        """

        cadence = ""

        cadence += "<"
        cadence += mpd.transpose_notename("c''", self.m_transp) + "4 "
        cadence += mpd.transpose_notename("g'", self.m_transp) + " "
        cadence += mpd.transpose_notename("e'", self.m_transp) + " "
        cadence += mpd.transpose_notename("c", self.m_transp)
        cadence += ">"

        cadence += "<"
        cadence += mpd.transpose_notename("c''", self.m_transp) + "4 "
        cadence += mpd.transpose_notename("a'", self.m_transp) + " "
        cadence += mpd.transpose_notename("c'", self.m_transp) + " "
        cadence += mpd.transpose_notename("f", self.m_transp)
        cadence += ">"

        cadence += "<"
        cadence += mpd.transpose_notename("b'", self.m_transp) + "4 "
        cadence += mpd.transpose_notename("g'", self.m_transp) + " "
        cadence += mpd.transpose_notename("d'", self.m_transp) + " "
        cadence += mpd.transpose_notename("g", self.m_transp)
        cadence += ">"

        cadence += " "

        cadence += "<"
        cadence += mpd.transpose_notename("c''", self.m_transp) + "4 "
        cadence += mpd.transpose_notename("g'", self.m_transp) + " "
        cadence += mpd.transpose_notename("e'", self.m_transp) + " "
        cadence += mpd.transpose_notename("c", self.m_transp)
        cadence += ">"

        #s = "<b'4 g' d' g> <c''2. g' e' c>"

        melody = ""
        p = mpd.MusicalPitch()
        for k in self.m_question:
            melody += " " + mpd.transpose_notename(solmisation_notenames[k], self.m_transp) + "4"

        if self.get_bool('play_cadence'):
            result = cadence + " " + melody
        else:
            result = melody

        return result
    def get_music_string(self):
        """
            Return a complete mpd string of the current question that can
            be feed to utils.play_music.
            """
        return r"\staff{ \time 1000000/4 %s}" % self.get_music_notenames(True)
    def play(self, rhythm):
        """
        rhythm is a string. Example: 'c4 c8 c8 c4'
        """
        # FIXME can we use lessonfile.Rhythm insted of this?
        score = mpd.parser.parse_to_score_object(rhythm)
        track = mpd.score_to_tracks(score)[0]
        track.prepend_bpm(self.get_int("bpm"))
        track.prepend_volume(cfg.get_int('config/preferred_instrument_volume'))
        soundcard.synth.play_track(track)

    def set_default_header_values(self):
        for n, default in (('bpm', 60),
                           ('count_in', 2),
                           ('num_notes', 4)):
            if n in self.m_P.header:
                self.set_int(n, self.m_P.header[n])
            else:
                self.set_int(n, default)


class SolmisationAddOnGuiClass(object):
    def add_select_elements_gui(self):
        self.g_element_frame = frame = Gtk.Frame(label=_("Choose tones"))
        self.config_box.pack_start(frame, False, False, 0)
        self.g_select_rhythms_box = Gtk.VBox()
        self.g_select_rhythms_box.set_border_width(gu.hig.SPACE_SMALL)
        frame.add(self.g_select_rhythms_box)
        self.soltogglebuttons = []

    def add_select_num_notes_gui(self):
        hbox = Gtk.HBox()
        hbox.set_spacing(gu.hig.SPACE_SMALL)
        label = Gtk.Label(label=_("Number of tones:"))
        hbox.pack_start(label, False, False, 0)
        self.config_box_sizegroup.add_widget(label)
        label.set_alignment(1.0, 0.5)
        hbox.pack_start(gu.nSpinButton(self.m_exname, "num_notes",
                                       Gtk.Adjustment(4, 1, 100, 1, 10)), False, False, 0)
        self.config_box.pack_start(hbox, False, False, 0)
        hbox.show_all()
        self.config_box.pack_start(hbox, False, False, 0)

    def soltogglebutton(self, i):
        if i >= 0:
            btn = Gtk.ToggleButton(solmisation_syllables[i])
            btn.connect('toggled', self.select_element_cb, i)
        else:
            btn = Gtk.ToggleButton()
            btn.set_sensitive(False)
        btn.show()
        return btn

    def update_select_elements_buttons(self):
        """
        (Re)create the checkbuttons used to select which rhythm elements
        to be used when creating questions. We only need to do this if
        we are in m_custom_mode.
        """
        for but in self.soltogglebuttons:
            but.destroy()
        self.soltogglebuttons = []

        gs = Gtk.SizeGroup(Gtk.SizeGroupMode.HORIZONTAL)

        for i, v in enumerate((
                [1, 4, -1, 8, 11, -1, 15, 18, 21, -1, 25, 28, -1, 32],
                [0, 3, 6, 7, 10, 13, 14, 17, 20, 23, 24, 27, 30, 31, 34],
                [2, 5, -1, 9, 12, -1, 16, 19, 22, -1, 26, 29, -1, 33])):
            hbox = Gtk.HBox(True, 0)
            for k in v:
                b = self.soltogglebutton(k)
                gs.add_widget(b)
                for n in self.m_t.m_P.header.solmisation_elements:
                    if k == n:
                        b.set_active(True)
                hbox.pack_start(b, True, True, 0)
                self.soltogglebuttons.append(b)
            spacing = Gtk.Alignment()
            if i in (0, 2):
                spacing.set_property('left-padding', 16)
                spacing.set_property('right-padding', 16)
            spacing.add(hbox)
            self.g_select_rhythms_box.pack_start(spacing, True, True, 0)
            spacing.show_all()

    def select_element_cb(self, button, element_num):
        def sortlike(orig, b):
            ret = []
            for n in orig:
                if n in b:
                    ret.append(n)
            return ret
        if button.get_active():
            if element_num not in self.m_t.m_P.header.solmisation_elements:
                self.m_t.m_P.header.solmisation_elements.append(element_num)
                self.m_t.m_P.header.solmisation_elements = sortlike(
                    SolmisationAddOnClass.elements,
                    self.m_t.m_P.header.solmisation_elements)
        else:
            if element_num in self.m_t.m_P.header.solmisation_elements:
                self.m_t.m_P.header.solmisation_elements.remove(element_num)
