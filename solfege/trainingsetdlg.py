# vim: set fileencoding=utf-8 :
# GNU Solfege - free ear training software
# Copyright (C) 2007, 2008, 2011 Tom Cato Amundsen
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

import os
import time

from gi.repository import GObject
from gi.repository import Gtk

from solfege import buildinfo
from solfege import filesystem
from solfege import gu
from solfege import lessonfile
from solfege import lessonfilegui
from solfege import lfmod
from solfege import osutils
from solfege.dataparser import Dataparser

import solfege

# The definition of a training set will be stored in a file in the
# ~/.solfege/trainingsets

class TrainingSetDialog(Gtk.Window, gu.EditorDialogBase, lessonfilegui.ExercisesMenuAddIn):
    fileformat_version = 2
    STORE_FILENAME = 0
    STORE_TITLE = 1
    STORE_COUNT = 2
    STORE_REPEAT = 3
    STORE_DELAY = 4
    savedir = os.path.join(filesystem.user_data(), "trainingsets")
    def __init__(self, filename=None):
        Gtk.Window.__init__(self)
        gu.EditorDialogBase.__init__(self, filename)
        self.set_default_size(800, 300)
        # This VBox will have 2 parts.
        # 1: the tool bar
        # 2: another container widget that has the content of a file
        self.g_vbox = Gtk.VBox()
        self.add(self.g_vbox)
        self.setup_toolbar()
        #
        self.g_settings_box = Gtk.VBox()
        self.g_settings_box.set_border_width(6)
        self.g_vbox.pack_start(self.g_settings_box, False, False, 0)
        self.g_output = {}
        self.g_output['midi'] = Gtk.RadioButton.new_with_mnemonic(None, _("MIDI"))
        self.g_output['wav'] = Gtk.RadioButton.new_with_mnemonic_from_widget(self.g_output['midi'], _("WAV"))
        self.g_output['mp3'] = Gtk.RadioButton.new_with_mnemonic_from_widget(self.g_output['midi'], _("MP3"))
        self.g_output['ogg'] = Gtk.RadioButton.new_with_mnemonic_from_widget(self.g_output['midi'], _("OGG"))
        hbox = Gtk.HBox()
        hbox.set_spacing(6)
        self.g_settings_box.pack_start(hbox, True, True, 0)
        hbox.pack_start(Gtk.Label(_("Preferred output format:")),
                                  False, False, 0)
        for s in ('midi', 'wav', 'mp3', 'ogg'):
            hbox.pack_start(self.g_output[s], False, False, 0)
        ####
        hbox.pack_start(Gtk.VSeparator(), False, False, 0)
        self.g_named_tracks = Gtk.CheckButton(_("Name files by questions"))
        hbox.pack_start(self.g_named_tracks, False, False, 0)
        self.g_liststore = Gtk.ListStore(
            GObject.TYPE_STRING, # filename
            GObject.TYPE_STRING, # visible exercise name
            GObject.TYPE_INT, # count
            GObject.TYPE_INT, # repeat
            GObject.TYPE_INT) # delay
        self.g_treeview = Gtk.TreeView(self.g_liststore)
        self.g_treeview.set_size_request(400, 100)
        self.g_treeview.connect('cursor-changed',
            self.on_treeview_cursor_changed)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("Title"), renderer, text=self.STORE_TITLE, markup=1)
        def mark_invalid(column, cell_renderer, tree_model, iter, user_data=None):
            fn = tree_model.get_value(iter, self.STORE_FILENAME)
            if not fn:
                cell_renderer.props.markup = '<span background="red">%s</span>' % tree_model.get_value(iter, self.STORE_TITLE)
        column.set_cell_data_func(renderer, mark_invalid)
        self.g_treeview.append_column(column)
        renderer = Gtk.CellRendererText()
        renderer.set_property('editable', True)
        renderer.connect('edited', self.on_count_edited)
        column = Gtk.TreeViewColumn(_("Count"), renderer,
                                    text=self.STORE_COUNT)
        self.g_treeview.append_column(column)
        renderer = Gtk.CellRendererText()
        renderer.set_property('editable', True)
        renderer.connect('edited', self.on_repeat_edited)
        column = Gtk.TreeViewColumn(_("_Repeat").replace("_", ""), renderer,
                                    text=self.STORE_REPEAT)
        self.g_treeview.append_column(column)
        renderer = Gtk.CellRendererText()
        renderer.set_property('editable', True)
        renderer.connect('edited', self.on_delay_edited)
        column = Gtk.TreeViewColumn(_("Delay"), renderer, text=self.STORE_DELAY)
        self.g_treeview.append_column(column)
        self.g_vbox.pack_start(self.g_treeview, True, True, 0)
        if filename:
            self.load_file(filename)
        else:
            self.init_empty_file()
        self.show_all()
        self.add_to_instance_dict()
    def on_treeview_cursor_changed(self, treeview):
        self.g_ui_manager.get_widget("/ExportToolbar/Remove").set_sensitive(True)
    def on_count_edited(self, renderer, path, text):
        self._edit_col(2, path, text)
    def on_repeat_edited(self, renderer, path, text):
        self._edit_col(3, path, text)
    def on_delay_edited(self, renderer, path, text):
        self._edit_col(4, path, text)
    def _edit_col(self, col_num, path, text):
        """
        This method does the real work when on_XXXX_edited is called.
        """
        try:
            i = int(text)
        except ValueError:
            i = None
        if i is not None:
            iter = self.g_liststore.get_iter_from_string(path)
            self.g_liststore.set_value(iter, col_num, i)
    def on_remove_lesson_clicked(self, *w):
       path, column = self.g_treeview.get_cursor()
       assert path
       iter = self.g_liststore.get_iter(path)
       if iter:
           if self.g_liststore.remove(iter):
               self.g_treeview.set_cursor(self.g_liststore.get_path(iter))
           elif path[0] > 0:
               self.g_treeview.set_cursor((path[0]-1,))
           else:
               self.g_ui_manager.get_widget("/ExportToolbar/Remove").set_sensitive(False)
    def on_add_lesson_clicked(self, button):
        try:
            self.menu
        except AttributeError:
            self.menu = self.create_learning_tree_menu()
        self.menu.popup(None, None, None, None, 1, 0)
    def on_select_exercise(self, item, filename):
        """
        This method is called when the user has selected an exercise to
        add.
        """
        module = lessonfile.infocache.get(filename, 'module')
        if module not in ('harmonicinterval', 'melodicinterval', 'idbyname'):
            print "Only harmonicinterval, melodicinterval and idbyname module exercises are working now. Ignoring..."
            return
        if module == 'idbyname':
            p = lessonfile.LessonfileCommon()
            p.parse_file(filename)
            if not [q for q in p.m_questions if isinstance(q.music, lessonfile.MpdParsable)]:
                gu.dialog_ok(_("This lesson file cannot be exported because some of the music in the file are not parsable by the mpd module."))
                return
        self.m_changed = True
        self.g_liststore.append((
            filename, self.get_lessonfile_title(filename), 3, 3, 4))
    def get_lessonfile_title(self, filename):
        """
        Return a string we use the name the lesson file in the GUI.
        """
        return "%s (%s)" % (_(lessonfile.infocache.get(filename, 'title')), filename)
    def init_empty_file(self):
        self.m_changed = False
        self.set_title(self._get_a_filename())
        self.g_ui_manager.get_widget("/ExportToolbar/Remove").set_sensitive(False)
    def setup_toolbar(self):
        self.g_actiongroup.add_actions([
         ('Export', Gtk.STOCK_EXECUTE, _("Export"), None, None, self.on_export),
         ('Add', Gtk.STOCK_ADD, None, None, None, self.on_add_lesson_clicked),
         ('Remove', Gtk.STOCK_REMOVE, None, None, None, self.on_remove_lesson_clicked),
        ])
        self.g_ui_manager.insert_action_group(self.g_actiongroup, 0)
        uixml = """
        <ui>
         <toolbar name='ExportToolbar'>
          <toolitem action='Add'/>
          <toolitem action='Remove'/>
          <toolitem action='New'/>
          <toolitem action='Open'/>
          <toolitem action='Save'/>
          <toolitem action='SaveAs'/>
          <toolitem action='Export'/>
          <toolitem action='Close'/>
          <toolitem action='Help'/>
         </toolbar>
         <accelerator action='Close'/>
         <accelerator action='New'/>
         <accelerator action='Open'/>
         <accelerator action='Save'/>
        </ui>
        """
        self.g_ui_manager.add_ui_from_string(uixml)
        self.g_vbox.pack_start(self.g_ui_manager.get_widget("/ExportToolbar"),
                               False, False, 0)
        self.g_ui_manager.get_widget("/ExportToolbar").set_style(Gtk.ToolbarStyle.BOTH)
    def on_show_help(self, widget):
        solfege.app.handle_href("trainingset-editor.html")
    def load_file(self, filename):
        p = Dataparser()
        p.parse_file(filename)
        mod = lfmod.parse_tree_interpreter(p.tree, {'yes': True, 'no': False})
        s = mod.m_globals.setdefault('output_format', 'midi')
        s = s.lower()
        if s in self.g_output:
            self.g_output[s].set_active(True)
        else:
            # MIDI is the default format
            self.g_output['midi'].set_active(True)
        self.m_filename = filename
        if mod.m_globals['fileformat_version'] == 1:
            e = Exception("TrainingSetDlg")
            e.msg1 = _("Cannot read old file format")
            e.msg2 = _("To convert the file to the new file format, you must open and save it in an older version of Solfege. Versions from 3.16.0 to 3.20.4 should do the job.")
            raise e
        self.g_named_tracks.set_active(mod.m_globals.get('named_tracks', False))
        for lesson in mod.m_blocklists.setdefault('lesson', []):
            # In this loop we will set the filename column of the liststore
            # to None if there is any problem, and set a title mentioning
            # the unknown filename.
            filename = lesson['filename']
            if filename:
                if os.path.exists(lessonfile.uri_expand(filename)):
                    fn = filename
                    title = self.get_lessonfile_title(filename)
                else:
                    fn = None
                    title = _(u"«<b>%s</b>» was not found") % filename
                self.g_liststore.append((fn,
                    title,
                    lesson['count'],
                    lesson['repeat'],
                    lesson['delay']))
            else:
                self.g_liststore.append((filename,
                    _(u"«%s» not found") % filename,
                    lesson['count'],
                    lesson['repeat'],
                    lesson['delay']))
        self.m_changed = False
        self.set_title(self.m_filename)
    def save(self):
        """
        Save the file to a file named by self.m_filename
        """
        assert self.m_filename
        f = open(self.m_filename, 'w')
        print >> f, "# Training set definition file for GNU Solfege %s" % buildinfo.VERSION_STRING
        print >> f, "\nfileformat_version = %i" % self.fileformat_version
        print >> f, "output_format = \"%s\"" % [k for k in self.g_output if self.g_output[k].get_active()][0]
        print >> f, "named_tracks = %s" % (u"yes" if self.g_named_tracks.get_active() else u"no")
        iter = self.g_liststore.get_iter_first()
        while iter:
            print >> f, "lesson {"
            filename = self.g_liststore.get_value(iter, self.STORE_FILENAME)
            print >> f, '  filename = "%s"' % filename
            print >> f, '  count = %i' \
                % self.g_liststore.get_value(iter, self.STORE_COUNT)
            print >> f, '  repeat = %i' \
                % self.g_liststore.get_value(iter, self.STORE_REPEAT)
            print >> f, '  delay = %i' \
                % self.g_liststore.get_value(iter, self.STORE_DELAY)
            print >> f, "}\n"
            iter = self.g_liststore.iter_next(iter)
        f.close()
        self.m_changed = False
    def on_export(self, widget):
        iter = self.g_liststore.get_iter_first()
        all_files_ok = True
        while iter:
            if self.g_liststore.get(iter, self.STORE_FILENAME) == (None,):
                all_files_ok = False
            iter = self.g_liststore.iter_next(iter)
        if not all_files_ok:
            gu.dialog_ok("Can not run because some exercises are not found.")
            return
        export_to = \
            self.select_empty_directory(_("Select where to export the files"))
        if not export_to:
            return
        progress_dialog = Gtk.Dialog(_("Exporting training set"), self,
            0, (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL))
        progress_dialog.show()
        label = Gtk.Label()
        label.set_markup('<span weight="bold">%s</span>' % gu.escape(_("Export training set")))
        label.show()
        progress_dialog.vbox.pack_start(label, False, False, 0)
        def _cancel(widget, response):
            solfege.app.m_abort_export = True
        progress_dialog.connect('response', _cancel)
        progress_bar = Gtk.ProgressBar()
        progress_bar.show()
        progress_dialog.vbox.pack_start(progress_bar, True, True, 0)
        # We have to make a version of the data without gtk widgets
        v = []
        iter = self.g_liststore.get_iter_first()
        while iter:
            v.append({
                'filename': \
                        unicode(self.g_liststore.get_value(iter, self.STORE_FILENAME)),
                'count': self.g_liststore.get_value(iter, self.STORE_COUNT),
                'repeat': self.g_liststore.get_value(iter, self.STORE_REPEAT),
                'delay': self.g_liststore.get_value(iter, self.STORE_DELAY),
                        })
            iter = self.g_liststore.iter_next(iter)
        output_format = [k for k in self.g_output if self.g_output[k].get_active()][0]
        progress_dialog.queue_draw()
        while Gtk.events_pending():
            Gtk.main_iteration()
        time.sleep(0.1)
        while Gtk.events_pending():
            Gtk.main_iteration()
        try:
            for prog in solfege.app.export_training_set(v, export_to, output_format, self.g_named_tracks.get_active()):
                progress_bar.set_fraction(prog)
                while Gtk.events_pending():
                    Gtk.main_iteration()
            progress_dialog.destroy()
        except osutils.BinaryBaseException, e:
            progress_dialog.destroy()
            solfege.win.display_error_message2(e.msg1, e.msg2)


