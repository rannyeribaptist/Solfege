# vim: set fileencoding=utf-8 :
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
import sys
import traceback

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject

from solfege import gu
from solfege import inputwidgets
from solfege.specialwidgets import RandomTransposeDialog
from solfege import soundcard, mpd
from solfege import utils
from solfege import cfg, lessonfile, osutils, const

import solfege

class QstatusDefs:
    QSTATUS_NO = 0
    QSTATUS_NEW = 1
    QSTATUS_WRONG = 2
    QSTATUS_SOLVED = 3
    QSTATUS_GIVE_UP = 4
    QSTATUS_VOICING_SOLVED = 5
    QSTATUS_VOICING_WRONG = 6
    QSTATUS_TYPE_WRONG = 7
    QSTATUS_TYPE_SOLVED = 8

class Teacher(cfg.ConfigUtils, QstatusDefs):
    def __init__(self, exname):
        cfg.ConfigUtils.__init__(self, exname)
        self.q_status = self.QSTATUS_NO
        self.m_statistics = None
        self.m_timeout_handle = None
        self.m_P = None
        # The file name, not a file object
        self.m_lessonfile = None
        self.m_question = None
        self.m_custom_mode = False
        self.m_lessonfile_defs = {'yes': True, 'no': False,
            'hidden': 'hidden',
            'enabled': 'enabled',
            'disabled': 'disabled'}
        # Some exercises modules want other default values for the
        # lessonfile header variables. They can add them to this dict
        self.m_lessonfile_header_defaults = {}
    def maybe_auto_new_question(self):
        if self.get_bool('new_question_automatically'):
            if self.m_timeout_handle is None:
                def remove_timeout(self=self):
                    self.m_timeout_handle = None
                    self.g_view.new_question()
                self.m_timeout_handle = GObject.timeout_add(int(self.get_float('seconds_before_new_question')*1000),  remove_timeout)
    def end_practise(self):
        if self.m_timeout_handle:
            GObject.source_remove(self.m_timeout_handle)
            self.m_timeout_handle = None
        self.q_status = self.QSTATUS_NO
        soundcard.synth.stop()
    def exit_test_mode(self):
        """
        Shared between harmonic and melodic interval.
        """
        self.m_statistics.exit_test_mode()
    def set_lessonfile(self, lessonfile):
        """
        Set the variable 'm_lessonfile' and
        parse the lesson file and save the statistics.
        """
        self.m_lessonfile = lessonfile
        self.parse_lessonfile()
        if self.m_P and self.m_statistics:
            solfege.db.validate_stored_statistics(self.m_P.m_filename)
    def parse_lessonfile(self):
        self.m_question = None
        self.q_status = self.QSTATUS_NO
        if not self.m_lessonfile:
            self.m_P = None
            return
        self.m_P = self.lessonfileclass(self.m_lessonfile_defs,
                                        self.m_lessonfile_header_defaults)
        self.m_P.parse_file(self.m_lessonfile)
        if [q for q in self.m_P.m_questions if isinstance(q.get('music'), lessonfile.Cmdline)]:
            run = gu.dialog_yesno(_("The lessonfile contain potentially dangerous code because it run external programs. Run anyway?"))
            if not run:
                self.m_P = None
    def check_askfor(self):
        if self.m_custom_mode:
            self.set_list('ask_for_names', range(len(self.m_P.get_unique_cnames())))
    def play_tonic(self):
        """
        Play the tonic of the question, if defined.
        """
        if 'tonic' in self.m_P.get_question():
            self.m_P.play_question(None, 'tonic')

