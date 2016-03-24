# vim: set fileencoding=utf-8 :
# GNU Solfege - free ear training software
# Copyright (C) 2009, 2011  Tom Cato Amundsen
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
import StringIO
import subprocess

from gi.repository import Gtk

from solfege.esel import SearchView

if __name__ == '__main__':
    from solfege import i18n
    i18n.setup(".", "C")
    import solfege.statistics
    solfege.db = solfege.statistics.DB()

import solfege
from solfege import cfg
from solfege import filesystem
from solfege import gu
from solfege import frontpage as pd
from solfege import lessonfile
from solfege import osutils

class LessonFilePreviewWidget(Gtk.VBox):
    def __init__(self, model):
        Gtk.VBox.__init__(self)
        self.m_model = model
        self.set_size_request(200, 200)
        l = Gtk.Label()
        l.set_alignment(0.0, 0.5)
        l.set_markup("<b>Title:</b>")
        self.pack_start(l, False, False, 0)
        self.g_title = Gtk.Label()
        self.g_title.set_alignment(0.0, 0.5)
        self.pack_start(self.g_title, False, False, 0)
        l = Gtk.Label()
        l.set_alignment(0.0, 0.5)
        l.set_markup("<b>Module:</b>")
        self.pack_start(l, False, False, 0)
        self.g_module = Gtk.Label()
        self.g_module.set_alignment(0.0, 0.5)
        self.pack_start(self.g_module, False, False, 0)
        l = Gtk.Label()
        l.set_alignment(0.0, 0.5)
        l.set_markup("<b>Used in topcis:</b>")
        self.pack_start(l, False, False, 0)
        self.g_topic_box = Gtk.VBox()
        self.pack_start(self.g_topic_box, False, False, 0)
        self.show_all()
    def update(self, dlg):
        fn = dlg.get_preview_filename()
        if fn:
            fn = gu.decode_filename(fn)
            for child in self.g_topic_box.get_children():
                child.destroy()
            fn = lessonfile.mk_uri(fn)
            try:
                self.set_sensitive(True)
                self.g_title.set_text(lessonfile.infocache.get(fn, 'title'))
                self.g_module.set_text(lessonfile.infocache.get(fn, 'module'))
                self.g_ok_button.set_sensitive(True)
                for x in self.m_model.iterate_topics_for_file(fn):
                    l = Gtk.Label(label=x)
                    l.set_alignment(0.0, 0.5)
                    self.g_topic_box.pack_start(l, False, False, 0)
                if not self.g_topic_box.get_children():
                    l = Gtk.Label(label=u"-")
                    l.set_alignment(0.0, 0.5)
                    self.g_topic_box.pack_start(l, False, False, 0)
            except (lessonfile.InfoCache.FileNotFound,
                    lessonfile.InfoCache.FileNotLessonfile), e:
                self.g_title.set_text(u'')
                self.g_module.set_text(u'')
                self.g_ok_button.set_sensitive(False)
                self.set_sensitive(False)
        self.show_all()
        return True

class SelectLessonFileDialog(Gtk.FileChooserDialog):
    def __init__(self, parent):
        Gtk.FileChooserDialog.__init__(self, _("Select lesson file"),
            parent=parent,
            buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,))
        self.set_select_multiple(True)
        pv = LessonFilePreviewWidget(parent.m_model)
        pv.g_ok_button = self.add_button("gtk-ok", Gtk.ResponseType.OK)
        pv.g_ok_button.set_sensitive(False)
        pv.show()
        self.set_preview_widget(pv)
        self.connect('selection-changed', pv.update)


class SelectLessonfileBySearchDialog(Gtk.Dialog):
    def __init__(self):
        Gtk.Dialog.__init__(self, buttons=(Gtk.STOCK_CLOSE, Gtk.ResponseType.ACCEPT))
        view = SearchView(_('Search for exercises. Each exercise you click will be added to the section of the front page.'),
            fields=['link-with-filename-tooltip', 'module'])
        view.on_link_clicked = self.on_link_clicked
        self.vbox.pack_start(view, True, True, 0)
        self.show_all()
    def on_link_clicked(self, widget, filename):
        self.m_filename = filename
        self.response(Gtk.ResponseType.OK)


