# -*- coding: iso-8859-1 -*-
# GNU Solfege - free ear training software
# Copyright (C) 2004, 2005, 2006, 2007, 2008, 2011  Tom Cato Amundsen
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

import os
import sys

import gi
pyGtk.require("2.0")
from gi.repository import Gtk

from solfege import mpd
from solfege import gu
from solfege import lessonfile
from solfege import dataparser
from solfege import stock

Gtk.stock_add([('solfege-notehead', _("Add noteheads"), 0, 0, ''),
               ('solfege-sharp', _("Add sharps"), 0, 0, ''),
               ('solfege-double-sharp', _("Add double-sharps"), 0, 0, ''),
               ('solfege-natural', _("Remove accidentals"), 0, 0, ''),
               ('solfege-flat', _("Add flats"), 0, 0, ''),
               ('solfege-double-flat', _("Add double-flats"), 0, 0, ''),
               ('solfege-erase', _("Delete tones"), 0, 0, ''),
               ])
app_version = "0.1.4"

class HelpWindow(Gtk.Window):
    def __init__(self, parent):
        Gtk.Window.__init__(self)
        self.set_title(_("GNU Solfege lesson file editor") )
        self.set_default_size(400, 400)
        self.g_parent = parent
        self.vbox = Gtk.VBox()
        self.vbox.set_spacing(8)
        self.add(self.vbox)
        self.connect('delete_event', self.delete_cb)
        self.g_htmlwidget = htmlwidget.HtmlWidget(None, None)
        self.vbox.pack_start(self.g_htmlwidget, True, True, 0)
        self.vbox.pack_start(Gtk.HSeparator(), False)
        bbox = Gtk.HButtonBox()
        bbox.set_border_width(8)
        self.vbox.pack_start(bbox, False)
        b = Gtk.Button(stock=Gtk.STOCK_CLOSE)
        b.connect('clicked', self.close_cb)
        bbox.pack_start(b, True, True, 0)
        self.show_all()
        self.set_focus(b)
    def source(self, html):
        self.g_htmlwidget.source(html)
    def delete_cb(self, *v):
        self.g_parent.g_help_window = None
    def close_cb(self, w):
        self.g_parent.g_help_window = None
        self.destroy()


window_actions = [
    ('FileMenu', None, _('_File')),
    ('NewLessonfile', Gtk.STOCK_NEW, None, None, 'new file', 'file_new_cb'),
    ('Open', Gtk.STOCK_OPEN, None, None, 'Open lesson file', 'file_open_cb'),
    ('Save', Gtk.STOCK_SAVE, None, None, 'Save the lesson file', 'file_save_cb'),
    ('SaveAs', Gtk.STOCK_SAVE_AS, None, '<shift><ctrl>s', 'Save the lesson file with a new name', 'file_save_as_cb'),
    ('Quit', Gtk.STOCK_QUIT, None, None, 'Quit program', 'quit_cb'),
    ('HelpMenu', None, _('_Help')),
    ('HelpHelp', Gtk.STOCK_HELP, None, None, None, 'help_cb'),
    ('HelpAbout', None, _('_About'), '', '', 'about_cb'),
]
lessonfile_actions = [
    ('GotoFirstQuestion', Gtk.STOCK_GOTO_FIRST, None, None,
     _('Go to the first question'), 'goto_first_question_cb'),
    ('GoBackQuestion', Gtk.STOCK_GO_BACK, None, None,
     _('Go to the previous question'), 'go_back_question_cb'),
    ('GoForwardQuestion', Gtk.STOCK_GO_FORWARD, None, None,
     _('Go to the next question'), 'go_forward_question_cb'),
    ('GotoLastQuestion', Gtk.STOCK_GOTO_LAST, None, None,
     _('Go to the last question'), 'goto_last_question_cb'),
    ('NewQuestion', Gtk.STOCK_ADD, None, None,
     _('Add a new question'), 'new_question_cb'),
    ('NoteheadCursor', 'solfege-notehead', None, None,
     _('Add noteheads'), 'select_cursor_notehead_cb'),
    ('SharpCursor', 'solfege-sharp', None, None,
     _('Add sharps'), 'select_cursor_sharp_cb'),
    ('DoubleSharpCursor', 'solfege-double-sharp', None, None,
     _('Add double-sharps'), 'select_cursor_2sharp_cb'),
    ('NaturalCursor', 'solfege-natural', None, None,
     _('Remove accidentals'), 'select_cursor_natural_cb'),
    ('FlatCursor', 'solfege-flat', None, None,
     _('Add flats'), 'select_cursor_flat_cb'),
    ('DoubleFlatCursor', 'solfege-double-flat', None, None,
     _('Add double-flats'), 'select_cursor_2flat_cb'),
    ('EraseCursor', 'solfege-erase', None, None,
     _('Delete tones'), 'select_cursor_erase_cb'),
]
ui_string = """<ui>
  <menubar name='Menubar'>
    <menu action='FileMenu'>
      <menuitem action='NewLessonfile'/>
      <menuitem action='Open'/>
      <menuitem action='Save'/>
      <menuitem action='SaveAs'/>
      <separator/>
      <menuitem action='Quit'/>
    </menu>
    <menu action='HelpMenu'>
      <menuitem action='HelpHelp'/>
      <menuitem action='HelpAbout'/>
    </menu>
  </menubar>
  <toolbar name='Toolbar'>
    <toolitem action='GotoFirstQuestion'/>
    <toolitem action='GoBackQuestion'/>
    <toolitem action='GoForwardQuestion'/>
    <toolitem action='GotoLastQuestion'/>
    <toolitem action='NewQuestion'/>
    <separator/>
    <toolitem action='NoteheadCursor'/>
    <toolitem action='DoubleSharpCursor'/>
    <toolitem action='SharpCursor'/>
    <toolitem action='NaturalCursor'/>
    <toolitem action='FlatCursor'/>
    <toolitem action='DoubleFlatCursor'/>
    <toolitem action='EraseCursor'/>
  </toolbar>
</ui>"""