class MelodicIntervalTeacher(Teacher):
    """
    Base class for interval exercises where
    you can have more than one interval.
    When this class was created it was used by melodicinterval
    and singinterval.
    """
    class ConfigureException(Exception):
        def __init__(self, msg=_("The exercise has to be better configured.")):
            Exception.__init__(self, msg)
    OK = 0
    ERR_PICKY = 1
    ERR_CONFIGURE = 2
    no_intervals_str = _("No intervals selected for interval number %i.")
    def __init__(self, exname):
        Teacher.__init__(self, exname)
        self.m_tonika = None
        self.m_question = []
    def new_question(self, L, H):
        assert isinstance(L, basestring)
        assert isinstance(H, basestring)

        if self.m_timeout_handle:
            GObject.source_remove(self.m_timeout_handle)
            self.m_timeout_handle = None

        if solfege.app.m_test_mode:
            old_tonika = self.m_tonika
            if old_tonika:
                old_toptone = old_tonika + self.m_question[0]
            self.m_P.next_test_question()
            self.m_question = [self.m_P.m_test_questions[self.m_P.m_test_idx]]
            self.m_tonika = mpd.MusicalPitch()
            # Do this loop to make sure two questions in a row does not have
            # the same top or bottom tone.
            while True:
                self.m_tonika, _ignore = utils.random_tonika_and_interval(L, H,
                            self.m_question)
                if not old_tonika:
                    break
                if old_tonika != self.m_tonika and self.m_tonika + self.m_question[0] != old_toptone:
                    break
            self.q_status = self.QSTATUS_NEW
            return self.OK

        if self.get_bool('config/picky_on_new_question') \
              and self.q_status in [self.QSTATUS_NEW, self.QSTATUS_WRONG]:
            return self.ERR_PICKY

        self.q_status = self.QSTATUS_NO
        last_tonika = self.m_tonika
        last_question = self.m_question
        if self.get_bool("lock-to-key"):
            # We don't have to check the validity of these two variables
            # because get_int will check that a int value is stored in the
            # database (and make it an int if it is not), and nComboBox
            # will make sure the int value is within the correct limits.
            lock_tonic = mpd.MusicalPitch.new_from_int(self.get_int("lock-to-key-note"))
            lock_scaletype = utils.key_data.keys()[:][self.get_int("lock-to-key-scaletype")]

        def try_make_question():
            try:
                if self.get_bool("lock-to-key"):
                    self.m_tonika, i = \
                        utils.random_tonic_and_interval_in_key(L, H,
                            self.get_list('ask_for_intervals_0'),
                            lock_tonic, lock_scaletype)
                else:
                    self.m_tonika, i = utils.random_tonika_and_interval(L, H,
                            self.get_list('ask_for_intervals_0'))
            except utils.NoPossibleIntervals, e:
                raise self.ConfigureException(self.no_intervals_str % 1)

            self.m_question = [i]
            t = self.m_tonika + i
            for x in range(1, self.get_int('number_of_intervals=1')):
                interval_list = self.get_list('ask_for_intervals_%i' % x)
                if not interval_list:
                    raise self.ConfigureException(self.no_intervals_str % (x + 1))
                if self.get_bool('lock-to-key'):
                    i = utils.random_interval_in_key(t, L, H,
                            interval_list,
                            lock_tonic, lock_scaletype)
                    if not i:
                        raise self.ConfigureException(_(u"Failed to select random interval number %i because of the configuration of the exercise. Either you have enabled intervals only if one direction, or none of the intervals belong to the key selected when you enabled «Lock to key».") % x)
                else:
                    i = utils.random_interval(t, L, H,
                            self.get_list('ask_for_intervals_%i' % x))
                    if not i:
                        raise self.ConfigureException(_("Failed to select random interval number %i because of the configuration of the exercise. You should select some intervals going in both directions.") % x)
                self.m_question.append(i)
                t = t + i
        max_try = 1000
        for counter in range(max_try):
            try:
                try_make_question()
            except self.ConfigureException, e:
                if counter == max_try -1:
                    raise
                else:
                    continue
            if last_tonika is not None \
                    and last_tonika == self.m_tonika \
                    and last_question == self.m_question:
                continue
            self.q_status = self.QSTATUS_NEW
            return self.OK

    def play_question(self):
        if self.q_status == self.QSTATUS_NO:
            return
        t = self.m_tonika

        m = utils.new_track()
        m.note(4, self.m_tonika.semitone_pitch())
        for i in self.m_question:
            t = t + i
            m.note(4, t.semitone_pitch())
        soundcard.synth.play_track(m)


class RhythmAddOnClass:
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

        norest_v = []
        v = []
        for x in self.m_P.header.rhythm_elements:
            if not (const.RHYTHMS[x][0] == "r"
                    and self.get_bool("not_start_with_rest")):
                norest_v.append(x)
            v.append(x)
        if not v:
            return self.ERR_NO_ELEMS
        if not norest_v:
            return self.ERR_NO_ELEMS
        self.m_question = [random.choice(norest_v)]
        for x in range(1, self.get_int("num_beats")):
            self.m_question.append(random.choice(v))
        self.q_status = self.QSTATUS_NEW
        return self.OK
    def get_music_notenames(self, count_in):
        """
        Return a string with the notenames of the current question.
        Include count in if count_in == True
        """
        s = ""
        if count_in:
            if self.m_P.header.count_in_notelen:
                count_in_notelen = self.m_P.header.count_in_notelen
            else:
                count_in_notelen = "4"
            s = "d%s " % count_in_notelen * self.get_int("count_in")
        s += " ".join([const.RHYTHMS[k] for k in self.m_question])
        return s
    def get_music_string(self):
        """
        Return a complete mpd string of the current question that can
        be feed to utils.play_music.
        """
        return r"\rhythmstaff{ \time 1000000/4 %s}" % self.get_music_notenames(True)
    def play_rhythm(self, rhythm):
        """
        rhythm is a string. Example: 'c4 c8 c8 c4'
        """
        # FIXME can we use lessonfile.Rhythm insted of this?
        score = mpd.parser.parse_to_score_object(rhythm)
        track = mpd.score_to_tracks(score)[0]
        track.prepend_bpm(self.get_int("bpm"))
        track.prepend_volume(cfg.get_int('config/preferred_instrument_volume'))
        track.replace_note(mpd.notename_to_int("c"),
                           self.get_int("config/rhythm_perc"))
        track.replace_note(mpd.notename_to_int("d"),
                           self.get_int("config/countin_perc"))
        soundcard.synth.play_track(track)
    def set_elements_variables(self):
        """
        This is called from the on_start_practise() method of exercise
        modules that generate rhythms and use these variables to select
        rhythm elements.
        """
        if self.m_custom_mode:
            if not self.m_P.header.rhythm_elements:
                self.m_P.header.rhythm_elements = self.m_P.header.configurable_rhythm_elements[:3]
            self.m_P.header.visible_rhythm_elements = self.m_P.header.rhythm_elements[:]
        else:
            if not self.m_P.header.visible_rhythm_elements:
                self.m_P.header.visible_rhythm_elements = \
                    self.m_P.header.rhythm_elements[:]
                self.m_P.header.rhythm_elements = \
                  [n for n in self.m_P.header.rhythm_elements if n != 'newline']
    def set_default_header_values(self):
        for n, default in (('bpm', 60),
                  ('count_in', 2),
                  ('num_beats', 4)):
            if n in self.m_P.header:
                self.set_int(n, self.m_P.header[n])
            else:
                self.set_int(n, default)