def editor_of(obj):
    """
    Return the toplevel page, the one that is a Editor object.
    """
    p = obj
    while not isinstance(p, Editor):
        p = p.m_parent
    return p

def parent_page(obj):
    """
    Return the parent page of obj. Return None if this is the toplevel page.
    """
    p = obj
    while True:
        try:
            p = p.m_parent
        except AttributeError:
            return None
        if isinstance(p, Page):
            return p
        if p is None:
            return None

class Section(Gtk.VBox):
    """
    A section consists of a heading and a list of links.
    self.g_link_box is a vbox that contains the links.
    """
    def __init__(self, model, parent):
        Gtk.VBox.__init__(self)
        self.m_model = model
        self.m_parent = parent
        assert isinstance(model, pd.LinkList)
        hbox = Gtk.HBox()
        hbox.set_spacing(6)
        self.pack_start(hbox, False, False, 0)
        # This is displayed and used when we edit the heading
        self.g_heading_entry = Gtk.Entry()
        self.g_heading_entry.set_no_show_all(True)
        hbox.pack_start(self.g_heading_entry, True, True, 0)
        self.g_heading = Gtk.Label()
        self.g_heading.set_alignment(0.0, 0.5)
        # FIXME escape m_name
        self.g_heading.set_markup("<b>%s</b>" % model.m_name)
        hbox.pack_start(self.g_heading, False, False, 0)
        #
        button_hbox = Gtk.HBox()
        button_hbox.set_spacing(0)
        hbox.pack_start(button_hbox, False, False, 0)
        im = Gtk.Image()
        im.set_from_stock(Gtk.STOCK_EDIT, Gtk.IconSize.MENU)
        button = Gtk.Button()
        button.add(im)
        button.connect('clicked', self.on_edit_heading)
        button_hbox.pack_start(button, False, False, 0)
        #
        im = Gtk.Image()
        im.set_from_stock(Gtk.STOCK_ADD, Gtk.IconSize.MENU)
        button = Gtk.Button()
        button.add(im)
        button.connect('button-release-event', self.on_add)
        button_hbox.pack_start(button, False, False, 0)
        #
        im = Gtk.Image()
        im.set_from_stock(Gtk.STOCK_REMOVE, Gtk.IconSize.MENU)
        button = Gtk.Button()
        button.add(im)
        button.connect('button-release-event', self.on_remove)
        button_hbox.pack_start(button, False, False, 0)
        #
        im = Gtk.Image()
        im.set_from_stock(Gtk.STOCK_CUT, Gtk.IconSize.MENU)
        b = Gtk.Button()
        b.add(im)
        b.connect('clicked', self.on_cut)
        button_hbox.pack_start(b, False, False, 0)
        #
        im = Gtk.Image()
        im.set_from_stock(Gtk.STOCK_PASTE, Gtk.IconSize.MENU)
        b = Gtk.Button()
        b.add(im)
        b.connect('clicked', self.on_paste, -1)
        Editor.clipboard.register_paste_button(b, (pd.LinkList, pd.Page, unicode))
        button_hbox.pack_start(b, False, False, 0)
        #
        im = Gtk.Image()
        im.set_from_stock(Gtk.STOCK_GO_DOWN, Gtk.IconSize.MENU)
        self.g_move_down_btn = Gtk.Button()
        self.g_move_down_btn.add(im)
        self.g_move_down_btn.connect('clicked',
            self.m_parent.move_section_down, self)
        button_hbox.pack_start(self.g_move_down_btn, False, False, 0)
        #
        im = Gtk.Image()
        im.set_from_stock(Gtk.STOCK_GO_UP, Gtk.IconSize.MENU)
        self.g_move_up_btn = Gtk.Button()
        self.g_move_up_btn.add(im)
        self.g_move_up_btn.connect('clicked',
            self.m_parent.move_section_up, self)
        button_hbox.pack_start(self.g_move_up_btn, False, False, 0)
        #
        im = Gtk.Image()
        im.set_from_stock(Gtk.STOCK_GO_BACK, Gtk.IconSize.MENU)
        self.g_move_left_btn = Gtk.Button()
        self.g_move_left_btn.add(im)
        self.g_move_left_btn.connect('clicked',
            parent.m_parent.on_move_section_left, self)
        button_hbox.pack_start(self.g_move_left_btn, False, False, 0)
        #
        im = Gtk.Image()
        im.set_from_stock(Gtk.STOCK_GO_FORWARD, Gtk.IconSize.MENU)
        self.g_move_right_btn = Gtk.Button()
        self.g_move_right_btn.add(im)
        self.g_move_right_btn.connect('clicked',
            parent.m_parent.on_move_section_right, self)
        button_hbox.pack_start(self.g_move_right_btn, False, False, 0)
        #
        self.g_link_box = Gtk.VBox()
        self.pack_start(self.g_link_box, False, False, 0)
        for link in self.m_model:
            self.g_link_box.pack_start(self.create_linkrow(link), True, True, 0)
        # The button to click to add a new link
        hbox = Gtk.HBox()
        self.pack_start(hbox, True, True, 0)
    def on_edit_heading(self, btn):
        self.g_heading_entry.set_text(self.m_model.m_name)
        self.g_heading_entry.show()
        self.g_heading.hide()
        self.g_heading_entry.grab_focus()
        def finish_edit(entry):
            self.g_heading_entry.disconnect(sid)
            self.g_heading_entry.disconnect(keyup_id)
            self.g_heading_entry.disconnect(keydown_sid)
            self.m_model.m_name = entry.get_text()
            self.g_heading.set_markup(u"<b>%s</b>" % entry.get_text())
            self.g_heading_entry.hide()
            self.g_heading.show()
        sid = self.g_heading_entry.connect('activate', finish_edit)
        def keydown(entry, event):
            if event.keyval == Gdk.KEY_Tab:
                finish_edit(entry)
        keydown_sid = self.g_heading_entry.connect('key-press-event', keydown)
        def keyup(entry, event):
            if event.keyval == Gdk.KEY_Escape:
                self.g_heading_entry.disconnect(sid)
                self.g_heading_entry.disconnect(keyup_id)
                self.g_heading_entry.hide()
                self.g_heading.show()
                return True
        keyup_id = self.g_heading_entry.connect('key-release-event', keyup)
    def on_add(self, btn, event):
        menu = Gtk.Menu()
        item = Gtk.MenuItem(_("Add link to new page"))
        item.connect('activate', self.on_add_link_to_new_page)
        menu.append(item)
        item = Gtk.MenuItem(_("Add link to exercise"))
        item.connect('activate', self.on_add_link)
        menu.append(item)
        item = Gtk.MenuItem(_("Add link by searching for exercises"))
        item.connect('activate', self.on_add_link_by_search)
        menu.append(item)
        menu.show_all()
        menu.popup(None, None, None, None, event.button, event.time)
    def on_remove(self, btn, event):
        self.m_parent.remove_section(self)
    def on_add_link_by_search(self, btn):
        dlg = SelectLessonfileBySearchDialog()
        while True:
            ret = dlg.run()
            if ret == Gtk.ResponseType.OK:
                self._add_filenames([os.path.abspath(lessonfile.uri_expand(dlg.m_filename))])
            else:
                break
        dlg.destroy()
    def on_add_link(self, btn):
        if editor_of(self).m_filename:
            open_dir = os.path.split(editor_of(self).m_filename)[0]
        else:
            open_dir = filesystem.user_data()
        dlg = SelectLessonFileDialog(editor_of(self))
        dlg.set_current_folder(open_dir)
        while 1:
            ret = dlg.run()
            if ret in (Gtk.ResponseType.REJECT, Gtk.ResponseType.DELETE_EVENT, Gtk.ResponseType.CANCEL):
                break
            else:
                assert ret == Gtk.ResponseType.OK
                self._add_filenames(dlg.get_filenames())
                break
        dlg.destroy()
    def _add_filenames(self, filenames):
        for filename in filenames:
            fn = gu.decode_filename(filename)
            assert os.path.isabs(fn)
            # If the file name is a file in a subdirectory below
            # lessonfile.exercises_dir in the current working directory,
            # then the file is a standard lesson file, and it will be
            # converted to a uri scheme with:
            fn = lessonfile.mk_uri(fn)
            # Small test to check that the file actually is a lesson file.
            try:
                lessonfile.infocache.get(fn, 'title')
            except lessonfile.infocache.FileNotLessonfile:
                continue
            self.m_model.append(fn)
            self.g_link_box.pack_start(self.create_linkrow(fn, True, True, 0), False)
    def on_add_link_to_new_page(self, menuitem):
        page = pd.Page(_("Untitled%s") % "", [pd.Column()])
        self.m_model.append(page)
        self.g_link_box.pack_start(self.create_linkrow(page, True, True, 0))
    def create_linkrow(self, link_this):
        hbox = Gtk.HBox()
        def ff(btn, page):
            if id(page) in editor_of(self).m_page_mapping:
                editor_of(self).show_page_id(id(page))
            else:
                if not page[0]:
                    page[0].append(pd.LinkList(link_this.m_name))
                p = Page(page, parent_page(self))
                p.show()
                editor_of(self).add_page(p)
        if isinstance(link_this, pd.Page):
            linkbutton = gu.ClickableLabel(link_this.m_name)
            linkbutton.connect('clicked', ff, link_this)
        else:
            try:
                linkbutton = gu.ClickableLabel(lessonfile.infocache.get(link_this, 'title'))
                linkbutton.set_tooltip_text(link_this)
            except lessonfile.InfoCache.FileNotFound:
                linkbutton = gu.ClickableLabel(_(u"«%s» was not found") % link_this)
                linkbutton.make_warning()

        hbox.pack_start(linkbutton, True, True, 0)
        linkbutton.connect('button-press-event', self.on_right_click_row, link_this)
        hbox.show_all()
        return hbox
    def on_right_click_row(self, button, event, linked):
        idx = self.m_model.index(linked)
        if event.button == 3:
            m = Gtk.Menu()
            item = Gtk.ImageMenuItem(Gtk.STOCK_DELETE)
            item.connect('activate', self.on_delete_link, linked)
            m.append(item)
            item = Gtk.ImageMenuItem(Gtk.STOCK_CUT)
            item.connect('activate', self.on_cut_link, idx)
            m.append(item)
            item = Gtk.ImageMenuItem(Gtk.STOCK_PASTE)
            item.set_sensitive(bool(Editor.clipboard))
            item.connect('activate', self.on_paste, idx)
            m.append(item)
            item = Gtk.ImageMenuItem(Gtk.STOCK_EDIT)
            item.connect('activate', self.on_edit_linktext, linked)
            item.set_sensitive(bool(not isinstance(linked, basestring)))
            m.append(item)
            item = Gtk.ImageMenuItem(Gtk.STOCK_GO_UP)
            item.connect('activate', self.on_move_link_up, idx)
            item.set_sensitive(bool(idx > 0))
            m.append(item)
            item = Gtk.ImageMenuItem(Gtk.STOCK_GO_DOWN)
            item.connect('activate', self.on_move_link_down, idx)
            item.set_sensitive(bool(idx < len(self.m_model) - 1))
            m.append(item)
            item = Gtk.ImageMenuItem(Gtk.STOCK_EDIT)
            item.set_sensitive(isinstance(linked, unicode))
            item.connect('activate', self.on_edit_file, idx)
            m.append(item)
            m.show_all()
            m.popup(None, None, None, None, event.button, event.time)
            return True
    def on_delete_link(self, menuitem, linked):
        idx = self.m_model.index(linked)
        if id(linked) in editor_of(self).m_page_mapping:
            editor_of(self).destroy_window(id(linked))
        self.g_link_box.get_children()[idx].destroy()
        del self.m_model[idx]
    def on_edit_linktext(self, menuitem, linked):
        idx = self.m_model.index(linked)
        # row is the hbox containing the linkbutton
        row = self.g_link_box.get_children()[idx]
        linkbutton = row.get_children()[0]
        entry = Gtk.Entry()
        entry.set_text(linkbutton.get_label())
        row.pack_start(entry, True, True, 0)
        linkbutton.hide()
        entry.show()
        entry.grab_focus()
        def finish_edit(entry):
            linkbutton.set_label(entry.get_text().decode("utf-8"))
            linkbutton.get_children()[0].set_alignment(0.0, 0.5)
            linkbutton.show()
            self.m_model[idx].m_name = entry.get_text().decode("utf-8")
            entry.destroy()
        sid = entry.connect('activate', finish_edit)
        def keydown(entry, event):
            if event.keyval == Gdk.KEY_Tab:
                finish_edit(entry)
        entry.connect('key-press-event', keydown)
        def keyup(entry, event):
            if event.keyval == Gdk.KEY_Escape:
                linkbutton.show()
                entry.disconnect(sid)
                entry.destroy()
                return True
        entry.connect('key-release-event', keyup)
    def on_edit_file(self, menuitem, linked):
        try:
            try:
                subprocess.call((cfg.get_string("programs/text-editor"),
                             lessonfile.uri_expand(self.m_model[linked])))
            except OSError, e:
                 raise osutils.BinaryForProgramException("Text editor", cfg.get_string("programs/text-editor"), e)
        except osutils.BinaryForProgramException, e:
            solfege.win.display_error_message2(e.msg1, e.msg2)
    def on_cut(self, btn):
        self.m_parent.cut_section(self)
    def on_cut_link(self, menuitem, idx):
        Editor.clipboard.append(self.m_model[idx])
        del self.m_model[idx]
        self.g_link_box.get_children()[idx].destroy()
    def on_paste(self, btn, idx):
        assert Editor.clipboard, "Paste buttons should be insensitive when the clipboard is empty."
        pobj = Editor.clipboard.pop()
        if isinstance(pobj, pd.LinkList):
            mobj = pd.Page(pobj.m_name, [pd.Column(pobj)])
        else:
            mobj = pobj
        if idx == -1:
            self.m_model.append(mobj)
            self.g_link_box.pack_start(self.create_linkrow(mobj, True, True, 0))
        else:
            self.m_model.insert(idx, mobj)
            row = self.create_linkrow(mobj)
            self.g_link_box.pack_start(row, True, True, 0)
            self.g_link_box.reorder_child(row, idx)
    def on_move_link_up(self, btn, idx):
        """
        Move the link one row up.
        """
        assert idx > 0
        self.m_model[idx], self.m_model[idx - 1] = self.m_model[idx - 1], self.m_model[idx]
        self.g_link_box.reorder_child(self.g_link_box.get_children()[idx], idx - 1)
    def on_move_link_down(self, btn, idx=None):
        """
        Move the link one row down.
        """
        self.m_model[idx], self.m_model[idx + 1] = self.m_model[idx + 1], self.m_model[idx]
        self.g_link_box.reorder_child(self.g_link_box.get_children()[idx], idx + 1)


