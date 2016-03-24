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

import solfege


import webbrowser
import textwrap
# We move x-www-browser to the end of the list because on my
# debian etch system, the browser does will freeze solfege until
# I close the browser window.
try:
    i = webbrowser._tryorder.index("x-www-browser")
    webbrowser._tryorder.append(webbrowser._tryorder[i])
    del webbrowser._tryorder[i]
except ValueError:
    pass

import sys
import traceback
import locale
import os
import urllib
import shutil

try:
    from pyalsa import alsaseq
except ImportError:
    alsaseq = None

from solfege import winlang
from solfege import buildinfo
from solfege.esel import FrontPage, TestsView, SearchView

from gi.repository import Gtk
from gi.repository import Gdk

from solfege import utils
from solfege import i18n

class SplashWin(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, Gtk.WindowType.POPUP)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_resizable(True)
        frame = Gtk.Frame()
        frame.set_shadow_type(Gtk.ShadowType.OUT)
        self.add(frame)
        vbox = Gtk.VBox()
        vbox.set_border_width(20)
        frame.add(vbox)
        l = Gtk.Label(label=_("Starting GNU Solfege %s") % buildinfo.VERSION_STRING)
        l.set_name("Heading1")
        vbox.pack_start(l, True, True, 0)
        l = Gtk.Label(label="http://www.solfege.org")
        vbox.pack_start(l, True, True, 0)
        self.g_infolabel = Gtk.Label(label='')
        vbox.pack_start(self.g_infolabel, True, True, 0)
        self.show_all()
    def show_progress(self, txt):
        self.g_infolabel.set_text(txt)
        while Gtk.events_pending():
            Gtk.main_iteration()

from solfege.configwindow import ConfigWindow
from solfege.profilemanager import ChangeProfileDialog
from solfege import gu
from solfege import cfg
from solfege import mpd
from solfege import lessonfile
from solfege import download_pyalsa
from solfege import statistics
from solfege import stock


from solfege import frontpage
from solfege import fpeditor
from solfege.trainingsetdlg import TrainingSetDialog
from solfege.practisesheetdlg import PractiseSheetDialog
from solfege import filesystem

class MusicViewerWindow(Gtk.Dialog):
    def __init__(self):
        Gtk.Dialog.__init__(self)
        self.set_default_size(500, 300)
        self.g_music_displayer = mpd.MusicDisplayer()
        self.vbox.pack_start(self.g_music_displayer, True, True, 0)
        b = gu.bButton(self.action_area, _("Close"), solfege.win.close_musicviewer)
        b.grab_focus()
        self.connect('destroy', solfege.win.close_musicviewer)
        self.show_all()
    def display_music(self, music):
        fontsize = cfg.get_int('config/feta_font_size=20')
        self.g_music_displayer.display(music, fontsize)