class Gui(Gtk.VBox, cfg.ConfigUtils, QstatusDefs):
    """Important members:
         - practise_box
         - action_area
         - config_box
    """
    short_delay = 700
    def __init__(self, teacher, no_notebook=False):
        Gtk.VBox.__init__(self)
        cfg.ConfigUtils.__init__(self, teacher.m_exname)
        assert type(no_notebook) == bool
        self._std_buttons = []
        self.m_key_bindings = {}
        self.m_t = teacher

        vbox = Gtk.VBox()
        vbox.set_spacing(gu.PAD)
        vbox.set_border_width(gu.PAD)
        vbox.show()

        self.practise_box = Gtk.VBox()
        self.practise_box.show()
        vbox.pack_start(self.practise_box, True, True, 0)

        box = Gtk.VBox()
        self.practise_box.pack_start(box, False, False, padding=gu.hig.SPACE_LARGE)
        box.show()
        self.g_lesson_heading = Gtk.Label()
        box.pack_start(self.g_lesson_heading, True, True, 0)

        self.g_lesson_description = Gtk.Label()
        self.g_lesson_description.set_line_wrap(True)
        box.pack_start(self.g_lesson_description, True, True, 0)

        self.action_area = Gtk.HBox()
        self.action_area.show()
        vbox.pack_start(self.action_area, False, False, 0)

        self.config_box = Gtk.VBox()
        self.config_box.set_border_width(gu.PAD)
        self.config_box.show()
        self.config_box_sizegroup = Gtk.SizeGroup(Gtk.SizeGroupMode.HORIZONTAL)
        if no_notebook:
            self.pack_start(vbox, True, True, 0)
            self.pack_start(self.config_box, False, False, 0)
            self.g_notebook = None
        else:
            self.g_notebook = Gtk.Notebook()
            self.pack_start(self.g_notebook, True, True, 0)

            self.g_notebook.append_page(vbox, Gtk.Label(label=_("Practise")))
            self.g_notebook.append_page(self.config_box, Gtk.Label(label=_("Config")))
            self.g_notebook.show()
        self.g_cancel_test = Gtk.Button(_("_Cancel test"))
        self.g_cancel_test.connect('clicked', self.on_cancel_test)
        self.action_area.pack_end(self.g_cancel_test, False, False, 0)
    def add_module_is_deprecated_label(self):
        """
        The deprecated module must set a message in self.g_deprecated_label
        in on_start_practise, preferable telling the file name of the
        lesson file.
        """
        img = Gtk.Image()
        img.set_from_stock(Gtk.STOCK_DIALOG_WARNING,
                           Gtk.IconSize.BUTTON)
        hbox = Gtk.HBox()
        hbox.set_border_width(12)
        self.practise_box.set_child_packing(self.g_lesson_heading, False, False, 0, 0)
        hbox.set_spacing(6)
        hbox.pack_start(img, True, True, 0)
        self.g_deprecated_label = Gtk.Label()
        hbox.pack_start(self.g_deprecated_label, True, True, 0)
        self.practise_box.pack_start(hbox, False, False, 0)
        self.practise_box.reorder_child(hbox, 0)
    def set_deprecation_text(self, oldmodule, newmodule, filename):
        self.g_deprecated_label.set_line_wrap(True)
        self.g_deprecated_label.set_markup("<b>The %(oldmodule)s module is deprecated. Convert \"%(filename)s\" to use the %(newmodule)s module.</b>" % locals())
    def std_buttons_add(self, *buttons):
        """
        buttons is a sequence of tuples ('buttonname', callback)
        buttonnames with a hyphen '-' are splitted at the first hyphen,
        and only the first part of the name are used.
        """
        d = {'new': _("_New"),
             'new-interval': _("_New interval"),
             'new-chord': _("_New chord"),
             'new-tone': _("_New tone"),
             'repeat': _("_Repeat"),
             'repeat_arpeggio': _("Repeat _arpeggio"),
             'repeat_slowly': _("Repeat _slowly"),
             'repeat_melodic': _("Repeat _melodic"),
             'repeat_first': _("Repeat first"),
             'repeat_last': _("Repeat last"),
             'play_tonic': _("Play _tonic"),
             'play_music': _("P_lay music"),
             'play_answer': _("_Play answer"),
             'guess_answer': _("Guess _answer"),
             'display_music': _("_Display music"),
             # This button exist mostly for historical reasons, but I think
             # it can be useful, even though it is not much used today (as in
             # Solfege 3.6). It will present a Show button for exercises that
             # does not have a music displayer. And the button will be
             # insensitive until the question has been solved.
             'show': _("_Show"),
             'give_up': _("_Give up"),
             'backspace': _("Backspace"),
        }
        self._std_buttons.extend([x[0] for x in buttons])
        for b, cb in buttons:
            button = gu.bButton(self.action_area, d[b], cb)
            if '-' in b:
                b = b.split('-')[0]
            setattr(self, 'g_%s' % b, button)
    def _std_buttons_start_sensitivity(self):
        # Values like 'new-interval', 'new-tone' and 'new-chord' and
        # possible others can be added to ._std_buttons
        if [n for n in self._std_buttons if n.split("-")[0] == 'new']:
            self.g_new.set_sensitive(True)
        for b in ('repeat', 'repeat_slowly', 'repeat_arpeggio',
            'repeat_first', 'repeat_last',
            'repeat_melodic', 'guess_answer', 'play_tonic', 'play_music',
            'play_answer', 'backspace',
            'display_music', 'show', 'give_up'):
            if b in self._std_buttons:
                getattr(self, 'g_%s' % b).set_sensitive(False)
    def std_buttons_start_practise(self):
        self._std_buttons_start_sensitivity()
        self.g_new.grab_focus()
        if 'repeat_slowly' in self._std_buttons:
            if self.m_t.m_P.header.have_repeat_slowly_button:
                self.g_repeat_slowly.show()
            else:
                self.g_repeat_slowly.hide()
        if 'repeat_arpeggio' in self._std_buttons:
            # If one or more of the questions is of musictype 'chord', then
            # we need the "Repeat arpeggio" button.
            if [q for q in self.m_t.m_P.m_questions \
                if isinstance(q.music, lessonfile.ChordCommon)]:
                self.g_repeat_arpeggio.show()
            else:
                self.g_repeat_arpeggio.hide()
        if 'play_tonic' in self._std_buttons:
            # Display the 'Play tonic' button if any questions in the
            # lesson file set the 'tonic' variable.
            if [q for q in self.m_t.m_P.m_questions if 'tonic' in q]:
                self.g_play_tonic.show()
            else:
                self.g_play_tonic.hide()
        if 'show' in self._std_buttons:
            # We only want the Show button if there are any questions that can
            # be displayed.
            if [q for q in self.m_t.m_P.m_questions if isinstance(q.music, lessonfile.MpdDisplayable)] and not self.m_t.m_P.header.have_music_displayer:
                self.g_show.show()
            else:
                self.g_show.hide()
    def std_buttons_new_question(self):
        # Values like 'new-interval', 'new-tone' and 'new-chord' and
        # possible others can be added to ._std_buttons
        if [n for n in self._std_buttons if n.split("-")[0] == 'new']:
            self.g_new.set_sensitive(
                not self.get_bool('config/picky_on_new_question'))
        for s in ('repeat', 'repeat_slowly', 'repeat_arpeggio',
                'repeat_first', 'repeat_last',
                'repeat_melodic', 'guess_answer', 'play_music',
                'display_music', 'play_answer'):
            if s in self._std_buttons:
                getattr(self, 'g_%s' % s).set_sensitive(True)
        if 'play_tonic' in self._std_buttons:
            self.g_play_tonic.set_sensitive(
                'tonic' in self.m_t.m_P.get_question())
        for n in 'show', 'give_up', 'guess_answer':
            if n in self._std_buttons:
                getattr(self, 'g_%s' % n).set_sensitive(False)
    def std_buttons_end_practise(self):
        # We check for the lesson parser because it is possible that a
        # completely broken lesson file was started, and the user tries
        # to exit that exercise or quit the program. And if the lesson file
        # does not have a header block, then we cannot call
        # std_buttons_start_practise
        if self.m_t.m_P and hasattr(self.m_t.m_P, 'header'):
            self.std_buttons_start_practise()
        else:
            for name in self._std_buttons:
                if name.split("-")[0] not in ('new', 'repeat', 'give_up'):
                    if '-' in name:
                        name = name.split('-')[0]
                    getattr(self, 'g_%s' % name).hide()
    def std_buttons_answer_correct(self):
        # Setting sensitivity is only required when
        # self.get_bool('config/picky_on_new_question') is True, but
        # we does it every time just in case the user have changed the
        # variable between clicking 'New' and answering the question.
        if [n for n in self._std_buttons if n.split("-")[0] == 'new']:
            self.g_new.set_sensitive(True)
            self.g_new.grab_focus()
        if 'show' in self._std_buttons:
            self.g_show.set_sensitive(True)
        if 'give_up' in self._std_buttons:
            self.g_give_up.set_sensitive(False)
        if 'guess_answer' in self._std_buttons:
            self.g_guess_answer.set_sensitive(False)
        if 'backspace' in self._std_buttons:
            self.g_backspace.set_sensitive(False)
    def std_buttons_answer_wrong(self):
        if 'give_up' in self._std_buttons:
            self.g_give_up.set_sensitive(True)
    def std_buttons_give_up(self):
        if [n for n in self._std_buttons if n.split("-")[0] == 'new']:
            self.g_new.set_sensitive(True)
            self.g_new.grab_focus()
        if 'show' in self._std_buttons:
            self.g_show.set_sensitive(
                not self.g_music_displayer.props.visible)
        if 'give_up' in self._std_buttons:
            self.g_give_up.set_sensitive(False)
        if 'guess_answer' in self._std_buttons:
            self.g_guess_answer.set_sensitive(False)
        if 'backspace' in self._std_buttons:
            self.g_backspace.set_sensitive(False)
    def std_buttons_exception_cleanup(self):
        self._std_buttons_start_sensitivity()
    def on_cancel_test(self, *w):
        self.g_cancel_test.hide()
        self.on_end_practise()
        solfege.win.exit_test_mode()
    def do_test_complete(self):
        self.on_end_practise()
        req = self.m_t.m_P.get_test_requirement()
        self.g_cancel_test.hide()
        solfege.win.exit_test_mode()
        passed, res = solfege.db.get_test_status(self.m_t.m_P.m_filename)
        if res >= req:
            gu.dialog_ok(_("Test completed!\nYour score was %(score).1f%%.\nThe test requirement was %(requirement).1f%%.") % {'score': res * 100, 'requirement': req * 100})
        else:
            gu.dialog_ok(_("Test failed.\nYour score was %(score).1f%%.\nThe test requirement was %(requirement).1f%%.") % {'score': res * 100, 'requirement': req * 100})
    def set_lesson_heading(self, txt):
        if txt:
            self.g_lesson_heading.set_text('<span size="large"><b>%s</b></span>' % gu.escape(txt))
            self.g_lesson_heading.set_use_markup(True)
            self.g_lesson_heading.show()
        else:
            self.g_lesson_heading.hide()
    def set_lesson_description(self, txt):
        if txt:
            self.g_lesson_description.set_text(gu.escape(txt))
            self.g_lesson_description.set_use_markup(True)
            self.g_lesson_description.show()
        else:
            self.g_lesson_description.hide()
    def on_start_practise(self):
        """
        Code that are common for all exercises. Not used by many now,
        but lets see if that can improve.
        """
        self.handle_config_box_visibility()
        self.handle_statistics_page_sensibility()
        if self.get_bool("lock-to-key"):
            self.set_bool("lock-to-key", False)
        if hasattr(self, 'g_flashbar'):
            self.g_flashbar.require_size(["|Xy"])
        if self.m_t.m_P.header.lesson_heading:
            self.set_lesson_heading(self.m_t.m_P.header.lesson_heading)
        else:
            self.set_lesson_heading(getattr(self, "lesson_heading", None))
        if self.m_t.m_P.header.lesson_description:
            self.set_lesson_description(self.m_t.m_P.header.lesson_description)
        else:
            self.set_lesson_description(getattr(self, "lesson_description", None))
    def on_end_practise(self):
        pass
    def handle_config_box_visibility(self):
        """
        Show self.config_box if it has any visible children, otherwise
        hide it.
        """
        if [c for c in self.config_box.get_children() \
            if c.get_property('visible')]:
            self.config_box.show()
        else:
            self.config_box.hide()
    def handle_statistics_page_sensibility(self):
        try:
            if self.m_t.m_custom_mode:
                self.g_statview.set_sensitive(False)
                self.g_statview.set_tooltip_text(_(u"Statistics is disabled. Either because you selected a “Configure yourself” exercise, or because “Expert mode” is selected in the preferences window."))
            else:
                self.g_statview.set_sensitive(True)
                self.g_statview.set_tooltip_text("")
        except AttributeError: # not all exercises has g_statview
            pass
    def on_key_press_event(self, widget, event):
        if (self.g_notebook is None or self.g_notebook.get_current_page() == 0) \
                and event.type == Gdk.EventType.KEY_PRESS:
            for s in self.m_key_bindings:
                if self.keymatch(event, s):
                    self.m_key_bindings[s]()
                    return 1
    def keymatch(self, event, cfname):
        a, b = gu.parse_key_string(self.get_string(cfname))
        return ((event.get_state() & (Gdk.ModifierType.CONTROL_MASK|Gdk.ModifierType.SHIFT_MASK|Gdk.ModifierType.MOD1_MASK)) == a) and (event.keyval == b)
    def setup_statisticsviewer(self, viewclass, heading):
        self.g_statview = viewclass(self.m_t.m_statistics, heading)
        self.g_statview.show()
        self.g_notebook.append_page(self.g_statview, Gtk.Label(label=_("Statistics")))
        self.g_notebook.connect('switch_page', self.on_switch_page)
    def on_switch_page(self, notebook, obj, pagenum):
        if pagenum == 2:
            if self.m_t.m_P and not self.m_t.m_custom_mode:
                self.g_statview.update()
            else:
                self.g_statview.clear()
    def _add_auto_new_question_gui(self, box):
        hbox = gu.bHBox(box, False)
        hbox.set_spacing(gu.PAD_SMALL)
        adj = Gtk.Adjustment(0, 0, 10, 0.1, 1)
        spin = gu.nSpinButton(self.m_exname, 'seconds_before_new_question',
                       adj)
        spin.set_digits(1)
        label = Gtk.Label(label=_("Delay (seconds):"))
        label.show()
        def f(button, spin=spin, label=label):
            spin.set_sensitive(button.get_active())
            label.set_sensitive(button.get_active())
        b = gu.nCheckButton(self.m_exname, 'new_question_automatically',
                            _("_New question automatically."), callback=f)
        hbox.pack_start(b, False, False, 0)
        label.set_sensitive(b.get_active())
        hbox.pack_start(label, False, False, 0)
        spin.set_sensitive(b.get_active())
        hbox.pack_start(spin, False, False, 0)
    def _lessonfile_exception(self, exception, sourcefile, lineno):
        m = gu.ExceptionDialog(exception)
        idx = self.m_t.m_P._idx
        if idx is not None:
            m.add_text(_('Please check question number %(idx)i in the lesson file "%(lf)s".') % {'idx': self.m_t.m_P._idx+1, 'lf': self.m_t.m_P.m_filename})
        if 'm_nonwrapped_text' in dir(exception):
            m.add_nonwrapped_text(exception.m_nonwrapped_text)
        if 'm_mpd_badcode' in dir(exception) and exception.m_mpd_badcode:
            # some music classes may return an empty string if they have
            # nothing useful to display.
            m.add_nonwrapped_text(exception.m_mpd_badcode)
        m.add_text(_('The exception was caught in\n"%(filename)s", line %(lineno)i.') % {'filename': sourcefile, 'lineno': lineno})
        m.run()
        m.destroy()
    def _mpd_exception(self, exception, sourcefile, lineno):
        m = gu.ExceptionDialog(exception)
        if 'm_mpd_varname' in dir(exception):
            m.add_text(_('Failed to parse the music in the variable "%(varname)s" in question number %(idx)i in the lesson file "%(lf)s".') % {
                'idx': self.m_t.m_P._idx + 1,
                'lf': lessonfile.uri_expand(self.m_t.m_P.m_filename),
                'varname': exception.m_mpd_varname})
        else:
            m.add_text(_('Failed to parse the music for question number %(idx)i in the lesson file "%(lf)s".') % {'idx': self.m_t.m_P._idx + 1, 'lf': lessonfile.uri_expand(self.m_t.m_P.m_filename)})
        if 'm_mpd_badcode' in dir(exception):
            m.add_nonwrapped_text(exception.m_mpd_badcode)
        m.add_text(_('The exception was caught in\n"%(filename)s", line %(lineno)i.') % {'filename': sourcefile, 'lineno': lineno})
        m.run()
        m.destroy()
    def run_exception_handled(self, method, *args, **kwargs):
        """
        Call method() and catch exceptions with standard_exception_handler.
        """
        try:
            return method(*args, **kwargs)
        except Exception, e:
            if not self.standard_exception_handler(e):
                raise
    def standard_exception_handler(self, e, cleanup_function=lambda: False):
        """
        Use this method to try to catch a few common solfege exceptions.
        It should only be used to catch exceptions after the file has
        successfully parsed by the lessonfile parser, and only used in
        exercises where the mpd code that might be wrong is comming from
        lesson files, not generated code.

        Usage:
        try:
            do something
        except Exception, e:
            if not self.standard_exception_handler(e):
                raise
        """
        sourcefile, lineno, func, code = traceback.extract_tb(sys.exc_info()[2])[0]
        # We can replace characters because we will only display the
        # file name, not open the file.
        sourcefile = sourcefile.decode(sys.getfilesystemencoding(), 'replace')
        if solfege.app.m_options.disable_exception_handler:
            return False
        elif isinstance(e, lessonfile.NoQuestionsConfiguredException):
            cleanup_function()
            solfege.win.display_error_message2(e.args[0], e.args[1])
            return True
        elif isinstance(e, lessonfile.LessonfileException):
            cleanup_function()
            self._lessonfile_exception(e, sourcefile, lineno)
            return True
        elif isinstance(e, mpd.MpdException):
            cleanup_function()
            self._mpd_exception(e, sourcefile, lineno)
            return True
        elif isinstance(e, osutils.BinaryBaseException):
            cleanup_function()
            solfege.win.display_error_message2(e.msg1, e.msg2)
            return True
        elif isinstance(e, osutils.OsUtilsException):
            cleanup_function()
            gu.display_exception_message(e)
            return True
        return False