class Column(Gtk.VBox):
    def __init__(self, model, parent):
        Gtk.VBox.__init__(self)
        self.set_spacing(gu.hig.SPACE_MEDIUM)
        self.m_model = model
        self.m_parent = parent
        assert isinstance(model, pd.Column)
        self.g_section_box = Gtk.VBox()
        self.g_section_box.set_spacing(gu.hig.SPACE_MEDIUM)
        self.pack_start(self.g_section_box, False, False, 0)
        for section in model:
            assert isinstance(section, pd.LinkList)
            gui_section = Section(section, self)
            self.g_section_box.pack_start(gui_section, False, False, 0)
        hbox = Gtk.HBox()
        self.pack_start(hbox, False, False, 0)
        b = Gtk.Button(_("Add section"))
        hbox.pack_start(b, False, False, 0)
        b.connect('clicked', self.on_add_section)
        b = Gtk.Button(stock=Gtk.STOCK_PASTE)
        b.connect('clicked', self.on_paste)
        Editor.clipboard.register_paste_button(b, pd.LinkList)
        hbox.pack_start(b, False, False, 0)
    def __del__(self):
        logging.debug("Column.__del__")
    def cut_section(self, section):
        idx = self.g_section_box.get_children().index(section)
        Editor.clipboard.append(self.m_model[idx])
        del self.m_model[idx]
        self.g_section_box.get_children()[idx].destroy()
    def remove_section(self, section):
        idx = self.g_section_box.get_children().index(section)
        del self.m_model[idx]
        self.g_section_box.get_children()[idx].destroy()
    def on_add_section(self, btn):
        # We write "Untitled%s" % "" instead of just "Untitled" here
        # since "Untitled%s" is already translated in many languages.
        section = pd.LinkList(_("Untitled%s" % ""))
        self.m_model.append(section)
        gui_section = Section(section, self)
        self.g_section_box.pack_start(gui_section, False, False, 0)
        gui_section.show_all()
    def move_section_down(self, widget, section):
        idx = self.g_section_box.get_children().index(section)
        if idx < len(self.g_section_box.get_children()) - 1:
            self.g_section_box.reorder_child(section, idx + 1)
            self.m_model[idx], self.m_model[idx + 1] \
                    = self.m_model[idx + 1], self.m_model[idx]
            self.m_parent.update_buttons()
    def move_section_up(self, widget, section):
        idx = self.g_section_box.get_children().index(section)
        if idx > 0:
            self.g_section_box.reorder_child(section, idx - 1)
            self.m_model[idx], self.m_model[idx - 1] \
                    = self.m_model[idx - 1], self.m_model[idx]
            self.m_parent.update_buttons()
    def on_paste(self, widget):
        """
        Paste the clipboard as a new section to this column.
        """
        assert Editor.clipboard, "Paste buttons should be insensitive when the clipboard is empty."
        assert isinstance(Editor.clipboard[-1], pd.LinkList)
        pobj = Editor.clipboard.pop()
        self.m_model.append(pobj)
        sect = Section(pobj, self)
        sect.show_all()
        self.g_section_box.pack_start(sect, False, False, 0)


