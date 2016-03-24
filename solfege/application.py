# vim: set fileencoding=utf-8:
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

import errno
import locale
import logging
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from urlparse import urlparse
import webbrowser

from solfege import mpd
from solfege import soundcard

from solfege import abstract
from solfege import cfg
from solfege import dataparser
from solfege import filesystem
from solfege import gu
from solfege import i18n
from solfege import lessonfile
from solfege import osutils
from solfege import parsetree
from solfege import reportlib
from solfege import utils

import solfege

try:
    from pyalsa import alsaseq
except ImportError:
    alsaseq = None

solfege_copyright = u"Copyright © 1999-2008 Tom Cato Amundsen <tca@gnu.org>, and others."

warranty = """
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""


def check_rcfile():
    """See default.config for rcfileversion values, meanings and
    a description of how to add config variables.
    """
    rcfileversion = 21
    if cfg.get_int("app/rcfileversion") > rcfileversion:
        cfg.drop_user_config()
        return
    if cfg.get_int("app/rcfileversion") <= 1:
        if not "example-files" in cfg.get_string('config/lessoncollections'):
            cfg.set_string('config/lessoncollections',
                "%s example-files" % cfg.get_string('config/lessoncollections'))
    if cfg.get_int("app/rcfileversion") <= 5:
        # This is more complicated that necessary to fix an old
        # error.
        if cfg.get_string("sound/commandline"):
            cfg.del_key("sound/commandline")
    if cfg.get_int("app/rcfileversion") <= 3:
        cfg.set_list("config/lessoncollections",
            cfg.get_string("config/lessoncollections").split())
    if cfg.get_int("app/rcfileversion") <= 4:
        cfg.del_key("config/web_browser")
    if sys.platform == 'win32':
        if cfg.get_string('sound/wav_player'):
            cfg.del_key('sound/wav_player')
    if cfg.get_int("app/rcfileversion") <= 5:
        cfg.set_string("mainwin/history_back_ak", "<alt>Left")
        cfg.set_string("mainwin/history_forward_ak", "<alt>Right")
        cfg.set_string("mainwin/history_reload_ak", "<ctrl>r")
    if cfg.get_int("app/rcfileversion") <= 6:
        cfg.set_list("config/lessoncollections", ['solfege', 'user'])
    if cfg.get_int("app/rcfileversion") <= 7:
        cfg.set_int("rhythm/countin_perc", 80)
    if cfg.get_int("app/rcfileversion") <= 8:
        cfg.del_key("singinterval/highest_tone")
        cfg.del_key("singinterval/lowest_tone")
        cfg.del_key("melodicinterval/highest_tone")
        cfg.del_key("melodicinterval/lowest_tone")
        cfg.del_key("harmonicinterval/highest_tone")
        cfg.del_key("harmonicinterval/lowest_tone")
    if cfg.get_int("app/rcfileversion") <= 9:
        cfg.del_section("mainwin")
    if cfg.get_int("app/rcfileversion") <= 10:
        cfg.del_section("lessoncollections")
        cfg.del_key("config/lessoncollections")
        for n in cfg.iterate_sections():
            cfg.del_key("%s/lessoncollection" % n)
            cfg.del_key("%s/lessonfile" % n)
    if cfg.get_int("app/rcfileversion") <= 11:
        for s in ('rhythm', 'rhythmtapping2'):
            cfg.del_key("%s/countin_perc" % s)
            cfg.del_key("%s/rhythm_perc" % s)
    if cfg.get_int("app/rcfileversion") <= 12:
        cfg.del_key("sound/card_info")
    if cfg.get_int("app/rcfileversion") <= 13:
        cfg.del_key("config/lowest_instrument_velocity")
        cfg.del_key("config/middle_instrument_velocity")
        cfg.del_key("config/highest_instrument_velocity")
        cfg.del_key("config/preferred_instrument_velocity")
    if cfg.get_int("app/rcfileversion") <= 14:
        # We have to split the midi_to_wav_cmd into two strings, and
        # moving the options to *_options, so that midi_to_wav_cmd only
        # have the name of the binary. This to allow binaries in dirs
        # with spaces.
        for k in ("midi_to_wav", "wav_to_mp3", "wav_to_ogg"):
            v = cfg.get_string("app/%s_cmd" % k).split(" ")
            cfg.set_string("app/%s_cmd" % k, v[0])
            cfg.set_string("app/%s_cmd_options" % k, " ".join(v[1:]))
    if cfg.get_int("app/rcfileversion") <= 15:
        for k in ("midi", "wav", "mp3", "ogg"):
            v = cfg.get_string("sound/%s_player" % k).split(" ")
            cfg.set_string("sound/%s_player" % k, v[0])
            cfg.set_string("sound/%s_player_options" % k,
                " ".join(v[1:]))
    if cfg.get_int("app/rcfileversion") < 17:
        v = cfg.get_string("app/frontpage").split("/")
        if v[0] == u"exercises" and v[1] != u"standard":
            cfg.set_string("app/frontpage",
                           u"/".join([v[0], u"standard"] + v[1:]))
    if cfg.get_int("app/rcfileversion") < 18:
        cfg.del_key("gui/web_browser_as_help_browser")
    if cfg.get_int("app/rcfileversion") < 19:
        for ex in ('singinterval', 'melodicinterval'):
            if cfg.get_int("%s/maximum_number_of_intervals" % ex) == 10:
                cfg.set_int("%s/maximum_number_of_intervals" % ex, 12)
    if cfg.get_int("app/rcfileversion") < 20:
        cfg.del_key("gui/reserved_vspace")
    if cfg.get_int("app/rcfileversion") < 21:
        for ex in ("melodicinterval", "harmonicinterval"):
            i = cfg.get_int("%s/inputwidget" % ex)
            if i > 0:
                cfg.set_int("%s/inputwidget" % ex, i + 1)


    cfg.set_int("app/rcfileversion", rcfileversion)
    try:
        a = mpd.notename_to_int(cfg.get_string("user/lowest_pitch"))
        b = mpd.notename_to_int(cfg.get_string("user/highest_pitch"))
    except mpd.InvalidNotenameException:
        if cfg.get_string("user/sex") == "male":
            cfg.set_string("user/highest_pitch", "e'")
            cfg.set_string("user/lowest_pitch", "c")
        else:
            cfg.set_string("user/highest_pitch", "e''")
            cfg.set_string("user/lowest_pitch", "c'")


class SolfegeApp(cfg.ConfigUtils):
    def __init__(self, options):
        """
        options -- command line options parsed by optparse
        """
        cfg.ConfigUtils.__init__(self, 'solfege-app')
        lessonfile.MusicBaseClass.temp_dir = tempfile.mkdtemp(prefix="solfege-")
        os.environ['SOLFEGETEMPDIR'] = lessonfile.MusicBaseClass.temp_dir
        # test_mode is when we are running a test from the Tests menu
        self.m_test_mode = False
        self.m_options = options
        self.m_teachers = {}
        self.m_running_exercise = None
        self.m_sound_init_exception = None
        #
        self.m_userman_language = "C"
        for lang in i18n.langs():
            if os.path.isdir(os.path.join('help', lang)):
                self.m_userman_language = lang
                break
    def setup_sound(self):
        if sys.platform == 'win32' and \
                    cfg.get_string("sound/type") == "sequencer-device":
            # just in case c:\home\.solfegerc is wrong
            cfg.set_string("sound/type", "winsynth")
        if self.m_options.no_sound \
           or cfg.get_string("sound/type") == "fake-synth":
            soundcard.initialise_using_fake_synth(self.m_options.verbose_sound_init)
        elif cfg.get_string("sound/type") == "alsa-sequencer":
            if alsaseq:
                try:
                    clientid, portid = self.get_list("sound/alsa-client-port")
                except ValueError:
                    clientid, portid = (None, None)
                try:
                    soundcard.initialise_alsa_sequencer((clientid, portid),
                            self.m_options.verbose_sound_init)
                except alsaseq.SequencerError, e:
                    logging.debug("initialise_alsa_sequencer failed. Using fake synth.")
                    self.display_sound_init_error_message(e)
                    soundcard.initialise_using_fake_synth(True)
                    return
            else:
                if solfege.splash_win:
                    solfege.splash_win.hide()
                gu.dialog_ok(_("The pyalsa Python module is missing"),
                    solfege.win,
                    _("Solfege was configured to use the Python modules from www.alsa-project.org, but the modules were not found. You must reconfigure sound in the preferences window (Ctrl-F12) or restart Solfege in a way that it finds the modules."))
                soundcard.initialise_using_fake_synth(True)
                if solfege.splash_win:
                    solfege.splash_win.show()
        elif cfg.get_string("sound/type") == "winsynth":
            try:
                soundcard.initialise_winsynth(cfg.get_int("sound/synth_number"),
                      verbose_init=self.m_options.verbose_sound_init)
            except ImportError, e:
                self.display_sound_init_error_message(e)
                cfg.set_string("sound/type", "fake-synth")
                soundcard.initialise_using_fake_synth(True)
                return
            except RuntimeError, e:
                # We can get here if winmidi.output_devices() in winsynth
                # __init__ returns no devices. Don't know when, but it could
                # happen.
                gu.display_exception_message(e)
                cfg.set_string("sound/type", "fake-synth")
                soundcard.initialise_using_fake_synth(True)
                return
            if cfg.get_int("sound/synth_number") != soundcard.synth.m_devnum:
                solfege.win.display_error_message2(_("MIDI setup"), _("MIDI Device %(olddev)i not available. Will use device %(newdev)i.") % {'olddev': cfg.get_int("sound/synth_number"), 'newdev': soundcard.synth.m_devnum})
                cfg.set_int("sound/synth_number", soundcard.synth.m_devnum)
        elif cfg.get_string("sound/type") == "external-midiplayer":
            soundcard.initialise_external_midiplayer(
                    verbose_init=self.m_options.verbose_sound_init)
            soundcard.synth.error_report_cb = solfege.win.display_error_message
        elif cfg.get_string("sound/type") == '':
            solfege.win.display_error_message(
                _("You should configure sound from the 'Sound' page "
                  "of the preferences window."))
        elif cfg.get_string("sound/type") == "sequencer-device":
            try:
                soundcard.initialise_devicefile(
                             cfg.get_string("sound/device_file"),
                             cfg.get_int("sound/synth_number"),
                             verbose_init=self.m_options.verbose_sound_init)
            except (soundcard.SoundInitException, OSError, ImportError), e:
                self.m_sound_init_exception = e
                soundcard.initialise_using_fake_synth(True)
        if cfg.get_string("programs/csound") == "AUTODETECT":
            for p in osutils.find_csound_executables():
                cfg.set_string("programs/csound", p)
                break
            else:
                # If not csound binary was found, then we set the string empty.
                # This means that autodetection will only happen the first time
                # you run the program. But later will newly installed binaries
                # be shown in the combo box of the preferences window.
                cfg.set_string("programs/csound", "")
        if cfg.get_string("programs/mma") == "AUTODETECT":
            for p in osutils.find_mma_executables(cfg.get_list("app/win32_ignore_drives")):
                cfg.set_string("programs/mma", p)
                break
            else:
                cfg.set_string("programs/mma", "")
    def display_sound_init_error_message(self, e):
        if isinstance(e, soundcard.SoundInitException):
            solfege.win.display_error_message(
            """%s""" % str(e).decode(locale.getpreferredencoding(), 'replace'))
        elif isinstance(e, ImportError):
            solfege.win.display_error_message2(str(e), _("You should configure sound from the preferences window, and try to use an external midi player. Or try to recompile the program and check for error messages to see why the module is not built."))
        elif getattr(e, 'errno', None) == errno.EACCES:
            solfege.win.display_error_message(
                "The sound init failed: %s\n"
                "The errno EACCES indicates that you don't have write "
                "permission to the device."
                % str(e).decode(locale.getpreferredencoding(), 'replace'))
        elif getattr(e, 'errno', None) == errno.EBUSY:
            solfege.win.display_error_message(
                "The sound init failed: %s\n"
                "It seems like some other program is using the device. You "
                "should try to quit that other program and restart Solfege."
                % str(e).decode(locale.getpreferredencoding(), 'replace'))
        else:
            solfege.win.display_error_message(
                "The sound init failed: %s\n"
                "You should configure sound from the 'Sound' page of "
                "the preferences window.\n\n"
                "It is also possible that the OS sound setup is incorrect."
                % str(e).decode(locale.getpreferredencoding(), 'replace'))
    def please_help_me(self):
        if isinstance(solfege.win.get_view(), abstract.Gui):
            # If the view visible is an exercise, when we check if the
            # lesson file header define a specific help page.
            if self.m_teachers[self.m_running_exercise].m_P.header.help:
                self.handle_href('%s.html' % self.m_teachers[self.m_running_exercise].m_P.header.help)
            else:
                # if not, we display help page named the same as the
                # exercise module
                self.handle_href('%s.html' % solfege.win.m_viewer)
    def show_exercise_theory(self):
        if self.m_teachers[self.m_running_exercise].m_P.header.theory:
            solfege.win.display_docfile("%s.html" % self.m_teachers[self.m_running_exercise].m_P.header.theory)
    def _practise_lessonfile(self, filename, urlobj=None):
        """
        return the module name.
        """
        module = lessonfile.infocache.get(filename, 'module')
        if self.m_running_exercise:
            solfege.win.box_dict[self.m_running_exercise].on_end_practise()
        if not lessonfile.is_uri(filename):
            # Since the file is in ~/.solfege/exercises we must check
            # if the user have written his own exercise module
            if os.path.exists(os.path.normpath(os.path.join(
                            os.path.dirname(filename),
                            "..", "modules", u"%s.py" % module))):
                module = u"user:%s/%s" % (
                    os.path.dirname(filename).split(os.sep)[-2],
                    module)
        if module not in self.m_teachers:
            self.create_teacher(module)
        if module not in solfege.win.box_dict:
            solfege.win.initialise_exercise(self.m_teachers[module])
        self.m_teachers[module].set_lessonfile(filename)
        if self.m_teachers[module].m_P:
            solfege.win.activate_exercise(module, urlobj)
        self.m_running_exercise = module
        self.m_teachers[module].g_view = solfege.win.box_dict[module]
        solfege.win.show_help_on_current()
        return module
    def practise_lessonfile(self, filename):
        def cleanup():
            module = lessonfile.infocache.get(filename, 'module')
            self.m_teachers[module].m_P = None
            solfege.win.box_dict[module].practise_box.set_sensitive(False)
            solfege.win.box_dict[module].config_box.set_sensitive(False)
            solfege.win.box_dict[module].action_area.set_sensitive(False)
            solfege.win.box_dict[module].std_buttons_end_practise()
        try:
            module = self._practise_lessonfile(filename)
        except (lessonfile.LessonfileParseException,
                dataparser.DataparserException,
                parsetree.ParseTreeException,
                IOError), e:
            cleanup()
            gu.display_exception_message(e, lessonfile=filename)
            return
        if 'm_discards' in dir(self.m_teachers[module].m_P):
            for msg in self.m_teachers[module].m_P.m_discards:
                print >> sys.stderr, msg
        solfege.win.box_dict[module].practise_box.set_sensitive(True)
        solfege.win.box_dict[module].config_box.set_sensitive(True)
        solfege.win.box_dict[module].action_area.set_sensitive(True)
        solfege.win.box_dict[module].on_start_practise()
        w = solfege.win.g_ui_manager.get_widget("/Menubar/HelpMenu/PerExerciseHelp/HelpTheory")
        if w:
            w.set_sensitive(bool(self.m_teachers[module].m_P.header.theory))
        return module
    def test_lessonfile(self, filename):
        self.m_test_mode = True
        module = self.practise_lessonfile(filename)
        solfege.win.enter_test_mode()
    def handle_href(self, href):
        u = urlparse(href)
        if u.scheme:
            try:
                webbrowser.open_new(href)
            except Exception, e:
                solfege.win.display_error_message2(_("Error opening web browser"), str(e))
        else:
            solfege.win.display_docfile(u.path)
    def create_teacher(self, modulename):
        """
        Create the teacher in 'modulename' and add it to self.m_teachers.
        """
        m = self.import_module(modulename)
        self.m_teachers[modulename] = m.Teacher(modulename)
    def import_module(self, modulename):
        """
        If prefixed with "solfege:"

          user:collection/modulename

        collection is the directory name in
        ~/.solfege/exercises/collection/modulename
        and "user:" is just a prefix to show that the module name
        is in the users directory.

        If a plain string with not prefix, it is one of the standard modules
        included with Solfege.

        Return the imported module
        """
        if modulename.startswith("user:"):
            collection = modulename[len("user:"):].split(os.sep)[0]
            module_dir = os.path.join(filesystem.user_data(),
                                      "exercises", collection, "modules")
            sys.path.insert(0, module_dir)
            m = __import__(modulename.split("/")[1])
            reload(m)
            del sys.path[0]
        else:
            m = __import__("solfege.exercises.%s" % modulename, fromlist=("solfege.exercises.%s" % modulename,), level=0)
        return m
    def reset_exercise(self, w=None):
        """
        Call on_end_practise, and then on_start_practise in
        the currently active exercise, if we have a exercise.
        """
        if isinstance(solfege.win.get_view(), abstract.Gui):
            solfege.win.get_view().on_end_practise()
            solfege.win.get_view().on_start_practise()
    def quit_program(self):
        if isinstance(solfege.win.get_view(), abstract.Gui):
            g = solfege.win.get_view()
            # Check that the lesson file has a header, because if the
            # user tries to quit the program after parsing a bad lesson
            # file, we cannot call end_practise() without risking more
            # exceptions.
            if g.m_t.m_P and hasattr(g.m_t.m_P, 'header'):
                g.on_end_practise()
        try:
            cfg.sync()
        except IOError, e:
            gu.display_exception_message(e)
        try:
            solfege.db.conn.commit()
        except sqlite3.ProgrammingError, e:
            gu.display_exception_message(e)
        try:
            solfege.db.conn.close()
        except sqlite3.ProgrammingError, e:
            gu.display_exception_message(e)
        if soundcard.synth:
            soundcard.synth.close()
        shutil.rmtree(lessonfile.MusicBaseClass.temp_dir, True)
    def export_training_set(self, export_data, export_dir, output_format,
                            name_track_by_question):
        """
        This function requires a program that can create WAV files
        from MIDI files and MP3 files from WAV.
        """
        def delay(n, tempo):
            """
            tempo is a dict of two integers
            """
            track = mpd.Track()
            track.set_bpm(*tempo)#self.get_int('config/default_bpm'))
            track.note(mpd.Rat(n, 4), 80, 0)
            soundcard.synth.play_track(track)
        track_idx = 0
        num = sum([x['count'] for x in export_data])
        # MainWin will set this to True if the user want to cancel
        # the export.
        self.m_abort_export = False
        report = reportlib.Report()
        report.append(reportlib.Heading(1, "Exported exercises"))
        table = reportlib.Table()
        report.append(table)
        for lesson_info in export_data:
            filename = lesson_info['filename']
            module = lessonfile.infocache.get(filename, 'module')
            if module not in self.m_teachers:
                self.create_teacher(module)
            p = self.m_teachers[module].lessonfileclass()
            p.parse_file(lessonfile.uri_expand(filename))
            for c in range(lesson_info['count']):
                trackname = "track-%i"
                if module == 'idbyname':
                    p.select_random_question()
                    if p.header.lesson_heading:
                        s = p.header.lesson_heading
                    else:
                        s = p.header.title
                    table.append_row("%i" % track_idx,
                                     p.get_question().name,
                                     s)
                    if name_track_by_question:
                        trackname = "%s-%%i" % p.get_name()
                    soundcard.start_export(os.path.join(
                            export_dir, "%s.mid" % trackname % track_idx))
                    for n in range(lesson_info.get('repeat', 1)):
                        p.play_question()
                        if n != lesson_info.get('repeat', 1) - 1:
                            if 'delay' in lesson_info:
                                delay(lesson_info['delay'], p.get_tempo())
                    soundcard.end_export()
                elif module in ('melodicinterval', 'harmonicinterval'):
                    t = self.m_teachers[module]
                    t.set_lessonfile(filename)
                    t.start_practise()
                    t.new_question("c", "c''")
                    t.q_status = t.QSTATUS_SOLVED
                    try:
                        table.append_row("%i" % track_idx, "%s" % utils.int_to_intervalname(t.m_interval))
                        if name_track_by_question:
                            trackname = "%%i-%s.mid" % utils.int_to_intervalname(t.m_interval)
                    except AttributeError:
                        table.append_row("%i" % track_idx, "%s" % (" + ".join([utils.int_to_intervalname(q, False, True) for q in t.m_question])))
                        if name_track_by_question:
                            trackname = "%%i-%s.mid" % ("+".join([utils.int_to_intervalname(q, False, True) for q in t.m_question]))
                    soundcard.start_export(os.path.join(
                            export_dir, "%s.mid" % trackname % track_idx))
                    for n in range(lesson_info.get('repeat', 1)):
                        t.play_question()
                        if n != lesson_info.get('repeat', 1) - 1:
                            if 'delay' in lesson_info:
                                delay(lesson_info['delay'],
                                    (self.get_int('config/default_bpm'), 4))
                    soundcard.end_export()
                else:
                    logging.warning("export_training_set:ignoring exercise with module='%s'", module)
#####
                def do_convert(from_format, to_format):
                    """
                    Return False if we think the convert failed.
                    """
                    app_cfg_name = "app/%s_to_%s_cmd" % (from_format, to_format)
                    if from_format == 'midi':
                        from_ext = 'mid'
                    else:
                        from_ext = from_format
                    to_ext = to_format
                    if not cfg.get_string(app_cfg_name):
                        solfege.win.display_error_message2("Config variable not defined", "The missing or empty variable was '%s'" % app_cfg_name)
                        return False
                    try:
                        inout = {
                            'in': os.path.join(export_dir,
                                    "%s.%s" % (trackname % track_idx, from_ext)),
                            'out': os.path.join(export_dir,
                                    "%s.%s" % (trackname % track_idx, to_ext))}
                        opts = cfg.get_string(app_cfg_name + '_options').split(" ")
                        opts = [x % inout for x in opts]
                        # For some reasong setting the executable arg does
                        # not work for Python 2.5.2
                        try:
                            subprocess.call(
                                [cfg.get_string(app_cfg_name)] + opts)
                        except OSError, e:
                            raise osutils.BinaryForMediaConvertorException(app_cfg_name,
                                cfg.get_string(app_cfg_name), e)

                        if os.path.exists(os.path.join(export_dir, "%s.%s" % (trackname % track_idx, to_ext))):
                            os.remove(os.path.join(export_dir, "%s.%s" % (trackname % track_idx, from_ext)))
                        else:
                            # This means that the program failed to generate
                            # the WAV file. We set output_format to 'midi'
                            # because we don't want to display this error for
                            # every single file.
                            output_format = 'midi'
                            solfege.win.display_error_message2("External program must have failed", "The file in %(from)s format was not generated from the %(to)s file as expected. Please check your setup in the preferences window (CTRL-F12)." % {'to':to_format.upper(), 'from': from_format.upper()})
                    except (TypeError, KeyError):
                        solfege.win.display_error_message2("%(from)s to %(to)s config error", "There was a format string error. Will not generate WAV files. Please check the app/midi_to_wav_cmd config variable." % {'from': from_format, 'to': to_format})
                        output_format = 'midi'
                    return True
#####
                if output_format in ('mp3', 'wav', 'ogg'):
                    do_convert('midi', 'wav')
                if output_format in ('mp3', 'ogg'):
                    if not do_convert('wav', output_format):
                        output_format = 'wav'
                track_idx += 1
                yield 1.0 * track_idx / num
                if self.m_abort_export:
                    del self.m_abort_export
                    return
        reportlib.HtmlReport(report, os.path.join(export_dir, "toc.html"))
    def sheet_gen_questions(self, count, sdict):
        """
        count -- how many questions should we generate. We use this value
                 and not sdict['count'] because sometimes the app has some
                 questions, and just need a few more.
        """
        module = lessonfile.infocache.get(sdict['filename'], 'module')
        if module not in self.m_teachers:
            self.create_teacher(module)
        p = self.m_teachers[module].lessonfileclass()
        p.parse_file(lessonfile.uri_expand(sdict['filename']))
        if module == 'idbyname':
            for x in self._sheet_gen_question_idbyname(p, count, sdict):
                yield x
        else:
            assert module in ('harmonicinterval', 'melodicinterval')
            for x in self._sheet_gen_question_interval(module, p, count, sdict):
                yield x
    def _sheet_gen_question_idbyname(self, p, count, sdict):
        """
        yield count dicts, where each dict contain the data needed to
        print both the teachers and the students question.
        """
        counts = {}.fromkeys(range(len(p.m_questions)), 0)
        for x in range(count):
            while 1:
                p.select_random_question()
                if counts[p._idx] >= 1.0 * sdict['count'] / len(p.m_questions):
                    continue
                counts[p._idx] += 1
                break
            ret = {'question': {}, 'answer': {}}
            if sdict['qtype'] == 0:
                ret['question']['name'] = "...."
                ret['answer']['name'] = p.get_question().name
                ret['question']['music'] = p.get_lilypond_code()
                ret['answer']['music'] = p.get_lilypond_code()
                yield ret
            else:
                assert sdict['qtype'] == 1
                ret['question']['name'] = p.get_question().name
                ret['answer']['name'] = p.get_question().name
                ret['answer']['music'] = p.get_lilypond_code()
                ret['question']['music'] = p.get_lilypond_code_first_note()
                yield ret
    def _sheet_gen_question_interval(self, module, p, count, sdict):
        # FIXME in the idbyname we count how many times each question
        # has been selected, to get an even selection. We don't do it
        # here at the moment, because we need to descide what we really want.
        teacher = self.m_teachers[module]
        teacher.set_lessonfile(sdict['filename'])
        teacher.start_practise()
        for x in range(count):
            teacher.new_question("c'", "c''")
            # quick hack to use this for both melodic and harmonic intervals
            if module == 'melodicinterval':
                teacher.m_interval = teacher.m_question[0]
            teacher.q_status = teacher.QSTATUS_SOLVED
            ret = {'question': {}, 'answer': {}}
            if sdict['qtype'] == 0:
                ret['question']['name'] = "...."
                ret['answer']['name'] = mpd.Interval.new_from_int(abs(teacher.m_interval)).get_name()
                ret['question']['music'] = r"\score{" \
                        r" { %s %s }" \
                        r"\layout { "\
                        r"  ragged-last = ##t " \
                        r"  \context { \Staff " \
                        r'\remove "Time_signature_engraver" } }' \
                        r"}" % (
                    teacher.m_tonika.get_octave_notename(),
                    (teacher.m_tonika + mpd.Interval.new_from_int(teacher.m_interval)).get_octave_notename())
                ret['answer']['music'] = ret['question']['music']
                yield ret
            else:
                assert sdict['qtype'] == 1
                ret['question']['name'] = mpd.Interval.new_from_int(abs(teacher.m_interval)).get_name()
                ret['answer']['name'] = mpd.Interval.new_from_int(abs(teacher.m_interval)).get_name()
                ret['question']['music'] = r"\score{ { %s s4 s4} "\
                       r"\layout{ "\
                       r"  ragged-last = ##t "\
                       r"  \context { \Staff "\
                       r'     \remove "Time_signature_engraver" } }'\
                       r"}" % teacher.m_tonika.get_octave_notename()
                ret['answer']['music'] = r"\score{ { %s %s } "\
                       r"\layout{ "\
                       r"  ragged-last = ##t "\
                       r"  \context { \Staff "\
                       r'     \remove "Time_signature_engraver" } }'\
                       r"}" % (
                    teacher.m_tonika.get_octave_notename(),
                    (teacher.m_tonika + teacher.m_interval).get_octave_notename())
                yield ret