class MainWin(Gtk.Window, cfg.ConfigUtils):
    default_front_page = os.path.join(lessonfile.exercises_dir, 'learningtree.txt')
    debug_front_page = os.path.join(lessonfile.exercises_dir, 'debugtree.txt')
    def __init__(self, options, datadir):
        Gtk.Window.__init__(self, Gtk.WindowType.TOPLEVEL)
        self._vbox = Gtk.VBox()
        self._vbox.show()
        self.add(self._vbox)
        stock.SolfegeIconFactory(self, datadir)
        Gtk.Settings.get_default().set_property('gtk-button-images', True)
        cfg.ConfigUtils.__dict__['__init__'](self, 'mainwin')
        self.set_resizable(self.get_bool('gui/mainwin_user_resizeable'))
        self.add_watch('gui/mainwin_user_resizeable', lambda s: self.set_resizable(self.get_bool('gui/mainwin_user_resizeable')))
        self.connect('delete-event', self.quit_program)
        self.connect('key_press_event', self.on_key_press_event)
        self.g_about_window = None
        self.m_exercise = None
        self.m_viewer = None
        self.box_dict = {}
        self.g_config_window = None
        self.g_path_info_dlg = None
        self.g_musicviewer_window = None
        self.m_history = []
        self.g_ui_manager = Gtk.UIManager()
        self.m_action_groups = {
            'Exit': Gtk.ActionGroup('Exit'),
            'NotExit': Gtk.ActionGroup('NotExit'),
        }
        for a in self.m_action_groups.values():
            self.g_ui_manager.insert_action_group(a, 1)
        self.setup_menu()
        self.main_box = Gtk.VBox()
        self.main_box.show()
        self._vbox.pack_start(self.main_box, True, True, 0)
    def get_view(self):
        """
        Return the view that is currently visible.
        Raise KeyError if no view has yet been added.
        """
        return self.box_dict[self.m_viewer]
    def add_view(self, view, name):
        """
        Hide the current view.
        Add and view the new view.
        """
        assert name not in self.box_dict
        if self.m_viewer:
            self.get_view().hide()
        self.box_dict[name] = view
        self.main_box.pack_start(self.box_dict[name], True, True, 0)
        self.box_dict[name].show()
        self.m_viewer = name
    def show_view(self, name):
        """
        Return False if the view does not exist.
        Hide the current visible view, show the view named 'name' and
        return True.
        """
        if name not in self.box_dict:
            return False
        self.get_view().hide()
        self.m_viewer = name
        self.box_dict[name].show()
        return True
    def change_frontpage(self, filename):
        """
        Change to a different frontpage file.
        """
        self.set_string('app/frontpage', filename)
        self.load_frontpage()
    def load_frontpage(self):
        """
        Load the front page file set in the config database into
        solfege.app.m_frontpage_data
        """
        filename = self.get_string("app/frontpage")
        if filename == self.debug_front_page and not solfege.app.m_options.debug:
            self.set_string("app/frontpage", self.default_front_page)
            filename = self.default_front_page
        if not os.path.isfile(filename):
            filename = self.default_front_page
        try:
            solfege.app.m_frontpage_data = frontpage.load_tree(filename)
        except Exception, e:
            if solfege.splash_win:
                solfege.splash_win.hide()
            solfege.app.m_frontpage_data = frontpage.load_tree(self.default_front_page)
            self.set_string('app/frontpage', self.default_front_page)
            gu.dialog_ok(_("Loading front page '%s' failed. Using default page." % filename),
                secondary_text = "\n".join(traceback.format_exception(*sys.exc_info())))
            if solfege.splash_win:
                solfege.splash_win.show()
        self.display_frontpage()
    def setup_menu(self):
        self.m_action_groups['Exit'].add_actions([
          ('FileMenu', None, _('_File')),
          ('AppQuit', 'gtk-quit', None, None, None, self.quit_program),
        ])
        self.m_action_groups['NotExit'].add_actions([
          ('TheoryMenu', None, _('The_ory')),
          ('FrontPagesMenu', None, _('Sele_ct Front Page')),
          ('TheoryIntervals', None, _('_Intervals'), None, None,
            lambda o: solfege.app.handle_href('theory-intervals.html')),
          ('TreeEditor', None, _('_Edit Front Page'), None, None,
            self.do_tree_editor),
          ('ExportTrainingSet', None, _(u'E_xport Exercises to Audio Files…'), None, None,
            self.new_training_set_editor),
          ('EditPractiseSheet', None, _(u'Ear Training Test Pri_ntout…'), None, None,
            self.new_practisesheet_editor),
          ('ProfileManager', None, _("Profile _Manager"), None, None,
            self.open_profile_manager),
          ('OpenPreferencesWindow', 'gtk-preferences', None, '<ctrl>F12', None,
            self.open_preferences_window),
          ('HelpMenu', None, _('_Help')),
          ('Search', 'gtk-search', _('_Search Exercises'), '<ctrl>F', None,
              self.on_search_all_exercises),
          ('FrontPage', None, _('_Front Page'), 'F5', None,
              lambda w: self.display_frontpage()),
          ('TestsPage', None, _('_Tests Page'), 'F6', None,
              lambda w: self.display_testpage()),
          ('RecentExercises', None, _('_Recent Exercises'), 'F7', None,
              self.display_recent_exercises),
          ('RecentTests', None, _('_Recent Tests'), 'F8', None,
              self.display_recent_tests),
          ('UserExercises', None, _('_User Exercises'), 'F9', None,
              self.display_user_exercises),
          ('SetupPyAlsa', None, _("Download and compile ALSA modules"), None, None, self.setup_pyalsa),
          ('HelpHelp', 'gtk-help', _('_Help on the current exercise'), 'F1', None,
            lambda o: solfege.app.please_help_me()),
          ('HelpTheory', None, _('_Music theory on the current exercise'), 'F3', None, lambda o: solfege.app.show_exercise_theory()),
          ('HelpIndex', None, _('_User manual'), None, None,
            lambda o: solfege.app.handle_href('index.html')),
          ('HelpShowPathInfo', None, _('_File locations'), None,
            None, self.show_path_info),
          ('HelpOnline', None, _('_Mailing lists, web page etc.'), None, None,
            lambda o: solfege.app.handle_href('online-resources.html')),
          ('HelpDonate', None, _('_Donate'), None, None,
            lambda o: solfege.app.handle_href('http://www.solfege.org/donate/')),
          ('HelpReportingBugs', None, _('Reporting _bugs'), None, None,
            lambda o: solfege.app.handle_href('bug-reporting.html')),
          ('HelpAbout', 'gtk-about', None, None, None, self.show_about_window),
          ('ShowBugReports', None, _('_See your bug reports'), None, None,
            self.show_bug_reports),
        ])

        self.g_ui_manager.add_ui_from_file("ui.xml")

        self.add_accel_group(self.g_ui_manager.get_accel_group())
        hdlbox = Gtk.HandleBox()
        hdlbox.show()
        hdlbox.add(self.g_ui_manager.get_widget('/Menubar'))
        self._vbox.pack_start(hdlbox, False, False, 0)
        self.m_help_on_current_merge_id = None
    def create_frontpage_menu(self):
        """
        Create, or update if already existing, the submenu that let the
        user choose which front page file to display.
        """
        if self.m_frontpage_merge_id:
            self.g_ui_manager.remove_ui(self.m_frontpage_merge_id)
        actions = []
        old_dir = None
        s = "<menubar name='Menubar'><menu action='FileMenu'><menu action='FrontPagesMenu'>"
        for fn in frontpage.get_front_pages_list(solfege.app.m_options.debug):
            if solfege.splash_win:
                solfege.splash_win.show_progress(fn)
            if not frontpage.may_be_frontpage(fn):
                continue
            try:
                title = lessonfile.infocache.frontpage.get(fn, 'title')
            except TypeError:
                continue
            cur_dir = os.path.split(fn)[0]
            if old_dir != cur_dir:
                s += '<separator name="sep@%s"/>' % fn
                old_dir = cur_dir
            s += "<menuitem action='%s'/>\n" % fn
            if not self.m_action_groups['NotExit'].get_action(fn):
                actions.append((fn, None, lessonfile.infocache.frontpage.get(fn, 'title'), None, fn,
                lambda o, f=fn: self.change_frontpage(f)))
            else:
                action = self.m_action_groups['NotExit'].get_action(fn)
                action.props.label = lessonfile.infocache.frontpage.get(fn, 'title')
        s += "</menu></menu></menubar>"
        self.m_action_groups['NotExit'].add_actions(actions)
        self.m_frontpage_merge_id = self.g_ui_manager.add_ui_from_string(s)
    def show_help_on_current(self):
        """
        Show the menu entries for the exercise help and music theory
        pages on the Help menu.
        """
        if self.m_help_on_current_merge_id:
            return
        self.m_help_on_current_merge_id = self.g_ui_manager.add_ui_from_string("""
<menubar name='Menubar'>
  <menu action='HelpMenu'>
    <placeholder name='PerExerciseHelp'>
      <menuitem position='top' action='HelpHelp' />
      <menuitem action='HelpTheory' />
    </placeholder>
  </menu>
</menubar>""")
    def hide_help_on_current(self):
        """
        Hide the menu entries for the help and music theory pages on the
        Help menu.
        """
        if not self.m_help_on_current_merge_id:
            return
        self.g_ui_manager.remove_ui(self.m_help_on_current_merge_id)
        self.m_help_on_current_merge_id = None
    def show_bug_reports(self, *v):
        m = Gtk.Dialog(_("Question"), self, 0)
        m.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        m.add_button(Gtk.STOCK_OK, Gtk.ResponseType.OK)
        vbox = Gtk.VBox()
        m.vbox.pack_start(vbox, False, False, 0)
        vbox.set_spacing(18)
        vbox.set_border_width(12)
        l = Gtk.Label(label=_("Please enter the email used when you submitted the bugs:"))
        vbox.pack_start(l, False, False, 0)
        self.g_email = Gtk.Entry()
        m.action_area.get_children()[0].grab_default()
        self.g_email.set_activates_default(True)
        vbox.pack_start(self.g_email, False, False, 0)
        m.show_all()
        ret = m.run()
        m.destroy()
        if ret == Gtk.ResponseType.OK:
            params = urllib.urlencode({
                    'pagename': 'SITS-Incoming/SearchBugs',
                    'q': 'SITS-Incoming/"Submitter: %s"' % utils.mangle_email(self.g_email.get_text().decode("utf-8")()),
                })
            try:
                webbrowser.open_new("http://www.solfege.org?%s" % params)
            except Exception, e:
                self.display_error_message2(_("Error opening web browser"), str(e))
    def display_error_message2(self, text, secondary_text):
        """
        This is the new version of display_error_message, and it will
        eventually replace the old.
        """
        if solfege.splash_win and solfege.splash_win.props.visible:
            solfege.splash_win.hide()
            reshow_splash = True
        else:
            reshow_splash = False
        if not isinstance(text, unicode):
            text = text.decode(locale.getpreferredencoding(), 'replace')
        if not isinstance(secondary_text, unicode):
            secondary_text = secondary_text.decode(locale.getpreferredencoding(), 'replace')
        m = Gtk.MessageDialog(None, Gtk.DialogFlags.MODAL, Gtk.MessageType.ERROR,
                              Gtk.ButtonsType.CLOSE, text)
        if secondary_text:
            m.format_secondary_text(secondary_text)
        m.run()
        m.destroy()
        if reshow_splash:
            solfege.splash_win.show()
            while Gtk.events_pending():
                Gtk.main_iteration()
    def display_error_message(self, msg, title=None, secondary_text=None):
        if solfege.splash_win and solfege.splash_win.props.visible:
            solfege.splash_win.hide()
            reshow_splash = True
        else:
            reshow_splash = False
        if not isinstance(msg, unicode):
            msg = msg.decode(locale.getpreferredencoding(), 'replace')
        m = Gtk.MessageDialog(None, Gtk.DialogFlags.MODAL, Gtk.MessageType.ERROR,
                              Gtk.ButtonsType.CLOSE, None)
        m.set_markup(gu.escape(msg))
        if title:
            m.set_title(title)
        if secondary_text:
            m.format_secondary_text(secondary_text)
        m.run()
        m.destroy()
        if reshow_splash:
            solfege.splash_win.show()
            while Gtk.events_pending():
                Gtk.main_iteration()
    def show_path_info(self, w):
        if not self.g_path_info_dlg:
            self.g_path_info_dlg = Gtk.Dialog(_("_File locations").replace("_", ""), self,
                buttons=(Gtk.STOCK_OK, Gtk.ResponseType.ACCEPT))
            sc = Gtk.ScrolledWindow()
            sc.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
            self.g_path_info_dlg.vbox.pack_start(sc, True, True, 0)
            #
            vbox = gu.hig_dlg_vbox()
            sc.add_with_viewport(vbox)

            box1, box2 = gu.hig_category_vbox(_("_File locations").replace("_", ""))
            vbox.pack_start(box1, True, True, 0)
            sizegroup = Gtk.SizeGroup(Gtk.SizeGroupMode.HORIZONTAL)
            # statistics.sqlite
            # win32 solfegerc
            # win32 langenviron.txt
            box2.pack_start(gu.hig_label_widget(_("Solfege application data:"), Gtk.Label(label=filesystem.app_data()), sizegroup), False, False, 0)
            box2.pack_start(gu.hig_label_widget(_("Solfege user data:"), Gtk.Label(label=filesystem.user_data()), sizegroup), False, False, 0)
            box2.pack_start(gu.hig_label_widget(_("Solfege config file:"), Gtk.Label(label=filesystem.rcfile()), sizegroup), False, False, 0)
            box2.pack_start(gu.hig_label_widget(_("Solfege installation directory:"), Gtk.Label(label=os.getcwdu()), sizegroup), False, False, 0)
            box2.pack_start(gu.hig_label_widget(_("User manual in HTML format:"), Gtk.Label(label=os.path.join(os.getcwdu(), "help")), sizegroup), False, False, 0)
            box2.pack_start(gu.hig_label_widget("gtk:", Gtk.Label(label=str(Gtk)), sizegroup), False, False, 0)
            box2.pack_start(gu.hig_label_widget("pyalsa:", Gtk.Label(label=str(alsaseq)), sizegroup), False, False, 0)
            box2.pack_start(gu.hig_label_widget("PYTHONHOME", Gtk.Label(os.environ.get('PYTHONHOME', 'Not defined')), sizegroup), False, False, 0)
            self.g_path_info_dlg.show_all()
            def f(*w):
                self.g_path_info_dlg.hide()
                return True
            self.g_path_info_dlg.connect('response', f)
            self.g_path_info_dlg.connect('delete-event', f)
            sc.set_size_request(min(vbox.size_request().width + gu.hig.SPACE_LARGE * 2,
                                    Gdk.Screen.width() * 0.9),
                                vbox.size_request().height)
    def setup_pyalsa(self, widget):
        download_pyalsa.download()
    def show_about_window(self, widget):
        pixbuf = self.render_icon('solfege-icon', Gtk.IconSize.DIALOG)
        a = self.g_about_window = Gtk.AboutDialog()
        a.set_program_name("GNU Solfege")
        a.set_logo(pixbuf)
        a.set_website("http://www.solfege.org")
        a.set_version(buildinfo.VERSION_STRING)
        a.set_copyright("Copyright (C) 2013 Tom Cato Amundsen and others")
        a.set_license("\n".join((solfege.application.solfege_copyright, solfege.application.warranty)))
        # Using set_license_type causes the app to print warnings.
        #a.set_license_type(Gtk.License.GPL_3_0)
        a.set_authors(["Tom Cato Amundsen",
              'Giovanni Chierico %s' % _("(some lessonfiles)"),
              'Michael Becker %s' % _("(some lessonfiles)"),
              'Joe Lee %s' % _("(sound code for the MS Windows port)"),
              'Steve Lee %s' % _("(ported winmidi.c to gcc)"),
              'Thibaus Cousin %s' % _("(spec file for SuSE 8.2)"),
              'David Coe %s' %_("(spec file cleanup)"),
              'David Petrou %s' % _("(testing and portability fixes for FreeBSD)"),
              'Han-Wen Nienhuys %s' % _("(the music font from Lilypond)"),
              'Jan Nieuwenhuizen %s' % _("(the music font from Lilypond)"),
              'Davide Bonetti %s' % _("(scale exercises)"),
              ])
        a.set_documenters(["Tom Cato Amundsen",
                "Tom Eykens",
                ])
        if _("SOLFEGETRANSLATORS") == 'SOLFEGETRANSLATORS':
            a.set_translator_credits(None)
        else:
            a.set_translator_credits(_("SOLFEGETRANSLATORS"))
        self.g_about_window.run()
        self.g_about_window.destroy()
    def do_tree_editor(self, *v):
        """
        Open a front page editor editing the current front page.
        """
        fpeditor.Editor.edit_file(self.get_string("app/frontpage"))
    def post_constructor(self):
        self.m_frontpage_merge_id = None
        self.create_frontpage_menu()
        self.g_ui_manager.add_ui_from_file("help-menu.xml")
        if sys.platform != 'linux2':
            self.g_ui_manager.get_widget('/Menubar/HelpMenu/SetupPyAlsa').hide()
        if solfege.app.m_sound_init_exception is not None:
            if solfege.splash_win:
                solfege.splash_win.destroy()
                solfege.splash_win = None
            solfege.app.display_sound_init_error_message(solfege.app.m_sound_init_exception)
        # MIGRATION 3.9.0
        if sys.platform == "win32" \
            and os.path.exists(os.path.join(filesystem.get_home_dir(), "lessonfiles")) \
            and not os.path.exists(filesystem.user_lessonfiles()):
                if solfege.splash_win:
                    solfege.splash_win.hide()
                do_move = gu.dialog_yesno(_('In Solfege 3.9.0, the location where Solfege look for lesson files you have created was changed. The files has to be moved from "%(old)s" and into the folder "%(gnu)s" in your "%(doc)s" folder.\nMay I move the files automatically for you now?' % {
                    'doc':  os.path.split(os.path.split(filesystem.user_data())[0])[1],
                    'gnu':  os.path.join(filesystem.appname, 'lessonfiles'),
                    'old': os.path.join(filesystem.get_home_dir(), "lessonfiles"),
                  }), parent=self)
                if do_move:
                    try:
                        os.makedirs(filesystem.user_data())
                        shutil.copytree(os.path.join(filesystem.get_home_dir(), "lessonfiles"),
                                        os.path.join(filesystem.user_data(), "lessonfiles"))
                    except (OSError, shutil.Error), e:
                        gu.dialog_ok(_("Error while copying directory:\n%s" % e))
                    else:
                        gu.dialog_ok(_("Files copied. The old files has been left behind. Please delete them when you have verified that all files was copied correctly."))

                if solfege.splash_win:
                    solfege.splash_win.show()
        # MIGRATION 3.9.3 when we added langenviron.bat and in 3.11
        # we migrated to langenviron.txt because we does not use cmd.exe
        if sys.platform == 'win32' and winlang.win32_get_langenviron() != self.get_string('app/lc_messages'):
            gu.dialog_ok(_("Migrated old language setup. You might have to restart the program all translated messages to show up."))
            winlang.win32_put_langenviron(self.get_string('app/lc_messages'))
        # MIGRATION 3.11.1: earlier editors would create new learning trees
        # below app_data() instead of user_data().
        if (sys.platform == "win32" and
            os.path.exists(os.path.join(filesystem.app_data(),
                                        "learningtrees"))):
            if not os.path.exists(os.path.join(filesystem.user_data(), "learningtrees")):
                os.makedirs(os.path.join(filesystem.user_data(), "learningtrees"))
            for fn in os.listdir(os.path.join(filesystem.app_data(), "learningtrees")):
                if not os.path.exists(os.path.join(filesystem.user_data(), "learningtrees", fn)):
                    shutil.move(os.path.join(filesystem.app_data(), "learningtrees", fn),
                            os.path.join(filesystem.user_data(), "learningtrees"))
                else:
                    # We add the .bak exstention if the file already exists.
                    shutil.move(os.path.join(filesystem.app_data(), "learningtrees", fn),
                            os.path.join(filesystem.user_data(), "learningtrees", u"%s.bak" % fn))
                os.rmdir(os.path.join(os.path.join(filesystem.app_data(), "learningtrees")))
        item = self.g_ui_manager.get_widget("/Menubar/FileMenu/FrontPagesMenu")
        item.connect('activate', lambda s: self.create_frontpage_menu())
        try:
            i18n.locale_setup_failed
            print >> sys.stderr, "\n".join(textwrap.wrap("Translations are disabled because your locale settings are broken. This is not a bug in GNU Solfege, so don't report it. The README file distributed with the program has some more details."))
        except AttributeError:
            pass
        for filename in lessonfile.infocache.frontpage.iter_old_format_files():
            gu.dialog_ok(_("Cannot load front page file"), None,
                _(u"The file «%s» is saved in an old file format. The file can be converted by editing and saving it with an older version of Solfege. Versions from 3.16.0 to 3.20.4 should do the job.") % filename)
    def activate_exercise(self, module, urlobj=None):
        self.show_view(module)
        # We need this test because not all exercises use a notebook.
        if self.get_view().g_notebook:
            if urlobj and urlobj.action in ['practise', 'config', 'statistics']:
                self.get_view().g_notebook.set_current_page(
                   ['practise', 'config', 'statistics'].index(urlobj.action))
            else:
                self.get_view().g_notebook.set_current_page(0)
        self.set_title("Solfege - " + self.get_view().m_t.m_P.header.title)
    def display_docfile(self, fn):
        """
        Display the HTML file named by fn in the help browser window.
        """
        for lang in solfege.app.m_userman_language, "C":
            filename = os.path.join(os.getcwdu(), u"help", lang, fn)
            if os.path.isfile(filename):
                break
        try:
            webbrowser.open(filename)
        except Exception, e:
            self.display_error_message2(_("Error opening web browser"), str(e))
    def display_user_exercises(self, w):
        col = frontpage.Column()
        page = frontpage.Page(_('User exercises'), col)
        curdir = None
        linklist = None
        for filename in lessonfile.infocache.iter_user_files(only_user_collection=True):
            dir, fn = os.path.split(filename)
            if dir != curdir:
                curdir = dir
                linklist = frontpage.LinkList(dir)
                col.append(linklist)
            linklist.append(filename)
        if os.path.isdir(filesystem.user_lessonfiles()):
            linklist = None
            col.append(frontpage.Paragraph(_('You really should move the following directory to a directory below <span font_family="monospace">%s</span>. Future versions of GNU Solfege will not display files in the old location. The user manual have details on where to place the files.') % os.path.join(filesystem.user_data(), u'exercises')))
            # Added just to be nice with people not moving their files from
            # pre 3.15.3 location:
            for filename in os.listdir(filesystem.user_lessonfiles()):
                if not linklist:
                    linklist = frontpage.LinkList(filesystem.user_lessonfiles())
                linklist.append(os.path.join(filesystem.user_lessonfiles(), filename))
            # only display the linklist if there are any files.
            if linklist:
                col.append(linklist)
        self.display_frontpage(page)
    def display_recent_exercises(self, w):
        data = frontpage.Page(_('Recent exercises'),
            [frontpage.Column(
                [frontpage.LinkList(_('Recent exercises'),
                   solfege.db.recent(8))])])
        self.display_frontpage(data, show_topics=True)
        self.get_view().g_searchbox.hide()
    def display_recent_tests(self, w):
        data = frontpage.Page(_('Recent tests'),
            [frontpage.Column(
                [frontpage.LinkList(_('Recent tests'),
                   solfege.db.recent_tests(8))])])
        self.display_testpage(data, show_topics=True)
        self.get_view().g_searchbox.hide()
    def display_testpage(self, data=None, show_topics=False):
        """
        Display the front page of the data  in solfege.app.m_frontpage_data
        """
        self.set_title("GNU Solfege - tests")
        if not self.show_view('testspage'):
            p = TestsView()
            p.connect('link-clicked', self.history_handler)
            self.add_view(p, 'testspage')
        self.get_view().g_searchbox.show()
        if not data:
            data = solfege.app.m_frontpage_data
        self.trim_history(self.get_view(), data)
        self.get_view().display_data(data, show_topics=show_topics)
    def on_search_all_exercises(self, widget=None):
        self.set_title("GNU Solfege")
        if not self.show_view('searchview'):
            self.add_view(SearchView(_('Search the exercise titles of all lesson files found by the program, not just the active front page with sub pages.')), 'searchview')
    def display_frontpage(self, data=None, show_topics=False):
        """
        Display the front page of the data  in solfege.app.m_frontpage_data
        """
        if solfege.app.m_options.profile:
            self.set_title("GNU Solfege - %s" % solfege.app.m_options.profile)
        else:
            self.set_title("GNU Solfege")
        if not self.show_view('frontpage'):
            p = FrontPage()
            p.connect('link-clicked', self.history_handler)
            self.add_view(p, 'frontpage')
        self.get_view().g_searchbox.show()
        if not data:
            data = solfege.app.m_frontpage_data
        self.trim_history(self.get_view(), data)
        self.get_view().display_data(data, show_topics=show_topics)
    def trim_history(self, new_viewer, new_page):
        # First check if the page we want to display is in m_history.
        # If so, we will trunkate history after it.
        for i, (viewer, page) in enumerate(self.m_history):
            if (new_viewer != viewer) or (new_page == page):
                self.m_history = self.m_history[:i]
                break
    def history_handler(self, *w):
        self.m_history.append(w)
    def initialise_exercise(self, teacher):
        """
        Create a Gui object for the exercise and add it to
        the box_dict dict.
        """
        assert teacher.m_exname not in self.box_dict
        self.get_view().hide()
        m = solfege.app.import_module(teacher.m_exname)
        self.add_view(m.Gui(teacher), teacher.m_exname)
    def on_key_press_event(self, widget, event):
        try:
            view = self.get_view()
        except KeyError:
            return
        if (event.type == Gdk.EventType.KEY_PRESS
            and event.get_state() & Gdk.ModifierType.MOD1_MASK == Gdk.ModifierType.MOD1_MASK# Alt key
            and event.keyval in (Gdk.KEY_KP_Left, Gdk.KEY_Left)
            and self.m_history
            and not solfege.app.m_test_mode):
            obj, page = self.m_history[-1]
            self.trim_history(obj, page)
            # Find the box_dict key for obj
            for k, o in self.box_dict.items():
                if o == obj:
                    obj.display_data(page)
                    self.show_view(k)
                    break
            return True
        view.on_key_press_event(widget, event)
    def open_profile_manager(self, widget=None):
        p = ChangeProfileDialog(solfege.app.m_options.profile)
        if p.run() == Gtk.ResponseType.ACCEPT:
            prof = p.get_profile()
        else:
            # The user presses cancel. This will use the same profile as
            # before, but if the user has renamed the active profile, then
            # we need to use the new name.
            prof = p.m_default_profile

        solfege.app.reset_exercise()
        solfege.app.m_options.profile = prof
        solfege.db.conn.commit()
        solfege.db.conn.close()
        if prof == None:
            prof = ''
        solfege.db = statistics.DB(None, profile=prof)
        cfg.set_string("app/last_profile", prof)
        self.display_frontpage()
        p.destroy()
    def open_preferences_window(self, widget=None):
        if not self.g_config_window:
            self.g_config_window = ConfigWindow()
            self.g_config_window.show()
        else:
            self.g_config_window.update_old_statistics_info()
            self.g_config_window.update_statistics_info()
            self.g_config_window.show()
    def quit_program(self, *w):
        can_quit = True
        for dlg in gu.EditorDialogBase.instance_dict.values():
            if dlg.close_window():
                dlg.destroy()
            else:
                can_quit = False
                break
        if can_quit:
            solfege.app.quit_program()
            Gtk.main_quit()
        else:
            return True
    def display_in_musicviewer(self, music):
        if not self.g_musicviewer_window:
            self.g_musicviewer_window = MusicViewerWindow()
            self.g_musicviewer_window.show()
        self.g_musicviewer_window.display_music(music)
    def close_musicviewer(self, widget=None):
        self.g_musicviewer_window.destroy()
        self.g_musicviewer_window = None
    def enter_test_mode(self):
        if 'enter_test_mode' not in dir(self.get_view()):
            gu.dialog_ok(_("The '%s' exercise module does not support test yet." % self.m_viewer))
            return
        self.m_action_groups['NotExit'].set_sensitive(False)
        self.g = self.get_view().g_notebook.get_nth_page(0)
        self.get_view().g_notebook.get_nth_page(0).reparent(self.main_box)
        self.get_view().g_notebook.hide()
        self.get_view().enter_test_mode()
    def exit_test_mode(self):
        solfege.app.m_test_mode = False
        self.m_action_groups['NotExit'].set_sensitive(True)
        box = Gtk.VBox()
        self.get_view().g_notebook.insert_page(box, Gtk.Label(label=_("Practise")), 0)
        self.g.reparent(box)
        self.get_view().g_notebook.show()
        self.get_view().g_notebook.get_nth_page(0).show()
        self.get_view().g_notebook.set_current_page(0)
        self.get_view().exit_test_mode()
    def new_training_set_editor(self, widget):
        dlg = TrainingSetDialog()
        dlg.show_all()
    def new_practisesheet_editor(self, widget):
        dlg = PractiseSheetDialog()
        dlg.show_all()