class Page(Gtk.VBox):
    def __init__(self, model, parent):
        Gtk.VBox.__init__(self)
        self.m_model = model
        self.m_parent = parent
        sc = Gtk.ScrolledWindow()
        sc.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.pack_start(sc, True, True, 0)
        self.g_column_box = Gtk.HBox()
        self.g_column_box.set_spacing(gu.hig.SPACE_LARGE)
        self.g_column_box.set_border_width(gu.hig.SPACE_SMALL)
        # We pack column into this box
        sc.add_with_viewport(self.g_column_box)
        self.show_all()
        if model:
            self.update_from_model()
    def __del__(self):
        logging.debug("Page.__del__:", self.m_model.m_name)
    def on_add_column(self, *btn):
        column = pd.Column()
        self.m_model.append(column)
        gcol = Column(column, self)
        gcol.show_all()
        self.g_column_box.pack_start(gcol, True, True, 0)
    def on_move_section_left(self, button, section):
        column_idx = self.g_column_box.get_children().index(section.m_parent)
        section_idx = section.m_parent.g_section_box.get_children().index(section)
        if column_idx > 0:
            to_column = self.g_column_box.get_children()[column_idx - 1]
            section.reparent(to_column.g_section_box)
            section.m_parent = to_column
            to_column.g_section_box.set_child_packing(section, False, False, 0, Gtk.PACK_START)
            self.m_model[column_idx - 1].append(self.m_model[column_idx][section_idx])
            del self.m_model[column_idx][section_idx]
            # Remove the right-most column if we moved the
            # last section out of it.
            if not self.g_column_box.get_children()[-1].g_section_box.get_children():
                assert len(self.m_model[-1]) == 0
                del self.m_model[-1]
                self.g_column_box.get_children()[-1].destroy()
            self.update_buttons()
    def on_move_section_right(self, button, section):
        # the column we move from
        column_idx = self.g_column_box.get_children().index(section.m_parent)
        section_idx = section.m_parent.g_section_box.get_children().index(section)
        if column_idx == len(self.g_column_box.get_children()) - 1:
            self.on_add_column()
        to_column = self.g_column_box.get_children()[column_idx + 1]
        section.reparent(to_column.g_section_box)
        section.m_parent = to_column
        to_column.g_section_box.set_child_packing(section, False, False, 0, Gtk.PACK_START)
        to_section_idx = len(self.m_model[column_idx + 1])
        self.m_model[column_idx + 1].append(self.m_model[column_idx][section_idx])
        del self.m_model[column_idx][section_idx]
        self.update_buttons()
    def update_from_model(self):
        for child in self.g_column_box.get_children():
            child.destroy()
        for column in self.m_model:
            self.g_column_box.pack_start(Column(column, self), False, False, 0)
        self.g_column_box.show_all()
        self.update_buttons()
    def update_buttons(self):
        num_cols = len(self.g_column_box.get_children())
        for col_idx, column in enumerate(self.g_column_box.get_children()):
            num_sects = len(column.g_section_box.get_children())
            for sect_idx, section in enumerate(column.g_section_box.get_children()):
                section.g_move_up_btn.set_sensitive(sect_idx != 0)
                section.g_move_down_btn.set_sensitive(sect_idx != num_sects -1)
                section.g_move_left_btn.set_sensitive(col_idx != 0)
                if [col for col in self.g_column_box.get_children() if not col.g_section_box.get_children()] and col_idx == num_cols - 1:
                    section.g_move_right_btn.set_sensitive(False)
                else:
                    section.g_move_right_btn.set_sensitive(True)


