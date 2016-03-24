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

import logging
import os
import shutil
import sys

from gi.repository import GObject
from gi.repository import Gtk

from solfege import abstract
from solfege import cfg
from solfege import filesystem
from solfege import gu
from solfege import languages
from solfege import mpd
from solfege import notenamespinbutton
from solfege import osutils
from solfege import soundcard
from solfege import utils
from solfege import winlang
from solfege.instrumentselector import nInstrumentSelector, InstrumentConfigurator
import solfege

try:
    import solfege.soundcard.alsa_sequencer
except ImportError:
    solfege.soundcard.alsa_sequencer = None


if sys.platform == 'win32':
    try:
        from solfege.soundcard import winmidi
    except ImportError, e:
        print >> sys.stderr, "Loading winmidi.pyd failed:"
        print >> sys.stderr, e
        winmidi = None

class ConfigWindow(Gtk.Dialog, cfg.ConfigUtils):
    def on_destroy(self, widget, e):
        solfege.win.g_config_window.destroy()
        solfege.win.g_config_window = None
    def __init__(self):
        Gtk.Dialog.__init__(self, _("GNU Solfege Preferences"),
             solfege.win, 0,
             (Gtk.STOCK_HELP, Gtk.ResponseType.HELP, Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE))
        cfg.ConfigUtils.__init__(self, 'configwindow')
        self.connect('response', self.apply_and_close)
        # We do this so that the window is only hidden when the
        # user click on the close button provided by the window manager.
        self.connect('delete-event', self.on_destroy)#lambda w, e: True)

        hbox = Gtk.HBox()
        hbox.set_spacing(gu.hig.SPACE_LARGE)
        hbox.set_border_width(gu.hig.SPACE_SMALL)
        self.vbox.pack_start(hbox, True, True, 0)

        frame = Gtk.Frame()
        self.g_pages = Gtk.TreeStore(str)
        self.g_pview = Gtk.TreeView(self.g_pages)
        self.g_pview.set_headers_visible(False)
        hbox.pack_start(frame, False, False, 0)
        frame.add(self.g_pview)

        self.g_page_box = Gtk.HBox()
        hbox.pack_start(self.g_page_box, True, True, 0)
        self.m_page_mapping = {}

        def cursor_changed(treeview):
            path, col = treeview.get_cursor()
            if not path:
                return
            path = tuple(path)
            for key, page in self.m_page_mapping.items():
                if key == path:
                    page.show()
                else:
                    page.hide()
            self.m_page_mapping[path].show_all()
        tvcol = Gtk.TreeViewColumn("Col 0")
        self.g_pview.append_column(tvcol)
        cell = Gtk.CellRendererText()
        tvcol.pack_start(cell, True)
        tvcol.add_attribute(cell, 'text', 0)
        hbox.show_all()

        self.create_midi_config()
        self.create_user_config()
        self.create_external_programs_config()
        self.create_gui_config()
        self.create_practise_config()
        self.create_sound_config()
        self.create_statistics_config()
        self.g_pview.connect('cursor-changed', cursor_changed)
    def new_page_box(self, parent, heading):
        page_vbox = Gtk.VBox()
        page_vbox.set_spacing(gu.hig.SPACE_MEDIUM)
        self.g_page_box.pack_start(page_vbox, True, True, 0)
        it = self.g_pages.append(parent, [heading])
        self.m_page_mapping[tuple(self.g_pages.get_path(it))] = page_vbox
        return it, page_vbox
    def create_midi_config(self):
        it, page_vbox = self.new_page_box(None, _("Instruments"))
        vbox, category_vbox = gu.hig_category_vbox(_("Tempo"))
        page_vbox.pack_start(vbox, False, False, 0)
        sizegroup = Gtk.SizeGroup(Gtk.SizeGroupMode.HORIZONTAL)

        tempo_hbox = Gtk.Box(spacing=6)
        self.g_default_bpm = gu.nSpinButton('config', 'default_bpm',
            Gtk.Adjustment(self.get_int('config/default_bpm'), 10, 500, 1, 10))
        self.g_arpeggio_bpm = gu.nSpinButton('config', 'arpeggio_bpm',
            Gtk.Adjustment(self.get_int('config/arpeggio_bpm'), 10, 500, 1, 10))
        for text, widget in [(_("_Default:") ,self.g_default_bpm),
                             (_("A_rpeggio:") ,self.g_arpeggio_bpm)]:
            label = Gtk.Label(_("BPM"))
            tempo_hbox.pack_start(
                gu.hig_label_widget(text, [widget, label], None),
                False, False, 0)
            label.set_tooltip_text(_("Beats per minute"))
        category_vbox.pack_start(tempo_hbox, False, False, 0)

        box, category_vbox = gu.hig_category_vbox(_("Preferred Instrument"))
        page_vbox.pack_start(box, False, False, 0)
        self.g_instrsel = nInstrumentSelector('config',
                        'preferred_instrument', None)
        category_vbox.pack_start(self.g_instrsel, False, False, 0)

        box, category_vbox = gu.hig_category_vbox(_("Chord Instruments"))
        page_vbox.pack_start(box, False, False, 0)
        self.g_instrument_configurator  \
              = InstrumentConfigurator("config", 3,
                    _("Use different instruments for chords and harmonic intervals"))
        category_vbox.pack_start(self.g_instrument_configurator, False, False, 0)

        vbox, category_box = gu.hig_category_vbox(_("Percussion Instruments"))
        page_vbox.pack_start(vbox, False, False, 0)
        category_box.pack_start(gu.hig_label_widget(
            _("Count in:"),
            gu.PercussionNameButton("config", "countin_perc", "Claves"),
            sizegroup, True, True), True, True, 0)
        category_box.pack_start(gu.hig_label_widget(
            _("Rhythm:"),
            gu.PercussionNameButton("config", "rhythm_perc", "Side Stick"),
            sizegroup, True, True), False, False, 0)
    def create_user_config(self):
        it, page_vbox = self.new_page_box(None, _("User"))
        box, category_vbox = gu.hig_category_vbox(_("User's Vocal Range"))
        page_vbox.pack_start(box, False, False, 0)
        sizegroup = Gtk.SizeGroup(Gtk.SizeGroupMode.HORIZONTAL)

        self.g_highest_singable = notenamespinbutton.NotenameSpinButton(
            self.get_string('user/highest_pitch'))
        box = gu.hig_label_widget(_("Highest pitch:"),
                                  self.g_highest_singable,
                                  sizegroup)
        category_vbox.pack_start(box, True, True, 0)

        self.g_lowest_singable = notenamespinbutton.NotenameSpinButton(
            self.get_string('user/lowest_pitch'))
        box = gu.hig_label_widget(_("Lowest pitch:"),
                                  self.g_lowest_singable,
                                  sizegroup)
        category_vbox.pack_start(box, True, True, 0)
        notenamespinbutton.nNotenameRangeController(
                  self.g_lowest_singable, self.g_highest_singable,
                  mpd.LOWEST_NOTENAME, mpd.HIGHEST_NOTENAME,
                  'user', 'lowest_pitch', 'highest_pitch')


        box, category_vbox = gu.hig_category_vbox(_("Sex"))
        page_vbox.pack_start(box, False, False, 0)
        self.g_sex_male = Gtk.RadioButton.new_with_mnemonic(None, _("_Male"))
        self.g_sex_male.connect('toggled', lambda w: self.set_string('user/sex', 'male'))
        category_vbox.pack_start(self.g_sex_male, False, False, 0)
        self.g_sex_female = Gtk.RadioButton.new_with_mnemonic_from_widget(self.g_sex_male, _("_Female or child"))
        self.g_sex_female.connect('toggled', lambda w: self.set_string('user/sex', 'female'))
        category_vbox.pack_start(self.g_sex_female, False, False, 0)
        if self.get_string('user/sex') == 'female':
            self.g_sex_female.set_active(True)
    def create_external_programs_config(self):
        it, page_vbox = self.new_page_box(None, _("External Programs"))
        box, category_vbox = gu.hig_category_vbox(_("Converters"))
        page_vbox.pack_start(box, False, False, 0)
        sizegroup = Gtk.SizeGroup(Gtk.SizeGroupMode.HORIZONTAL)

        # midi_to_wav
        self.g_wav_convertor = gu.sComboBox(
            'app', 'midi_to_wav_cmd', ['timidity'])
        self.g_wav_convertor_options = gu.sComboBox(
            'app', 'midi_to_wav_cmd_options', ["-Ow %(in)s -o %(out)s"])
        self.g_wav_convertor_options.set_entry_text_column(0)
        category_vbox.pack_start(
            gu.hig_label_widget(_("MIDI to WAV:"),
                (self.g_wav_convertor, self.g_wav_convertor_options),
                 sizegroup),
            False, False, 0)

        # wav_to_mp3
        self.g_mp3_convertor = gu.sComboBox(
            'app', 'wav_to_mp3_cmd', ["lame"])
        self.g_mp3_convertor_options = gu.sComboBox(
            'app', 'wav_to_mp3_cmd_options', ["%(in)s %(out)s"])
        category_vbox.pack_start(
            gu.hig_label_widget(_("WAV to MP3:"),
                (self.g_mp3_convertor, self.g_mp3_convertor_options),
                sizegroup),
            False, False, 0)

        # wav_to_ogg
        self.g_ogg_convertor = gu.sComboBox(
            "app", "wav_to_ogg_cmd", ["oggenc"])
        self.g_ogg_convertor_options = gu.sComboBox(
            "app", "wav_to_ogg_cmd_options", ["%(in)s"])
        category_vbox.pack_start(
            gu.hig_label_widget(_("WAV to OGG:"),
                (self.g_ogg_convertor, self.g_ogg_convertor_options),
                sizegroup),
            False, False, 0)

        self.add_gui_for_external_programs(page_vbox)
        ########
        # Misc #
        ########
        sizegroup = Gtk.SizeGroup(Gtk.SizeGroupMode.HORIZONTAL)

        box, category_vbox = gu.hig_category_vbox(_("Miscellaneous"))
        page_vbox.pack_start(box, False, False, 0)

        # CSound_("Musical MIDI Accompaniment:")
        for binary, label, bins in (
            ("csound", _("CSound:"), osutils.find_csound_executables()),
            ("mma", "MMA:", osutils.find_mma_executables(
                cfg.get_list("app/win32_ignore_drives"))),
            ("lilypond-book", _("Lilypond-book:"),
             osutils.find_progs(("lilypond-book", "lilypond-book.py"))),
            ("latex", "Latex:", osutils.find_progs(("latex",))),
            ("text-editor", _("Text editor:"), osutils.find_progs(("sensible-editor", "gvim", "gedit", "emacs", "notepad.exe"))),
            ):
            combo = gu.sComboBox("programs", binary, bins)
            def binary_changed_cb(widget, binary):
                widget.warning.props.visible = not bool(
                    osutils.find_progs((cfg.get_string('programs/%s' % binary),)))
            combo.warning = Gtk.Image()
            combo.warning.set_tooltip_text(_("Not found. Much of GNU Solfege will run fine without this program. You will get a message when the program is required, and the user manual will explain what you need it for."))
            combo.warning.set_from_stock(Gtk.STOCK_DIALOG_WARNING,
                                              Gtk.IconSize.SMALL_TOOLBAR)
            box = gu.hig_label_widget(label,
                                      [combo, combo.warning],
                                      sizegroup, True, True)
            category_vbox.pack_start(box, True, True, 0)
            combo.warning.props.no_show_all = True
            binary_changed_cb(combo, binary)
            combo.connect('changed', binary_changed_cb, binary)
    def create_gui_config(self):
        i_iter, page_vbox = self.new_page_box(None, _("Interface"))

        self.g_mainwin_user_resizeable = gu.nCheckButton('gui',
          'mainwin_user_resizeable', _("_Resizeable main window"))
        page_vbox.pack_start(self.g_mainwin_user_resizeable, False, False, 0)

        # Combobox to select language
        hbox = Gtk.HBox()
        hbox.set_spacing(6)
        label = Gtk.Label()
        label.set_text_with_mnemonic(_("Select _language:"))
        hbox.pack_start(label, False, False, 0)
        self.g_language = Gtk.ComboBoxText()
        for n in languages.languages:
            self.g_language.append_text(n)
        label.set_mnemonic_widget(self.g_language)
        if sys.platform == 'win32':
            lang = winlang.win32_get_langenviron()
            if lang in languages.languages:
                idx = languages.languages.index(lang)
            elif lang == 'C':
                idx = languages.C_locale_idx
            else:
                idx = 0
        else:
            lang = cfg.get_string('app/lc_messages')
            if lang in languages.languages:
                idx = languages.languages.index(lang)
            elif lang == 'C':
                idx = languages.C_locale_idx
            else:
                idx = 0
        self.g_language.set_active(idx)
        def f(combobox):
            if combobox.get_active() == languages.C_locale_idx:
                lang = "C"
            else:
                lang = languages.languages[combobox.get_active()]
            cfg.set_string('app/lc_messages', lang)
            if sys.platform == 'win32':
                if combobox.get_active():
                    winlang.win32_put_langenviron(lang)
                else:
                    winlang.win32_put_langenviron(None)
        self.g_language.connect_after('changed', f)
        hbox.pack_start(self.g_language, False, False, 0)
        page_vbox.pack_start(hbox, False, False, 0)
        l = Gtk.Label(label=_("You have to restart the program for the language change to take effect."))
        l.set_alignment(0.0, 0.5)
        page_vbox.pack_start(l, False, False, 0)

        self.create_idtone_accels_config(i_iter)
        self.create_interval_accels_config(i_iter)
    def create_idtone_accels_config(self, parent):
        it, page_vbox = self.new_page_box(parent, _("Identify tone keyboard accelerators"))
        self.g_idtone_accels = Gtk.ListStore(GObject.TYPE_STRING,
            GObject.TYPE_STRING)
        notenames = ('c', 'cis', 'd', 'dis', 'e', 'f', 'fis',
                     'g', 'gis', 'a', 'ais', 'b')
        for notename in notenames:
            self.g_idtone_accels.append((
                solfege.mpd.MusicalPitch.new_from_notename(notename).get_user_notename(),
                cfg.get_string('idtone/tone_%s_ak' % notename)))
        self.g_treeview = Gtk.TreeView(self.g_idtone_accels)
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("Note name"), renderer, text=0)
        self.g_treeview.append_column(column)
        renderer = Gtk.CellRendererAccel()
        renderer.set_property('editable', True)
        def acc_ff(renderer, path, accel_key, accel_mods, hw_key):
            is_unique = True
            for notename in notenames:
                if (notename != notenames[int(path)]
                    and cfg.get_string('idtone/tone_%s_ak' % notename) == unichr(accel_key)):
                    is_unique = False
                    break
            if not is_unique:
                gu.dialog_ok(_(u"The accelerator in use for the tone “%s”. You have to choose another key.") % solfege.mpd.MusicalPitch.new_from_notename(notename).get_user_notename(), parent=self, msgtype=Gtk.MessageType.ERROR)
                return
            it = self.g_idtone_accels.get_iter(path)
            cfg.set_string('idtone/tone_%s_ak' % notenames[int(path)], unichr(accel_key))
            self.g_idtone_accels.set(it, 1, unichr(accel_key))
            return True
        renderer.connect('accel-edited', acc_ff)
        column = Gtk.TreeViewColumn(_i("keyboard|Key"), renderer, text=1)
        self.g_treeview.append_column(column)
        page_vbox.pack_start(self.g_treeview, True, True, 0)
        layouts = {'ascii': (_('ASCII'), u'awsedfujikol'),
                   'dvorak': (_('Dvorak'), u'a,o.eughctrn'),
        }
        hbox = Gtk.HBox()
        page_vbox.pack_start(hbox, False, False, 0)
        def set_buttons(widget, layout):
            v = layouts[layout][1]
            idx = 0
            it = self.g_idtone_accels.get_iter_first()
            while True:
                self.g_idtone_accels.set_value(it, 1, v[idx])
                cfg.set_string('idtone/tone_%s_ak' % notenames[idx], v[idx])
                it = self.g_idtone_accels.iter_next(it)
                idx += 1
                if not it:
                    break
        for key in layouts:
            btn = Gtk.Button(layouts[key][0])
            btn.connect('clicked', set_buttons, key)
            hbox.pack_start(btn, True, True, 0)
    def create_interval_accels_config(self, parent):
        it, page_vbox = self.new_page_box(parent, _("Interval keyboard accelerators"))
        self.g_interval_accels = Gtk.ListStore(GObject.TYPE_STRING,
            GObject.TYPE_STRING)
        intervals = ['minor2', 'major2', 'minor3', 'major3',
                     'perfect4', 'diminished5', 'perfect5', 'minor6',
                     'major6', 'minor7', 'major7', 'perfect8',
                     'minor9', 'major9', 'minor10', 'major10']
        for interval in intervals:
            self.g_interval_accels.append((
                mpd.Interval.new_from_int(intervals.index(interval)).get_name(),
                cfg.get_string('interval_input/%s' % interval)))
        self.g_intervals_treeview = Gtk.TreeView(self.g_interval_accels)
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("Interval"), renderer, text=0)
        self.g_intervals_treeview.append_column(column)
        renderer = Gtk.CellRendererAccel()
        renderer.set_property('editable', True)
        def acc_ff(renderer, path, accel_key, accel_mods, hw_key):
            is_unique = True
            for interval in intervals:
                if (interval != intervals[int(path)]
                    and cfg.get_string('interval_input/%s' % interval) == unichr(accel_key)):
                    is_unique = False
                    break
            if not is_unique:
                gu.dialog_ok(_(u"The accelerator in use for “%s”. You have to choose another key.") % mpd.Interval.new_from_int(intervals.index(interval)).get_name(), parent=self, msgtype=Gtk.MessageType.ERROR)
                return
            it = self.g_interval_accels.get_iter(path)
            cfg.set_string('interval_input/%s' % intervals[int(path)], unichr(accel_key))
            self.g_interval_accels.set(it, 1, unichr(accel_key))
            return True
        renderer.connect('accel-edited', acc_ff)
        column = Gtk.TreeViewColumn(_i("keyboard|Key"), renderer, text=1)
        self.g_intervals_treeview.append_column(column)
        page_vbox.pack_start(self.g_intervals_treeview, True, True, 0)
        hbox = Gtk.HBox()
        page_vbox.pack_start(hbox, False, False, 0)
        layouts = {'ascii': (_('ASCII'), u'1qaz2wsx3edc4rfv'),
                   'dvorak': (_('Dvorak'), u"1'a;2,oq3.ej4puk"),
        }
        def set_buttons(widget, layout):
            v = layouts[layout][1]
            idx = 0
            it = self.g_interval_accels.get_iter_first()
            while True:
                self.g_interval_accels.set_value(it, 1, v[idx])
                cfg.set_string('interval_input/%s' % intervals[idx], v[idx])
                it = self.g_interval_accels.iter_next(it)
                idx += 1
                if not it:
                    break
        for key in layouts:
            btn = Gtk.Button(layouts[key][0])
            btn.connect('clicked', set_buttons, key)
            hbox.pack_start(btn, True, True, 0)
    def create_practise_config(self):
        it, page_vbox = self.new_page_box(None, _("Practise"))
        self.g_picky_on_new_question = gu.nCheckButton('config', 'picky_on_new_question', _("_Not allow new question before the old is solved"))
        page_vbox.pack_start(self.g_picky_on_new_question, False, False, 0)

        self.g_autorepeat_if_wrong = gu.nCheckButton('config', 'auto_repeat_question_if_wrong_answer', _("_Repeat question if the answer was wrong"))
        page_vbox.pack_start(self.g_autorepeat_if_wrong, False, False, 0)

        self.g_expert_mode = gu.nCheckButton('gui',
                'expert_mode', _("E_xpert mode"))
        self.g_expert_mode.connect('toggled', solfege.app.reset_exercise)
        page_vbox.pack_start(self.g_expert_mode, False, False, 0)
    def create_sound_config(self):
        if sys.platform == 'win32':
            self.create_win32_sound_page()
        else:
            self.create_linux_sound_page()
    def create_statistics_config(self):
        it, page_vbox = self.new_page_box(None, _("Statistics"))
        box, category_vbox = gu.hig_category_vbox(_("Statistics from 3.15 and older"))
        page_vbox.pack_start(box, False, False, 0)
        self.g_old_stat_info = Gtk.Label()
        self.g_old_stat_info.set_line_wrap(True)
        self.g_old_stat_info.set_alignment(0.0, 0.5)
        category_vbox.pack_start(self.g_old_stat_info, False, False, 0)
        #
        self.g_delete_old_statistics = Gtk.Button(stock=Gtk.STOCK_DELETE)
        self.g_delete_old_statistics.connect('clicked', self.delete_obsolete_statistics)
        category_vbox.pack_start(self.g_delete_old_statistics, False, False, 0)
        box, category_vbox = gu.hig_category_vbox(_("Statistics"))
        page_vbox.pack_start(box, False, False, 0)
        self.g_stat_info = Gtk.Label()
        self.g_stat_info.set_line_wrap(True)
        self.g_stat_info.set_alignment(0.0, 0.5)
        category_vbox.pack_start(self.g_stat_info, False, False, 0)
        b = Gtk.Button(stock=Gtk.STOCK_DELETE)
        b.connect('clicked', self.delete_statistics)
        category_vbox.pack_start(b, False, False, 0)
        self.update_statistics_info()
        self.update_old_statistics_info()
    def add_gui_for_external_programs(self, page_vbox):
        box, category_vbox = gu.hig_category_vbox(_("Audio File Players"))
        page_vbox.pack_start(box, False, False, 0)
        format_info = {}
        if sys.platform != 'win32':
            format_info = {'wav': {
                 # testfile is a file in lesson-files/share
                 'testfile': 'fifth-small-220.00.wav',
                 'label': _("WAV:"),
                 # players is a list of tuples. The tuple has to or more
                 # items. The first is the binary, and the rest is possible
                 # sets of command line options that might work.
                 # '/path/to/player', 'comandline', '
                 'players': [
                        ('gst-launch', 'playbin uri=file://%s',
                                       'filesrc location=%s ! wavparse ! alsasink'),
                        ('play', ''),
                        ('aplay', ''),
                        ('esdplay', ''),
                 ],
                }
            }
        format_info['midi'] = {
             'testfile': 'fanfare.midi',
             'label': _("MIDI:"),
             'players': [
                         ('gst-launch', 'playbin uri=file://%s',
                                        'filesrc location=exercises/standard/lesson-files/share/fanfare.midi ! wildmidi ! alsasink'),
                         ('timidity', '-idqq %s'),
                         ('drvmidi', ''),
                         ('playmidi', ''),
             ],
            }
        format_info['mp3'] = {
             'testfile': 'fanfare.mp3',
             'label': _("MP3:"),
             'players': [
                        ('gst-launch', 'playbin uri=file://%s',
                                       'filesrc location=%s ! mad ! alsasink'),
                        ('mpg123', ''),
                        ('alsaplayer', ''),
             ],
            }
        format_info['ogg'] = {
             'testfile': 'fanfare.ogg',
             'label': _("OGG:"),
             'players': [
                        ('gst-launch', 'playbin uri=file://%s',
                                       'filesrc location=%s ! oggdemux ! vorbisdec ! audioconvert ! alsasink'),
                        ('ogg123', ''),
                        ('alsaplayer', ''),
             ],
            }
        sizegroup = Gtk.SizeGroup(Gtk.SizeGroupMode.HORIZONTAL)
        for formatid, format in format_info.items():
            combo = gu.sComboBox('sound', '%s_player' % formatid, [p[0] for p in format['players']])
            combo.set_tooltip_text(_("Enter the name of the program. An absolute path is required only if the executable is not found on the PATH."))
            combo.opts = gu.sComboBox('sound', '%s_player_options' % formatid, 'NOT YET!')
            combo.opts.set_tooltip_text(_("The command line options required. Write %s where you want the name of the file to be played. Or omit it to have it added to the end of the string."))

            def _changed(widget, formatid):
                if widget.get_active() != -1:
                    model = widget.opts.get_model()
                    model.clear()
                    format = format_info[formatid]
                    for player_options in format['players'][widget.get_active()][1:]:
                        model.append([player_options])
                    widget.opts.get_child().set_text(format['players'][widget.get_active()][1])
                widget.testbutton.set_sensitive(bool(
                    osutils.find_progs((widget.get_child().get_text().decode("utf-8"),))))

            combo.connect('changed', _changed, formatid)
            testbutton = Gtk.Button(_("_Test").replace("_", ""))
            testbutton.set_tooltip_text(_("This button is clickable only if the binary is found."))
            combo.testbutton = testbutton
            testbutton.connect('clicked', self.test_XXX_player,
                           formatid, format['testfile'])
            testbutton.set_sensitive(bool(
                    osutils.find_progs((combo.get_child().get_text().decode("utf-8"),))))
            box = gu.hig_label_widget(format['label'],
                                      [combo, combo.opts, testbutton],
                                      sizegroup, True, True)
            category_vbox.pack_start(box, True, True, 0)
    def test_XXX_player(self, w, typeid, testfile):
        try:
            soundcard.play_mediafile(typeid, os.path.join('exercises/standard/lesson-files/share', testfile))
        except osutils.BinaryBaseException, e:
            solfege.win.display_error_message2(e.msg1, e.msg2)
    def popup_alsa_connection_list(self, widget):
        connection_list = soundcard.alsa_sequencer.get_connection_list()
        if connection_list:
            menu = Gtk.Menu()
            for clientid, portid, clientname, portname, labeltext in connection_list:
                item = Gtk.MenuItem(labeltext)
                menu.append(item)
                def ff(widget, clientid, portid):
                    self.g_alsa_device.set_label(widget.get_child().get_text())
                    self.m_gui_client_port = (clientid, portid)
                    self.g_alsa_radio.set_active(True)
                item.connect('activate', ff, clientid, portid)
            menu.show_all()
            menu.popup(None, None, None, None, 0, Gtk.get_current_event_time())
    def create_linux_sound_page(self):
        it, page_vbox = self.new_page_box(None, _("Sound Setup"))
        #############
        # midi setup
        #############

        self.g_fakesynth_radio = gu.RadioButton(None, _("_No sound"), None)
        page_vbox.pack_start(self.g_fakesynth_radio, False, False, 0)

        ### ALSA
        self.m_gui_client_port = False
        hbox = gu.bHBox(page_vbox, False)
        self.g_alsa_radio = gu.RadioButton(self.g_fakesynth_radio,
              _("Use ALSA _device"), None)
        hbox.pack_start(self.g_alsa_radio, False, False, 0)

        self.g_alsa_device = Gtk.Button()
        self.g_alsa_device.connect('clicked', self.popup_alsa_connection_list)
        hbox.pack_start(self.g_alsa_device, False, False, 0)
        if solfege.soundcard.alsa_sequencer:
            connections = solfege.soundcard.alsa_sequencer.get_connection_list()
            for v in connections:
                if v[0:2] == self.get_list("sound/alsa-client-port"):
                    self.g_alsa_device.set_label(v[-1])
                    self.m_gui_client_port = v[0:2]
                    break
            else:
                if connections:
                    self.m_gui_client_port = connections[-1][0:2]
                    self.g_alsa_device.set_label(connections[-1][-1])
                else:
                    self.g_alsa_device.set_label("")
        else:
            self.g_alsa_device.set_sensitive(False)
            self.g_alsa_radio.set_sensitive(False)
            label = Gtk.Label(label="Disabled because the pyalsa Python module was not found.")
            label.show()
            hbox.pack_start(label, False, False, 0)
        ### OSS
        hbox = gu.bHBox(page_vbox, False)
        self.g_device_radio = gu.RadioButton(self.g_fakesynth_radio,
              _("Use OSS _device"), None)
        hbox.pack_start(self.g_device_radio, False, False, 0)

        self.g_device_file = gu.sComboBox('sound', 'device_file',
            ['/dev/sequencer', '/dev/sequencer2', '/dev/music'])
        self.g_synth_num = Gtk.SpinButton()
        self.g_synth_num.set_adjustment(Gtk.Adjustment(0, 0, 100, 1, 1))
        self.g_synth_num.set_value(self.get_int('sound/synth_number'))
        hbox.pack_start(self.g_device_file, False, False, 0)
        hbox.pack_start(self.g_synth_num, False, False, 0)

        ###
        hbox = gu.bHBox(page_vbox, False)
        self.g_midiplayer_radio = gu.RadioButton(self.g_fakesynth_radio,
             _("Use _external MIDI player"), None)
        hbox.pack_start(self.g_midiplayer_radio, False, False, 0)

        if self.get_string("sound/type") == "external-midiplayer":
            self.g_midiplayer_radio.set_active(True)
        elif self.get_string("sound/type") == "sequencer-device":
            self.g_device_radio.set_active(True)
        elif self.get_string("sound/type") == "alsa-sequencer":
            self.g_alsa_radio.set_active(True)
        else:
            self.g_fakesynth_radio.set_active(True)

        gu.bButton(page_vbox, _("_Test"), self.on_apply_and_play_test_sound, False)
    def create_win32_sound_page(self):
        it, page_vbox = self.new_page_box(None, _("Sound Setup"))
        #############
        # midi setup
        #############
        txt = Gtk.Label(_("""Solfege has two ways to play MIDI files. It is recommended to use Windows multimedia output. An external MIDI player can be useful if your soundcard lacks a hardware synth, in which case you have to use a program like timidity to play the music."""))
        txt.set_line_wrap(1)
        txt.set_justify(Gtk.Justification.FILL)
        txt.set_alignment(0.0, 0.0)
        page_vbox.pack_start(txt, False, False, 0)

        self.g_fakesynth_radio = gu.RadioButton(None, _("_No sound"), None)
        page_vbox.pack_start(self.g_fakesynth_radio, False, False, 0)

        hbox = gu.bHBox(page_vbox, False)
        self.g_device_radio = gu.RadioButton(self.g_fakesynth_radio,
              _("_Windows multimedia output:"), None)
        self.g_synth = Gtk.ComboBoxText()
        if winmidi:
            for devname in winmidi.output_devices():
                #FIXME workaround of the bug
                # http://code.google.com/p/solfege/issues/detail?id=12
                if devname is None:
                    self.g_synth.append_text("FIXME bug #12")
                else:
                    self.g_synth.append_text(devname)
        self.g_synth.set_active(self.get_int('sound/synth_number') + 1)
        hbox.pack_start(self.g_device_radio, False, False, 0)
        hbox.pack_start(self.g_synth, False, False, 0)

        hbox = gu.bHBox(page_vbox, False)
        self.g_midiplayer_radio = gu.RadioButton(self.g_fakesynth_radio,
             _("Use _external MIDI player"), None)
        hbox.pack_start(self.g_midiplayer_radio, False, False, 0)

        if self.get_string("sound/type") == "external-midiplayer":
            self.g_midiplayer_radio.set_active(True)
        elif self.get_string("sound/type") == "winsynth":
            self.g_device_radio.set_active(True)
        else:
            self.g_fakesynth_radio.set_active(True)

        gu.bButton(page_vbox, _("_Test"), self.on_apply_and_play_test_sound, False)
    def set_gui_from_config(self):
        if self.get_string("sound/type") == "fake-synth":
            self.g_fakesynth_radio.set_active(True)
        elif self.get_string("sound/type") == "external-midiplayer":
            self.g_midiplayer_radio.set_active(True)
        elif self.get_string("sound/type") == "alsa-sequencer":
            if solfege.soundcard.alsa_sequencer:
                self.g_alsa_radio.set_active(True)
                p = self.get_list("sound/alsa-client-port")
                for idx, k in enumerate(solfege.soundcard.alsa_sequencer.get_connection_list()):
                    if p[0] == k[0] and p[1] == k[1]:
                        self.g_alsa_device.set_label(k[-1])
                        break
            else:
                self.set_string("sound/type", "fake-synth")
                self.g_fakesynth_radio.set_active(True)
        else:
            assert self.get_string("sound/type") in ("winsynth", "sequencer-device")
            self.g_device_radio.set_active(True)
    def apply_and_close(self, w, response):
        if response ==  Gtk.ResponseType.DELETE_EVENT:
            self.set_gui_from_config()
        elif response == Gtk.ResponseType.HELP:
            solfege.app.handle_href("preferences-window.html")
            return
        else:
            if self.on_apply() == -1:
                self.set_gui_from_config()
                return
        self.hide()
    def on_apply_and_play_test_sound(self, *w):
        if self.on_apply() != -1:
            self.set_gui_from_config()
            self.play_midi_test_sound()
    def play_midi_test_sound(self):
        try:
            utils.play_music(r"""
            \staff\relative c{
              c16 e g c e, g c e g, c e g c4
            }
            \staff{
              c4 e g8 e c4
            }
            """, 130, 0, 100)
        # Here we are only cathing exceptions we know the MidiFileSynth
        # can raise. Maybe we should catch something from the Sequencer
        # synths too?
        except osutils.BinaryBaseException, e:
            solfege.win.display_error_message2(e.msg1, e.msg2)
    def on_apply(self, *v):
        """Returns -1 if sound init fails."""
        if soundcard.synth:
            soundcard.synth.close()
        if self.g_midiplayer_radio.get_active():
            soundcard.initialise_external_midiplayer()
            soundcard.synth.error_report_cb = solfege.win.display_error_message
        elif self.g_device_radio.get_active():
            try:
                if sys.platform == 'win32':
                    soundcard.initialise_winsynth(self.g_synth.get_active() - 1)
                else:
                    soundcard.initialise_devicefile(
                        self.g_device_file.get_child().get_text(),
                        self.g_synth_num.get_value_as_int())
            except (soundcard.SoundInitException, OSError, ImportError), e:
                solfege.app.display_sound_init_error_message(e)
                return -1
        elif solfege.soundcard.alsa_sequencer and self.g_alsa_radio.get_active():
            if self.m_gui_client_port:
                try:
                    soundcard.initialise_alsa_sequencer(self.m_gui_client_port)
                except solfege.soundcard.alsa_sequencer.alsaseq.SequencerError, e:
                    logging.debug("initialise_alsa_sequencer(%s) failed: %s", self.m_gui_client_port, str(e))
                    solfege.app.display_sound_init_error_message(e)
                    return -1
            else:
                return -1
        else: # no sound
            assert self.g_fakesynth_radio.get_active()
            soundcard.initialise_using_fake_synth(0)
        if self.g_midiplayer_radio.get_active():
            self.set_string("sound/type", "external-midiplayer")
        elif self.g_device_radio.get_active():
            if sys.platform == "win32":
                self.set_string("sound/type", "winsynth")
            else:
                self.set_string("sound/type", "sequencer-device")
        elif solfege.soundcard.alsa_sequencer and self.g_alsa_radio.get_active():
            self.set_string("sound/type", "alsa-sequencer")
            self.set_list("sound/alsa-client-port", self.m_gui_client_port)
        else:
            assert self.g_fakesynth_radio.get_active()
            self.set_string("sound/type", "fake-synth")
        if sys.platform != 'win32':
            self.set_string("sound/device_file", self.g_device_file.get_child().get_text())
        if soundcard.synth.m_type_major in ('OSS', 'win32'):
            self.set_int("sound/synth_number", soundcard.synth.m_devnum)
            # we set the spin just in case m_devnum was changed by the
            # soundcard setup code, if it was out of range
            if sys.platform != 'win32':
                self.g_synth_num.set_value(soundcard.synth.m_devnum)
            else:
                self.g_synth.set_active(soundcard.synth.m_devnum + 1)
    def delete_statistics(self, *w):
        if gu.dialog_delete(_("Delete statistics and test results?"), self,
                _(u"This will delete and recreate the file «%s».") % solfege.db.get_statistics_filename()):
            restart = False
            # We need to test for this, because get_view() can also return the front page
            if isinstance(solfege.win.get_view(), abstract.Gui):
                solfege.win.get_view().on_end_practise()
                restart = True
            solfege.db.reset_database()
            if restart:
                solfege.win.get_view().on_start_practise()
                if solfege.win.get_view().m_t.m_P and solfege.win.get_view().m_t.m_statistics:
                    solfege.db.validate_stored_statistics(solfege.win.get_view().m_t.m_P.m_filename)
        self.update_statistics_info()
    def delete_obsolete_statistics(self, *w):
        if gu.dialog_delete(_("Delete obsolete statistics?"), self,
                _(u"This will delete the directory «%s».") % os.path.join(filesystem.app_data(), u"statistics")):
            try:
                shutil.rmtree(os.path.join(filesystem.app_data(), u"statistics"))
            except OSError, e:
                gu.display_exception_message(e)
            self.update_old_statistics_info()
    def update_old_statistics_info(self):
        path = os.path.join(filesystem.app_data(), u'statistics')
        if os.path.exists(path):
            count = 1 # count app_data()/statistics too
        else:
            count = 0
        for dirpath, dirnames, filenames in os.walk(path):
            count += len(dirnames) + len(filenames)
        if count:
            self.g_old_stat_info.set_text(_("You have %i files and directories storing statistics in the old format that only Solfege 3.14 and older will use. These files are not useful any more unless you want to downgrade to Solfege 3.14.") % count)
        else:
            self.g_old_stat_info.set_text(_("No obsolete statistics found."))
        self.g_delete_old_statistics.set_sensitive(bool(count))
    def update_statistics_info(self):
        self.g_stat_info.set_text(_("Statistics of %(practise_count)i practise sessions and %(test_count)i tests from %(exercises)i different exercises.") % solfege.db.get_statistics_info())