class RhythmAddOnGuiClass(object):
    def add_select_elements_gui(self):
        self.g_element_frame = frame = Gtk.Frame(label=_("Rhythms to use in question"))
        self.config_box.pack_start(frame, False, False, 0)
        self.g_select_rhythms_box = gu.NewLineBox()
        self.g_select_rhythms_box.set_border_width(gu.PAD_SMALL)
        frame.add(self.g_select_rhythms_box)
    def add_select_num_beats_gui(self):
        ###
        hbox = Gtk.HBox()
        hbox.set_spacing(gu.hig.SPACE_SMALL)
        label = Gtk.Label(label=_("Number of beats in question:"))
        hbox.pack_start(label, False, False, 0)
        self.config_box_sizegroup.add_widget(label)
        label.set_alignment(1.0, 0.5)
        hbox.pack_start(gu.nSpinButton(self.m_exname, "num_beats",
                     Gtk.Adjustment(4, 1, 100, 1, 10)), False, False, 0)
        self.config_box.pack_start(hbox, False, False, 0)
        hbox.show_all()
        #
        hbox = Gtk.HBox()
        hbox.set_spacing(gu.hig.SPACE_SMALL)
        label = Gtk.Label(label=_("Count in before question:"))
        hbox.pack_start(label, False, False, 0)
        self.config_box_sizegroup.add_widget(label)
        label.set_alignment(1.0, 0.5)
        hbox.pack_start(gu.nSpinButton(self.m_exname, "count_in",
                     Gtk.Adjustment(2, 0, 10, 1, 10)), False, False, 0)
        hbox.show_all()
        self.config_box.pack_start(hbox, False, False, 0)
    def pngcheckbutton(self, i):
        btn = Gtk.CheckButton()
        btn.add(gu.create_rhythm_image(const.RHYTHMS[i]))
        btn.show()
        btn.connect('clicked', self.select_element_cb, i)
        return btn
    def update_select_elements_buttons(self):
        """
        (Re)create the checkbuttons used to select which rhythm elements
        to be used when creating questions. We only need to do this if
        we are in m_custom_mode.
        """
        self.g_select_rhythms_box.empty()
        for n in self.m_t.m_P.header.configurable_rhythm_elements:
            if n == 'newline':
                self.g_select_rhythms_box.newline()
            else:
                b = self.pngcheckbutton(n)
                self.g_select_rhythms_box.add_widget(b)
                b.set_active(n in self.m_t.m_P.header.rhythm_elements)
        self.g_select_rhythms_box.show_widgets()
    def select_element_cb(self, button, element_num):
        def sortlike(orig, b):
            ret = []
            for n in orig:
                if n == 'newline':
                    ret.append('newline')
                elif n in b:
                    ret.append(n)
            return ret
        if button.get_active():
            if element_num not in self.m_t.m_P.header.rhythm_elements:
                self.m_t.m_P.header.rhythm_elements.append(element_num)
                self.m_t.m_P.header.rhythm_elements = sortlike(
                    self.m_t.m_P.header.configurable_rhythm_elements,
                    self.m_t.m_P.header.rhythm_elements)
        else:
            if element_num in self.m_t.m_P.header.rhythm_elements:
                self.m_t.m_P.header.rhythm_elements.remove(element_num)
        self.m_t.m_P.header.visible_rhythm_elements = \
            self.m_t.m_P.header.rhythm_elements[:]
        self.m_t.m_P.header.rhythm_elements = \
            [n for n in self.m_t.m_P.header.rhythm_elements if n != 'newline']

