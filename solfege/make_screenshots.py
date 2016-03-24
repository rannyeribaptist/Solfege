
import os
import time

from gi.repository import Gtk

import solfege
from solfege.profilemanager import ChangeProfileDialog
from solfege.practisesheetdlg import PractiseSheetDialog
from solfege.trainingsetdlg import TrainingSetDialog

def run(cmd):
    print cmd
    os.system(cmd)

def compress(fn):
    f, ext = os.path.splitext(fn)
    run("pngnq -n 16 -f %s" % fn)
    run("mv %s-nq8.png %s" % (f, fn))


def screenshot(windowtitle, lang, fn):
    while Gtk.events_pending():
        Gtk.main_iteration()
    time.sleep(2)
    while Gtk.events_pending():
        Gtk.main_iteration()
    fn = "help/%s/figures/%s" % (lang, fn)
    cmd = u'import -window %s %s' % (windowtitle, fn)
    print cmd
    os.system(cmd.encode("utf-8"))
    compress(fn)


def do_profile_manager(lang):
    p = ChangeProfileDialog(solfege.app.m_options.profile)
    p.show()
    pid = hex(p.vbox.get_parent_window().xid)
    screenshot(pid, lang, "profile-manager.png")
    p.destroy()


def do_practise_sheet(lang):
    dlg = PractiseSheetDialog()
    dlg.show_all()
    pid = hex(dlg.vbox.get_parent_window().xid)
    dlg.on_select_exercise(None, u'solfege:lesson-files/melodic-intervals-down-3')
    screenshot(pid, lang, "ear-training-test-printout-editor.png")
    dlg.do_closing_stuff()
    dlg.destroy()

def do_training_set(lang):
    dlg = TrainingSetDialog()
    dlg.show_all()
    dlg.on_select_exercise(None, u'solfege:lesson-files/chord-m7-7')
    dlg.on_select_exercise(None, u'solfege:lesson-files/melodic-intervals-up')
    pid = hex(dlg.get_children()[0].get_parent_window().xid)
    screenshot(pid, lang, "trainingset-editor.png")
    dlg.do_closing_stuff()
    dlg.destroy()


def do_preferences_window(lang):
    solfege.win.open_preferences_window(None)
    xid = hex(solfege.win.g_config_window.get_children()[0].get_parent_window().xid)
    solfege.win.g_config_window.set_resizable(False)
    solfege.win.g_config_window.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
    solfege.win.g_config_window.g_pview.expand_all()
    screenshot(xid, lang, "preferences-midi.png")
    solfege.win.g_config_window.g_pview.set_cursor((1,))
    screenshot(xid, lang, "preferences-user.png")
    solfege.win.g_config_window.g_pview.set_cursor((2,))
    screenshot(xid, lang, "preferences-external-programs.png")
    solfege.win.g_config_window.g_pview.set_cursor((3,))
    screenshot(xid, lang, "preferences-gui.png")
    solfege.win.g_config_window.g_pview.set_cursor((3, 0))
    screenshot(xid, lang, "preferences-gui-idtone.png")
    solfege.win.g_config_window.g_pview.set_cursor((3, 1))
    screenshot(xid, lang, "preferences-gui-interval.png")
    solfege.win.g_config_window.g_pview.set_cursor((4,))
    screenshot(xid, lang, "preferences-practise.png")
    solfege.win.g_config_window.g_pview.set_cursor((5,))
    screenshot(xid, lang, "preferences-sound-setup.png")
    solfege.win.g_config_window.g_pview.set_cursor((6,))
    screenshot(xid, lang, "preferences-statistics.png")
    solfege.win.g_config_window.hide()

def do_exercises(lang, xid):
    solfege.app.practise_lessonfile(u"solfege:lesson-files/harmonic-intervals-3")
    solfege.win.get_view().use_inputwidget(0)
    screenshot(xid, lang, "id-interval-buttons-thirds.png")
    solfege.win.get_view().use_inputwidget(1)
    screenshot(xid, lang, "id-interval-piano.png")
    solfege.win.get_view().g_notebook.set_current_page(2)
    screenshot(xid, lang, "statistics.png")
    solfege.app.practise_lessonfile(u"solfege:lesson-files/melodic-intervals-3")
    solfege.win.get_view().use_inputwidget(0)
    screenshot(xid, lang, "melodicinterval-buttons.png")
    solfege.app.practise_lessonfile(u"solfege:lesson-files/sing-intervals-4-5")
    solfege.win.get_view().new_question()
    screenshot(xid, lang, "singinterval.png")
    solfege.app.practise_lessonfile(u"solfege:lesson-files/chord-min-major")
    screenshot(xid, lang, "idbyname-chords.png")
    solfege.app.practise_lessonfile(u"solfege:lesson-files/chord-min-major-close-open")
    screenshot(xid, lang, "chord.png")
    solfege.app.practise_lessonfile(u"solfege:lesson-files/singchord-1")
    solfege.win.get_view().new_question()
    screenshot(xid, lang, "singchord.png")
    solfege.app.practise_lessonfile(u"solfege:lesson-files/rhythm-easy")
    solfege.win.get_view().new_question()
    screenshot(xid, lang, "rhythm.png")
    solfege.app.practise_lessonfile(u"solfege:regression-lesson-files/rhythmtapping2-1")
    screenshot(xid, lang, "rhythmtapping2.png")
    solfege.app.practise_lessonfile(u"solfege:lesson-files/jsb-inventions")
    screenshot(xid, lang, "dictation.png")
    solfege.app.practise_lessonfile(u"solfege:lesson-files/csound-fifth-0.99")
    screenshot(xid, lang, "idbyname-intonation.png")
    solfege.app.practise_lessonfile(u"solfege:lesson-files/id-tone-cde-3")
    screenshot(xid, lang, "idtone.png")
    solfege.app.practise_lessonfile(u"solfege:lesson-files/bpm")
    screenshot(xid, lang, "identifybpm.png")
    solfege.app.practise_lessonfile(u"solfege:lesson-files/twelvetone")
    solfege.win.get_view().new_question()
    screenshot(xid, lang, "twelvetone.png")
    solfege.app.practise_lessonfile(u"solfege:lesson-files/nameinterval-2")
    solfege.win.get_view().new_question()
    screenshot(xid, lang, "nameinterval.png")
    solfege.app.practise_lessonfile(u"solfege:lesson-files/progression-2")
    screenshot(xid, lang, "elembuilder-harmonic-progressions.png")
    solfege.app.practise_lessonfile(u"solfege:lesson-files/toneincontext-major-f4")
    screenshot(xid, lang, "toneincontext.png")


def make_screenshots():
    if not (os.path.exists("configure.ac")
            and os.path.exists("help/C/solfege.xml.in")
            and os.path.exists("solfege.py")):
        print "I don't think you are in the source directory of"
        print "GNU Solfege, so I refuse to continue."
        solfege.win.quit_program()
        return
    lang = os.environ['LANGUAGE'].split(":")[0]
    if not os.path.exists(os.path.join("help", lang)):
        lang = lang.split("_")[0]
    if not os.path.exists(os.path.join("help", lang)):
        print "Unknown language"
        solfege.win.quit_program()
        return
    xid = hex(solfege.win.get_view().get_parent_window().xid)
    if not os.path.exists("help/%s/figures" % lang):
        os.makedirs("help/%s/figures" % lang)
    do_profile_manager(lang)
    do_practise_sheet(lang)
    do_training_set(lang)
    do_preferences_window(lang)
    do_exercises(lang, xid)
    solfege.win.quit_program()

