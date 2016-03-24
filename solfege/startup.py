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

import locale
import logging.handlers
import os
import sqlite3
import sys
import time

locale.setlocale(locale.LC_NUMERIC, "C")


import solfege
solfege.app_running = True
from solfege import application
from solfege import buildinfo
from solfege import cfg
from solfege import filesystem
from solfege import gu
from solfege import lessonfile
from solfege import optionparser
from solfege import osutils
from solfege.profilemanager import ProfileManager
from solfege import make_screenshots
from solfege import statistics
from solfege import tracebackwindow

from solfege.mainwin import MainWin, SplashWin

# check_rcfile has to be called before and
# functions that use the cfg module.
application.check_rcfile()

opt_parser = optionparser.SolfegeOptionParser()
options, args = opt_parser.parse_args()

from solfege import runtime
runtime.init(options)
from gi.repository import Gtk
from gi.repository import GObject
from gi.repository import Gdk


if options.debug or options.debug_level:
    # We import all exercise modules here even though it is not necessary
    # since the modules are loaded one by one when needed. But by importing
    # all here, we catch SyntaxErrors at once.
    from solfege.exercises import *

    handler = logging.StreamHandler()
    logging.getLogger().addHandler(handler)
    if options.debug_level:
        options.debug = True
    level = {'debug': logging.DEBUG,
             'info': logging.INFO,
             'warning': logging.WARNING,
             'error': logging.ERROR,
             'critical': logging.CRITICAL}.get(options.debug_level, logging.DEBUG)
    logging.getLogger().setLevel(level)
else:
    handler = logging.handlers.MemoryHandler(1)
    logging.getLogger().addHandler(handler)


if options.version:
    if buildinfo.is_release():
        rev_info = ""
    else:
        rev_info = buildinfo.version_info
    print (u"""GNU Solfege %s
Revision_id: %s
This is free software. It is covered by the GNU General Public License,
and you are welcome to change it and/or distribute copies of it under
certain conditions. Invoke as `solfege --warranty` for more information.

%s
        """ % (buildinfo.VERSION_STRING,
        rev_info,
        solfege.application.solfege_copyright)).encode(sys.getfilesystemencoding(), 'replace')
    sys.exit()

if options.warranty:
    print "GNU Solfege %s" % buildinfo.VERSION_STRING
    print solfege.application.solfege_copyright.encode(sys.getfilesystemencoding(), 'replace')
    print solfege.application.warranty
    sys.exit()

# redirect error messages to a window that will popup if
# something bad happens.

sys.stderr = tracebackwindow.TracebackWindow(options.show_gtk_warnings)

def do_profiles():
    return (os.path.isdir(os.path.join(filesystem.app_data(), 'profiles'))
           and os.listdir(os.path.join(filesystem.app_data(), 'profiles')))


def start_gui(datadir):
    if not options.profile:
        if cfg.get_bool("app/noprofilemanager"):
            options.profile = cfg.get_string("app/last_profile")
        elif do_profiles():
            if solfege.splash_win:
                solfege.splash_win.hide()
            p = ProfileManager(cfg.get_string("app/last_profile"))
            ret = p.run()
            if ret == Gtk.ResponseType.ACCEPT:
                options.profile = p.get_profile()
                cfg.set_string("app/last_profile", "" if not options.profile else options.profile)
            elif ret in (Gtk.ResponseType.CLOSE, Gtk.ResponseType.DELETE_EVENT):
                Gtk.main_quit()
                return
            p.destroy()
            if solfege.splash_win:
                solfege.splash_win.show()

    cfg.set_bool('config/no_random', bool(options.no_random))

    lessonfile.infocache = lessonfile.InfoCache()

    def f(s):
        if solfege.splash_win:
            solfege.splash_win.show_progress(s)
    if solfege.splash_win:
        solfege.splash_win.show_progress(_("Opening statistics database"))
    try:
        solfege.db = statistics.DB(f, profile=options.profile)
    except sqlite3.OperationalError, e:
        solfege.splash_win.hide()
        gu.dialog_ok(_(u"Failed to open the statistics database:\n«%s»") % str(e).decode(sys.getfilesystemencoding(), 'replace'), secondary_text=_("Click OK to exit the program. Then try to quit all other instances of the program, or reboot the computer. You can only run one instance of GNU Solfege at once."))
        sys.exit()

    if solfege.splash_win:
        solfege.splash_win.show_progress(_("Creating application window"))

    solfege.app = application.SolfegeApp(options)
    solfege.win = w = MainWin(options, datadir)
    solfege.app.setup_sound()
    w.post_constructor()
    solfege.win.load_frontpage()
    w.show()
    if solfege.splash_win:
        solfege.splash_win.destroy()
        solfege.splash_win = None

    def ef(t, value, traceback):
        if options.debug:
            msg = "ehooked:" + str(value)
        else:
            msg = str(value)
        if issubclass(t, lessonfile.LessonfileException):
            w.display_error_message(msg, str(t))
        elif issubclass(t, osutils.ExecutableDoesNotExist):
            if len(value.args) > 1:
                w.display_error_message2(value.args[0], "\n".join(value.args[1:]))
            else:
                w.display_error_message(msg, str(t))
        else:
            sys.__excepthook__(t, msg, traceback)
    if not options.disable_exception_handler:
        sys.excepthook = ef
    print time.time() - start_time
    # We parse all lesson files when we are idle to save a half a
    # second the first time the user searches all lesson files using
    # Ctrl-F.
    lessonfile.infocache.parse_all_files(True)
    if options.screenshots:
        make_screenshots.make_screenshots()

def start_app(datadir):
    global splash_win
    if not options.no_splash:
        solfege.splash_win = splash_win = SplashWin()
        time.sleep(0.1)
        Gdk.flush()
        while Gtk.events_pending():
            Gtk.main_iteration()
    else:
        solfege.splash_win = splash_win = None
    style_provider = Gtk.CssProvider()
    with open("solfege.css", "r") as f:
        css = f.read()
    try:
        style_provider.load_from_data(css)
    except GObject.GError, e:
        print e
        pass
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), style_provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    GObject.timeout_add(1, start_gui, datadir)
    Gtk.main()