class IntervalGui(Gui):
    """
    Creates 'New interval' and 'Repeat' buttons in the action_area.
    """
    keyboard_accel = 99
    def __init__(self, teacher):
        Gui.__init__(self, teacher)

        self.g_input = None

        self.g_flashbar = gu.FlashBar()
        self.g_flashbar.show()
        self.practise_box.pack_start(self.g_flashbar, False, False, 0)
        self.practise_box.set_spacing(gu.PAD)

        self.std_buttons_add(('new-interval', self.new_question),
            ('repeat', self.repeat_question))
        self.setup_key_bindings()
    def _create_select_inputwidget_gui(self):
        """
        This will be called by HarmonicInterval and MelodicInterval
        constructor
        """
        hbox = gu.bHBox(self.config_box, False)
        hbox.set_spacing(gu.PAD_SMALL)
        gu.bLabel(hbox, _("Input interface:"), False)

        combo = Gtk.ComboBoxText()
        for i in range(len(inputwidgets.inputwidget_names)):
            combo.append_text(inputwidgets.inputwidget_names[i])
        if self.get_int('inputwidget') < len(inputwidgets.inputwidget_names):
            combo.set_active(self.get_int('inputwidget'))
        else:
            combo.set_active(0)
        combo.connect('changed', lambda w: self.use_inputwidget(w.get_active()))
        hbox.pack_start(combo, False, False, 0)

        self.g_disable_unused_buttons = gu.nCheckButton(self.m_exname,
                    'disable_unused_intervals', _("_Disable unused buttons"))
        hbox.pack_start(self.g_disable_unused_buttons, True, True, 0)
    def add_lock_to_key_gui(self):
        # gui to lock to a key
        def toggle_lock_to_key_sensitivity(checkbutton):
            self.g_notename.set_sensitive(checkbutton.get_active())
            self.g_scaletype.set_sensitive(checkbutton.get_active())
        self.g_lock_to_key_hbox = Gtk.HBox(False, gu.hig.SPACE_SMALL)
        self.config_box.pack_start(self.g_lock_to_key_hbox, False, False, 0)
        check = gu.nCheckButton(self.m_exname, 'lock-to-key',
            _("Lock intervals to key:"),
            callback = toggle_lock_to_key_sensitivity)
        self.g_lock_to_key_hbox.pack_start(check, False, False, 0)
        self.g_notename = gu.nComboBox(self.m_exname, 'lock-to-key-note',
            mpd.MusicalPitch.new_from_int(60).get_user_notename(),
            [mpd.MusicalPitch.new_from_int(60 + x).get_user_notename() for x in range(12)])
        self.g_notename.show()
        self.g_lock_to_key_hbox.pack_start(self.g_notename, False, False, 0)
        self.g_scaletype = gu.nComboBox(self.m_exname, 'lock-to-key-scaletype', _("Major"), [n['name'] for n in utils.key_data.values()])
        self.g_scaletype.show()
        self.g_lock_to_key_hbox.pack_start(self.g_scaletype, False, False, 0)
        toggle_lock_to_key_sensitivity(check)
    def select_inputwidget(self):
        """
        This will be called by HarmonicInterval and MelodicInterval
        constructor
        """
        i = self.get_int('inputwidget')
        if i >= len(inputwidgets.inputwidget_names):
            i = 0
        self.use_inputwidget(i)
    def use_inputwidget(self, i):
        self.set_int('inputwidget', i)
        if self.g_input:
            self.g_input.destroy()
        # FIXME UGH ugly ugly ugly, I'm lazy lazy lazy
        import solfege.exercises.harmonicinterval
        if isinstance(self, solfege.exercises.harmonicinterval.Gui):
            v = ['intervals']
        else:
            v = []
            for x in range(self.get_int('maximum_number_of_intervals')):
                v.append('ask_for_intervals_%i' % x)
        self.g_input = inputwidgets.int_to_inputwidget(
            i, self.click_on_interval, self.m_exname,
            self.get_interval_input_list, v)
        self.practise_box.pack_start(self.g_input, True, True, 0)
        self.practise_box.reorder_child(self.g_input, 1)
        self.g_input.show()
        if self.m_t.m_tonika:
            # Don't call on_end_practise if we are starting up the exercise.
            # This whole thing is a mess.
            self.on_end_practise()
        self.g_disable_unused_buttons.set_sensitive(
            isinstance(self.g_input, inputwidgets.IntervalButtonsWidgetBase))
    def setup_key_bindings(self):
        keys = ['minor2', 'major2', 'minor3', 'major3',
                'perfect4', 'diminished5', 'perfect5', 'minor6',
                'major6', 'minor7', 'major7', 'perfect8',
                'minor9', 'major9', 'minor10', 'major10']
        self.m_key_bindings = {}
        for idx in range(len(keys)):
            self.m_key_bindings['interval_input/'+keys[idx]] = lambda idx=idx, self=self: self.click_on_interval(self.keyboard_accel, idx+1, None)
    def repeat_question(self, *w):
        self.m_t.play_question()
        self.g_input.grab_focus_first_sensitive_button()