class Clipboard(list):
    def __init__(self, v=[]):
        list.__init__(v)
        self.m_paste_buttons = []
    def pop(self, i=-1):
        ret = list.pop(self, i)
        self.update_buttons()
        return ret
    def append(self, obj):
        list.append(self, obj)
        self.update_buttons()
    def register_paste_button(self, button, accepts_types):
        button.set_sensitive(bool(self) and isinstance(self[-1], accepts_types))
        self.m_paste_buttons.append((button, accepts_types))
    def update_buttons(self):
        for button, types in self.m_paste_buttons:
            button.set_sensitive(bool(self) and isinstance(self[-1], types))


class Editor(Gtk.Window, gu.EditorDialogBase):
    savedir = os.path.join(filesystem.user_data(), u'exercises', u'user')
    # The clipboard will be shared between all Editor instances
    clipboard = Clipboard()
    def __init__(self, filename=None):
        Gtk.Window.__init__(self)
        logging.debug("fpeditor.Editor.__init__(%s)", filename)
        gu.EditorDialogBase.__init__(self, filename)
        self.set_default_size(800, 600)
        self.g_main_box = Gtk.VBox()
        self.add(self.g_main_box)
        self.g_actiongroup.add_actions([
            ('GoBack', Gtk.STOCK_GO_BACK, None, None, None, self.go_back),
        ])
        self.setup_toolbar()
        self.g_title_hbox = Gtk.HBox()
        self.g_title_hbox.set_spacing(gu.hig.SPACE_SMALL)
        self.g_title_hbox.set_border_width(gu.hig.SPACE_SMALL)
        label = Gtk.Label()
        label.set_markup(u"<b>%s</b>" % _("Front page title:"))
        self.g_title_hbox.pack_start(label, False, False, 0)
        self.g_fptitle = Gtk.Entry()
        self.g_title_hbox.pack_start(self.g_fptitle, True, True, 0)
        self.g_main_box.pack_start(self.g_title_hbox, False, False, 0)
        # This dict maps the windows created for all pages belonging to
        # the file.
        self.m_page_mapping = {}
        self.m_model = None
        if filename:
            self.load_file(filename)
        else:
            self.m_model = pd.Page(_("Untitled%s") % self.m_instance_number,
                    pd.Column())
            self.set_not_modified()
        self.add_page(Page(self.m_model, self))
        self.clipboard.update_buttons()
        self.show_all()
        self.add_to_instance_dict()
        self.g_fptitle.set_text(self.m_model.m_name)
        self.g_fptitle.connect('changed', self.on_frontpage_title_changed)
    def __del__(self):
        logging.debug("fpeditor.Editor.__del__, filename=%s", self.m_filename)
    def add_page(self, page):
        """
        Add and show the page.
        """
        editor_of(self).m_page_mapping[id(page.m_model)] = page
        self.g_main_box.pack_start(page, True, True, 0)
        self.show_page(page)
    def show_page_id(self, page_id):
        self.show_page(self.m_page_mapping[page_id])
    def show_page(self, page):
        """
        Hide the currently visible page, and show PAGE instead.
        """
        try:
            self.g_visible_page.hide()
        except AttributeError:
            pass
        self.g_visible_page = page
        page.show()
        if isinstance(page.m_parent, Page):
            self.g_title_hbox.hide()
        else:
            self.g_title_hbox.show()
        self.g_ui_manager.get_widget("/Toolbar/GoBack").set_sensitive(
            not isinstance(self.g_visible_page.m_parent, Editor))
    def go_back(self, *action):
        self.show_page(self.g_visible_page.m_parent)
    def on_frontpage_title_changed(self, widget):
        self.m_model.m_name = widget.get_text()
    def setup_toolbar(self):
        self.g_ui_manager.insert_action_group(self.g_actiongroup, 0)
        uixml = """
        <ui>
         <toolbar name='Toolbar'>
          <toolitem action='GoBack'/>
          <toolitem action='New'/>
          <toolitem action='Open'/>
          <toolitem action='Save'/>
          <toolitem action='SaveAs'/>
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
        toolbar = self.g_ui_manager.get_widget("/Toolbar")
        self.g_main_box.pack_start(toolbar, False, False, 0)
        self.g_main_box.reorder_child(toolbar, 0)
        self.g_ui_manager.get_widget("/Toolbar").set_style(Gtk.ToolbarStyle.BOTH)
    def destroy_window(self, window_id):
        """
        Destroy the window with the id 'windowid' and all subwindows.
        """
        def do_del(wid):
            for key in self.m_page_mapping:
                parent = parent_page(self.m_page_mapping[key])
                if id(parent) == wid:
                    do_del(key)
            editor_of(self).m_page_mapping[wid].destroy()
            del editor_of(self).m_page_mapping[wid]
        do_del(window_id)
    @staticmethod
    def edit_file(fn):
        if fn in Editor.instance_dict:
            Editor.instance_dict[fn].present()
        else:
            try:
                win = Editor(fn)
                win.show()
            except IOError, e:
                gu.dialog_ok(_("Loading file '%(filename)s' failed: %(msg)s") %
                        {'filename': fn, 'msg': str(e).decode('utf8', 'replace')})
    def load_file(self, filename):
        """
        Load a file into a empty, newly created Editor object.
        """
        assert self.m_model == None
        self.m_model = pd.load_tree(filename, C_locale=True)
        self.m_filename = filename
        #
        if not os.path.isabs(filename):
            if not os.access(filename, os.W_OK):
                m = Gtk.MessageDialog(self, Gtk.DialogFlags.MODAL, Gtk.MessageType.INFO,
                    Gtk.ButtonsType.CLOSE, _("The front page file is write protected in your install. This is normal. If you want to edit a front page file, you have to select one of the files stored in .solfege/exercises/*/ in your home directory."))
                m.run()
                m.destroy()
        self.set_not_modified()
        self.set_title(self.m_filename)
    def set_not_modified(self):
        """
        Store the current state of the data in self.m_orig_dump so that
        is_modified() will return False until we make new changes.
        """
        io = StringIO.StringIO()
        self.m_model.dump(io)
        self.m_orig_dump = io.getvalue()
    def is_modified(self):
        """
        Return True if the data has changed since the last call to
        set_not_modified()
        """
        io = StringIO.StringIO()
        self.m_model.dump(io)
        s = io.getvalue()
        return s != self.m_orig_dump
    @property
    def m_changed(self):
        return self.is_modified()
    def save(self, w=None):
        assert self.m_filename
        save_location = os.path.split(self.m_filename)[0] + os.sep
        fh = pd.FileHeader(1, self.m_model)
        fh.save_file(self.m_filename)
        self.set_not_modified()
        # We do test for solfege.win since it is not available during testing
        if hasattr(solfege, 'win'):
            solfege.win.load_frontpage()
    def on_show_help(self, *w):
        return
    def get_save_as_dialog(self):
        dialog = gu.EditorDialogBase.get_save_as_dialog(self)
        ev2 = Gtk.EventBox()
        ev2.set_name("DIALOGWARNING2")
        ev = Gtk.EventBox()
        ev.set_border_width(gu.hig.SPACE_SMALL)
        ev2.add(ev)
        ev.set_name("DIALOGWARNING")
        label = Gtk.Label()
        label.set_padding(gu.hig.SPACE_MEDIUM, gu.hig.SPACE_MEDIUM)
        ev.add(label)
        label.set_markup(_("<b>IMPORTANT:</b> Your front page file <b>must</b> be saved in a subdirectory below the directory named exercises. See the user manual for details."))
        dialog.set_extra_widget(ev2)
        ev2.show_all()
        return dialog

if __name__ == '__main__':
    Gtk.link_button_set_uri_hook(lambda a, b: None)
    e = Editor()
    e.load_file("learningtrees/learningtree.txt")
    Gtk.main()