def fix_actions(actions, instance):
    "Helper function to map methods to an instance"
    retval = []
    for i in range(len(actions)):
        curr = actions[i]
        if len(curr) > 5:
            curr = list(curr)
            curr[5] = getattr(instance, curr[5])
            curr = tuple(curr)
        retval.append(curr)
    return retval

class EditorLessonfile(object):
    def __init__(self):
        self.m_filename = None
        self.m_changed = False
        self.header = lessonfile._Header({'module': 'chord'})
        self.m_questions = [dataparser.Question()]
        self.m_questions[-1].music = lessonfile.Music("", "chord")
        self.m_questions[-1].name = ""
        self._idx = 0


class MainWin(Gtk.Window):
    def __init__(self, datadir):
        Gtk.Window.__init__(self)
        self.icons = stock.EditorIconFactory(self, datadir)
        self.connect('destroy', lambda w: Gtk.main_quit())
        self.g_help_window = None
        # toplevel_vbox:
        #   -menubar
        #   -toolbar
        #   -notebook
        #   -statusbar
        self.toplevel_vbox = Gtk.VBox()
        self.add(self.toplevel_vbox)
        self.create_menu_and_toolbar()
        self.g_notebook = Gtk.Notebook()
        self.toplevel_vbox.pack_start(self.g_notebook, True, True, 0)
        self.vbox = Gtk.VBox()
        self.toplevel_vbox.pack_start(self.vbox, True, True, 0)
        self.create_mainwin_ui()
        self.show_all()
    def create_mainwin_ui(self):
        qbox = gu.hig_dlg_vbox()
        self.g_notebook.append_page(qbox, Gtk.Label(label=_("Questions")))
        gu.bLabel(qbox, _("Enter new chords using the mouse"), False, False)
        hbox = gu.bHBox(qbox, False, False)
        self.g_displayer = mpd.musicdisplayer.ChordEditor()
        self.g_displayer.connect('clicked', self.on_displayer_clicked)
        self.g_displayer.clear(2)
        gu.bLabel(hbox, "")
        hbox.pack_start(self.g_displayer, False)
        gu.bLabel(hbox, "")
        ##
        self.g_question_name = Gtk.Entry()
        qbox.pack_start(gu.hig_label_widget(_("Question title:", True, True, 0), self.g_question_name, None), False)
        self.g_navinfo = Gtk.Label(label="")
        qbox.pack_start(self.g_navinfo, False)

        ##
        self.m_P = EditorLessonfile()
        cvbox = Gtk.VBox()
        self.g_notebook.append_page(cvbox, Gtk.Label(label=_("Lessonfile header")))
        ## Header section
        sizegroup = Gtk.SizeGroup(Gtk.SizeGroupMode.HORIZONTAL)
        self.g_title = Gtk.Entry()
        cvbox.pack_start(gu.hig_label_widget(_("File title:", True, True, 0), self.g_title,
                        sizegroup))
        self.g_content_chord = Gtk.RadioButton(None, "chord")
        self.g_content_chord_voicing = Gtk.RadioButton(self.g_content_chord, "chord-voicing")
        self.g_content_idbyname = Gtk.RadioButton(self.g_content_chord, "id-by-name")
        box = Gtk.HBox()
        box.pack_start(self.g_content_chord, True, True, 0)
        box.pack_start(self.g_content_chord_voicing, True, True, 0)
        box.pack_start(self.g_content_idbyname, True, True, 0)
        cvbox.pack_start(gu.hig_label_widget(_("Content:", True, True, 0), box, sizegroup))
        self.g_random_transpose = Gtk.Entry()
        cvbox.pack_start(gu.hig_label_widget(_("Random transpose:", True, True, 0),
            self.g_random_transpose, sizegroup))
        #
        #self.g_statusbar = Gtk.Statusbar()
        #self.toplevel_vbox.pack_start(self.g_statusbar, False)
        self.update_appwin()
    def proceed_if_changed(self):
        if not self.m_P.m_changed:
            return True
        dialog = Gtk.MessageDialog(self, Gtk.DialogFlags.MODAL, Gtk.MessageType.QUESTION,
              Gtk.ButtonsType.YES_NO, _("You have unsaved data. Proceed anyway?"))
        dialog.hide()
        if dialog.run() == Gtk.ResponseType.YES:
            dialog.destroy()
            return True
        dialog.destroy()
        return False
    def update_appwin(self):
        self.update_score()
        self.set_navinfo()
        self.g_title.set_text(self.m_P.header.title)
        self.g_random_transpose.set_text(str(self.m_P.header.random_transpose))
        {'chord': self.g_content_chord,
         'chordvoicing': self.g_content_chord_voicing,
         'idbyname': self.g_content_idbyname}[self.m_P.header.module].set_active(True)
    def set_navinfo(self):
        if self.m_P.m_filename:
            self.set_title(self.m_P.m_filename)
        else:
            self.set_title(_("No file"))
        self.g_navinfo.set_text(_("question %(idx)i of %(count)i") % {
            'idx': self.m_P._idx + 1,
            'count': len(self.m_P.m_questions)})
        self.g_question_name.set_text(self.m_P.m_questions[self.m_P._idx].name)
    def load_file(self, filename):
        self.m_P = lessonfile.ChordLessonfile(filename)
        self.m_P.m_changed = False
        if self.m_P.m_questions:
            self.m_P._idx = 0
            self.set_navinfo()
        else:
            # Do a little trick to make an empty question
            self.m_P.m_questions = [dataparser.Question()]
            self.m_P.m_questions[-1].music = lessonfile.Music("", "chord")
            self.m_P.m_questions[-1].name = ""
            self.m_P._idx = 0

        if self.m_P.header.module not in ('idbyname', 'chord', 'chordvoicing'):
                dialog = Gtk.MessageDialog(self, Gtk.DialogFlags.MODAL,
                    Gtk.MessageType.ERROR, Gtk.ButtonsType.CLOSE,
                    _("The exercise module '%s' is not supported yet. Cannot edit this file.") % c)
                dialog.run()
                dialog.destroy()
                self.m_P = EditorLessonfile()
        self.update_appwin()
    def file_open_cb(self, *v):
        dialog = Gtk.FileChooserDialog(_("Open..."), self,
                                   Gtk.FileChooserAction.OPEN,
                                   (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                    Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        dialog.set_default_response(Gtk.ResponseType.OK)
        if dialog.run() == Gtk.ResponseType.OK:
            filename = gu.decode_filename(dialog.get_filename())
            try:
                self.load_file(filename)
            except Exception, e:
                dialog.destroy()
                m = Gtk.MessageDialog(self, Gtk.DialogFlags.MODAL, Gtk.MessageType.ERROR,
                        Gtk.ButtonsType.CLOSE,
                        _("Loading file '%(filename)s' failed: %(msg)s") %
                            {'filename': filename, 'msg': e})
                m.run()
                m.destroy()
            else:
                dialog.destroy()
        else:
            dialog.destroy()
    def file_new_cb(self, action, v=None):
        if self.proceed_if_changed():
            self.m_P = EditorLessonfile()
            self.update_appwin()
    def file_save_as_cb(self, *v):
        self.store_data_from_ui()
        dialog = Gtk.FileChooserDialog(_("Save as..."), self,
                                  Gtk.FileChooserAction.SAVE,
                                   (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                    Gtk.STOCK_SAVE, Gtk.ResponseType.OK))
        dialog.set_default_response(Gtk.ResponseType.OK)

        if dialog.run() == Gtk.ResponseType.OK:
            self.m_P.m_filename = gu.decode_filename(dialog.get_filename())
            self.save_file()
        dialog.destroy()
    def file_save_cb(self, *v):
        self.store_data_from_ui()
        if self.m_P.m_filename is None:
            dialog = Gtk.FileChooserDialog(_("Save..."), self,
                                   Gtk.FileChooserAction.SAVE,
                                   (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                    Gtk.STOCK_SAVE, Gtk.ResponseType.OK))
            dialog.set_default_response(Gtk.ResponseType.OK)

            if dialog.run() == Gtk.ResponseType.OK:
                self.m_P.m_filename = gu.decode_filename(dialog.get_filename())
            dialog.destroy()
        if self.m_P.m_filename:
            self.update_appwin()
            self.save_file()
    def save_file(self):
        if not self.m_P.m_filename:
            raise Exception("No filename. Cannot save.")
        ofile = open(self.m_P.m_filename, 'w')
        ofile.write("# Creator: GNU Solfege lesson file editor %s\n\n"
                    % app_version)
        ofile.write("header {\n    module = %s\n" % self.m_P.header.module)
        if type(self.m_P.header.random_transpose) == list:
            ofile.write("    random_transpose = %s, %s, %s\n" % (self.m_P.header.random_transpose[0],
                            self.m_P.header.random_transpose[1], self.m_P.header.random_transpose[2]))
        else:
            ofile.write("    random_transpose = yes\n")
        if self.m_P.header.lesson_id:
            ofile.write('    lesson_id = "%s"\n' % self.m_P.header.lesson_id)
        ofile.write('    title = "%s"\n}\n' % self.m_P.header.title)
        for q in self.m_P.m_questions:
            print >> ofile, 'question {'
            print >> ofile, '    name = "%s"' % q.name
            print >> ofile, '    music = music("%s", chord)' % q.music.m_musicdata
            print >> ofile, '}'
        ofile.close()
        self.m_P.m_changed = False

    def quit_cb(self, *v):
        if self.proceed_if_changed():
            Gtk.main_quit()
    def help_cb(self, *v):
        if not self.g_help_window:
            self.g_help_window = HelpWindow(self)
            self.g_help_window.source("""<html>
<body>
<h2>GNU Solfege lesson file editor %s</h2>
<p>This is the very first unfinished release. Backup the files you
edit, since it can screw up.</p>
<p>The parser can create files for the chord exercise. It can parse more
advanced lesson files than it can write. So you might loose data if you
edit your hand written lesson files with this program.</p>
</body>
</html>
""" % app_version)
            self.g_help_window.show()
        else:
            self.g_help_window.present()
    def about_cb(self, *v):
        dialog = Gtk.MessageDialog(self, Gtk.DialogFlags.MODAL, Gtk.MessageType.INFO,
            Gtk.ButtonsType.CLOSE, "GNU Solfege lesson file editor %s\nCopyright (C) 2004, 2005 Tom Cato Amundsen <tca@gnu.org>" % app_version)
        dialog.run()
        dialog.destroy()
    def goto_first_question_cb(self, *v):
        self.store_data_from_ui()
        self.m_P._idx = 0
        self.update_appwin()
    def go_back_question_cb(self, *v):
        self.store_data_from_ui()
        self.m_P._idx = max(0, self.m_P._idx - 1)
        self.update_appwin()
    def go_forward_question_cb(self, *v):
        self.store_data_from_ui()
        self.m_P._idx = min(self.m_P._idx + 1, len(self.m_P.m_questions) - 1)
        self.update_appwin()
    def goto_last_question_cb(self, *v):
        self.store_data_from_ui()
        self.m_P._idx = len(self.m_P.m_questions) - 1
        self.update_appwin()
    def new_question_cb(self, *v):
        self.store_data_from_ui()
        self.m_P.m_questions.append(dataparser.Question())
        self.m_P.m_questions[-1].music = lessonfile.Music("", "chord")
        self.m_P.m_questions[-1].name = ""
        self.m_P._idx = len(self.m_P.m_questions) - 1
        self.update_appwin()
    def select_cursor_2flat_cb(self, *v):
        self.g_displayer.set_cursor("-2")
    def select_cursor_flat_cb(self, *v):
        self.g_displayer.set_cursor(-1)
    def select_cursor_natural_cb(self, *v):
        self.g_displayer.set_cursor(0)
    def select_cursor_sharp_cb(self, *v):
        self.g_displayer.set_cursor("1")
    def select_cursor_2sharp_cb(self, *v):
        self.g_displayer.set_cursor("2")
    def select_cursor_erase_cb(self, *v):
        self.g_displayer.set_cursor("erase")
    def select_cursor_notehead_cb(self, *v):
        self.g_displayer.set_cursor("notehead")
    def update_score(self):
        """
        Set m_chord_tones based on the data in the lesson file.
        Then call g_displayer.display to show the music.
        """
        assert self.m_P
        self.m_chord_tones = {}
        for n in self.m_P.m_questions[self.m_P._idx].music.m_musicdata.split():
            p = mpd.MusicalPitch.new_from_notename(n)
            self.m_chord_tones[p.steps()] = p
        #
        if self.m_chord_tones:
            s = ""
            for n in self.m_chord_tones.values():
                s += " " + n.get_octave_notename()
            self.g_displayer.display("\staff{ < %s >}\staff{\clef bass}" % s, "20-tight")
        else:
            self.g_displayer.display("\staff{ }\staff{\clef bass}", "20-tight")
        self.g_displayer.set_size_request(400, -1)
    def store_data_from_ui(self):
        self.m_P.m_questions[self.m_P._idx].name = self.g_question_name.get_text()
        self.m_P.header.title = self.g_title.get_text()
        self.m_P.header.random_transpose = eval(self.g_random_transpose.get_text())
        if self.g_content_chord.get_active():
            self.m_P.header.module = 'chord'
        if self.g_content_chord_voicing.get_active():
            self.m_P.header.module = 'chordvoicing'
        if self.g_content_idbyname.get_active():
            self.m_P.header.module = 'idbyname'
    def on_displayer_clicked(self, ed, steps):
        self.m_P.m_changed = True
        notename = ("c", "d", "e", "f", "g", "a", "b")[6-(steps % 7)]
        n = mpd.MusicalPitch.new_from_notename(notename)
        n.m_octave_i = 1-(steps // 7)
        if self.g_displayer.m_cursor == 'notehead':
            if n.steps() not in self.m_chord_tones:
                self.m_chord_tones[n.steps()] = n
        elif self.g_displayer.m_cursor == 'erase':
            if n.steps() in self.m_chord_tones:
                del self.m_chord_tones[n.steps()]
        else:
            if n.steps() not in self.m_chord_tones:
                return
            else:
                self.m_chord_tones[n.steps()].m_accidental_i = int(self.g_displayer.m_cursor)
        v = self.m_chord_tones.values()
        v.sort()
        v = [y.get_octave_notename() for y in v]
        self.m_P.m_questions[self.m_P._idx].music.m_musicdata = " ".join(v)
        self.update_score()

class UIManagerMainWin(MainWin):
    def __init__(self, datadir):
        MainWin.__init__(self, datadir)
    def create_menu_and_toolbar(self):
        self.window_ag = Gtk.ActionGroup('WindowActions')
        self.lessonfile_ag = Gtk.ActionGroup('LessonfileActions')

        self.window_ag.add_actions(fix_actions(window_actions, self))
        self.lessonfile_ag.add_actions(fix_actions(lessonfile_actions, self))
        self.ui = Gtk.UIManager()
        self.ui.insert_action_group(self.window_ag, 0)
        self.ui.insert_action_group(self.lessonfile_ag, 1)
        self.ui.add_ui_from_string(ui_string)
        self.add_accel_group(self.ui.get_accel_group())
        self.toplevel_vbox.pack_start(self.ui.get_widget('/Menubar', True, True, 0), False)
        self.ui.get_widget('/Toolbar').set_style(Gtk.TOOLBAR_ICONS)
        self.toplevel_vbox.pack_start(self.ui.get_widget('/Toolbar', True, True, 0), False)

def main(datadir):
    mpd.engravers.fetadir = os.path.join(datadir, "feta")
    w = UIManagerMainWin(datadir)
    if len(sys.argv) == 2:
        w.load_file(sys.argv[1])
    w.show()
    Gtk.main()