class LessonbasedGui(Gui):
    def __init__(self, teacher, no_notebook=False):
        Gui.__init__(self, teacher, no_notebook)
    def add_random_transpose_gui(self):
        self.g_random_transpose_box = hbox = gu.bHBox(self.config_box, False, False)
        label = Gtk.Label(label=_("Random transpose:"))
        label.show()
        hbox.pack_start(label, False, False, 0)
        hbox.set_spacing(6)
        self.g_random_transpose = Gtk.Label()
        self.g_random_transpose.show()
        hbox.pack_start(self.g_random_transpose, True, True, 0)

        button = Gtk.Button(_("Change ..."))
        button.show()
        button.connect('clicked', self.run_random_transpose_dialog)
        hbox.pack_start(button, True, True, 0)
    def run_random_transpose_dialog(self, widget):
        dlg = RandomTransposeDialog(self.m_t.m_P.header.random_transpose, solfege.win)
        response = dlg.run()
        if response == Gtk.ResponseType.OK:
            self.m_t.m_P.header.random_transpose = dlg.get_value()
            if self.m_t.m_P.header.random_transpose[0] == True:
                self.g_random_transpose.set_text(_("Yes"))
            elif self.m_t.m_P.header.random_transpose[0] == False:
                self.g_random_transpose.set_text(_("No"))
            else:
                self.g_random_transpose.set_text(str(self.m_t.m_P.header.random_transpose))
        dlg.destroy()
    def show_answer(self, widget=None):
        """
        Show the answer in the g_music_displayer if we have one, if not
        use a new window.
        """
        if 'vmusic' in self.m_t.m_P.get_question():
            varname = 'vmusic'
        else:
            varname = 'music'
        if not isinstance(self.m_t.m_P.get_question()[varname], lessonfile.MpdDisplayable):
            return
        self.display_music(varname)
    def display_music(self, varname):
        """
        Display the music in the variable named by varname from
        the currently selected question. This method will handle
        the normal mpd and lessonfile exceptions.
        """
        try:
            if self.m_t.m_P.header.have_music_displayer:
                fontsize = self.get_int('config/feta_font_size=20')
                self.g_music_displayer.display(self.m_t.m_P.get_music(varname), fontsize)
            else:
                solfege.win.display_in_musicviewer(self.m_t.m_P.get_music(varname))
        except mpd.MpdException, e:
            self.m_t.m_P.get_question()[varname].complete_to_musicdata_coords(self.m_t.m_P, e)
            e.m_mpd_varname = varname
            e.m_mpd_badcode = self.m_t.m_P.get_question()[varname].get_err_context(e, self.m_t.m_P)
            if not self.standard_exception_handler(e):
                raise
    def do_at_question_start_show_play(self):
        """
        This method is shared by idbyname and elembuilder, and possibly
        other exercises later. It will show and/or play music based on
        the header.at_question_start  variable.

        It might raise mpd.MpdException.
        """
        if self.m_t.m_P.header.at_question_start == 'show':
            self.show_answer()
        elif self.m_t.m_P.header.at_question_start == 'play':
            self.m_t.m_P.play_question()
            if 'cuemusic' in self.m_t.m_P.get_question():
                self.display_music('cuemusic')
        else:
            self.m_t.m_P.play_question()
            if 'show' in self.m_t.m_P.header.at_question_start \
                and 'play' in self.m_t.m_P.header.at_question_start:
                self.show_answer()
            elif 'cuemusic' in self.m_t.m_P.get_question():
                self.display_music('cuemusic')
    def show_hide_at_question_start_buttons(self):
        """
        Show and hide g_play_music, g_repeat and g_display_music
        depending on the content of header.at_question_start.
        This method is used by at least idbyname and elembuilder.
        """
        if self.m_t.m_P.header.at_question_start == 'show':
            self.g_play_music.show()
            self.g_repeat.hide()
        else:
            self.g_play_music.hide()
            self.g_repeat.show()
        if self.m_t.m_P.header.at_question_start == 'play':
            self.g_display_music.show()
        else:
            self.g_display_music.hide()

