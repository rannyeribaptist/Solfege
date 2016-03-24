# vim: set fileencoding=utf-8 :
# GNU Solfege - free ear training software
# Copyright (C) 2010, 2011 Tom Cato Amundsen
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
import shutil

from gi.repository import GObject
from gi.repository import Gtk

from solfege import filesystem
from solfege import gu

class NewProfileDialog(Gtk.Dialog):
    def __init__(self):
        Gtk.Dialog.__init__(self, _(u"_Create profile\u2026").replace(u"\u2026", "").replace("_", ""))
        self.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                         Gtk.STOCK_OK, Gtk.ResponseType.ACCEPT)
        vbox = gu.hig_dlg_vbox()
        self.vbox.pack_start(vbox, True, True, 0)
        #
        label = Gtk.Label(label=_("Enter the name of the new folder:"))
        label.set_alignment(0.0, 0.5)
        vbox.pack_start(label, False, False, 0)
        #
        self.g_entry = Gtk.Entry()
        self.g_entry.connect('changed', self.on_entry_changed)
        self.g_entry.set_activates_default(True)
        vbox.pack_start(self.g_entry, False, False, 0)
        #
        label = Gtk.Label(label=_("Your profile data will be stored in:"))
        label.set_alignment(0.0, 0.5)
        vbox.pack_start(label, False, False, 0)
        #
        self.g_profile_location = Gtk.Label()
        vbox.pack_start(self.g_profile_location, False, False, 0)
        #
        self.g_statusbox = Gtk.HBox()
        self.g_statusbox.set_no_show_all(True)
        vbox.pack_start(self.g_statusbox, False, False, 0)
        im = Gtk.Image()
        im.set_from_stock(Gtk.STOCK_DIALOG_WARNING, Gtk.IconSize.MENU)
        self.g_statusbox.pack_start(im, False, False, 0)
        im.show()

        self.g_status = Gtk.Label()
        self.g_status.show()
        self.g_statusbox.pack_start(self.g_status, False, False, 0)
        self.g_entry.set_text(_("New Profile"))
        self.set_default_response(Gtk.ResponseType.ACCEPT)
    def on_entry_changed(self, *w):
        pdir = os.path.join(filesystem.app_data(), u"profiles",
                            self.g_entry.get_text().decode("utf-8"))
        self.g_profile_location.set_text(pdir)
        if os.path.exists(pdir):
            self.g_status.set_text(_(u"The profile «%s» already exists.") % self.g_entry.get_text().decode("utf-8"))
            self.g_statusbox.show()
            self.set_response_sensitive(Gtk.ResponseType.ACCEPT, False)
        else:
            self.g_statusbox.hide()
            self.g_status.set_text(u"")
            self.set_response_sensitive(Gtk.ResponseType.ACCEPT, True)


class RenameProfileDialog(Gtk.Dialog):
    def __init__(self, oldname):
        Gtk.Dialog.__init__(self, _(u"_Rename profile\u2026").replace("_", "").replace(u"\u2026", ""))
        self.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                        Gtk.STOCK_OK, Gtk.ResponseType.ACCEPT)
        vbox = gu.hig_dlg_vbox()
        self.vbox.pack_start(vbox, True, True, 0)

        label = Gtk.Label(label=_(u"Rename the profile «%s» to:") % oldname)
        label.set_alignment(0.0, 0.5)
        vbox.pack_start(label, False, False, 0)

        self.g_entry = Gtk.Entry()
        self.g_entry.set_text(oldname)
        self.g_entry.set_activates_default(True)
        self.g_entry.connect('changed', self.on_entry_changed)
        vbox.pack_start(self.g_entry, False, False, 0)

        self.g_info = Gtk.Label()
        self.g_info.set_no_show_all(True)
        vbox.pack_start(self.g_info, False, False, 0)
        self.set_default_response(Gtk.ResponseType.ACCEPT)
    def on_entry_changed(self, w):
        s = self.g_entry.get_text().decode("utf-8")
        pdir = os.path.join(filesystem.app_data(), u"profiles", s)
        ok = False
        if not s:
            self.g_info.show()
            self.g_info.set_text("Empty string not allowed")
        elif os.path.exists(pdir):
            self.g_info.show()
            self.g_info.set_text(_(u"The profile «%s» already exists.") % self.g_entry.get_text().decode("utf-8"))
        else:
            self.g_info.hide()
            ok = True
        self.set_response_sensitive(Gtk.ResponseType.ACCEPT, ok)


class ProfileManagerBase(Gtk.Dialog):
    def __init__(self, default_profile):
        Gtk.Dialog.__init__(self, _("GNU Solfege - Choose User Profile"))
        # We save the initially selected profile, because we need to keep
        # track of it if the user renames it and then presses cancel.
        self.m_default_profile = default_profile
        vbox = gu.hig_dlg_vbox()
        self.vbox.pack_start(vbox, False, False, 0)
        l = Gtk.Label(_("Solfege will save your statistics and test results in the user profile. By adding additional user profiles to Solfege, multiple users can share a user account on the operating system."))
        l.set_alignment(0.0, 0.5)
        l.set_line_wrap(True)
        vbox.pack_start(l, True, True, 0)

        hbox = Gtk.HBox()
        hbox.set_spacing(gu.hig.SPACE_MEDIUM)
        vbox.pack_start(hbox, True, True, 0)
        button_box = Gtk.VBox()

        self.g_create_profile = Gtk.Button.new_with_mnemonic(_(u"_Create profile\u2026"))
        self.g_create_profile.connect('clicked', self.on_create_profile)
        button_box.pack_start(self.g_create_profile, False, False, 0)

        self.g_rename_profile = Gtk.Button.new_with_mnemonic(_(u"_Rename profile\u2026"))
        self.g_rename_profile.connect('clicked', self.on_rename_profile)
        button_box.pack_start(self.g_rename_profile, False, False, 0)

        self.g_delete_profile = Gtk.Button.new_with_mnemonic(_(u"_Delete profile\u2026"))
        self.g_delete_profile.connect('clicked', self.on_delete_profile)
        button_box.pack_start(self.g_delete_profile, False, False, 0)

        hbox.pack_start(button_box, False, False, 0)
        self.g_liststore = liststore = Gtk.ListStore(GObject.TYPE_STRING)
        liststore.append((_("Standard profile"),))
        if os.path.exists(os.path.join(filesystem.app_data(), 'profiles')):
            for subdir in os.listdir(os.path.join(filesystem.app_data(),
                'profiles')):
                liststore.append((subdir,))
        #
        self.g_tw = tw = Gtk.TreeView(liststore)
        tw.connect('row-activated', lambda a, b, c: self.response(Gtk.ResponseType.ACCEPT))
        tw.set_headers_visible(False)
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(None, renderer, text=0)
        tw.append_column(column)
        hbox.pack_start(tw, False, False, 0)
        tw.show()
        tw.connect('cursor-changed', self.on_cursor_changed)
        tw.set_cursor((0,))
        for idx, s in enumerate(self.g_liststore):
            if s[0].decode("utf-8") == default_profile:
                tw.set_cursor((idx, ))
        #
        chk = gu.nCheckButton("app", "noprofilemanager", _("D_on't ask at startup"))
        vbox.pack_start(chk, False, False, 0)
        self.show_all()
    def on_create_profile(self, w):
        dlg = NewProfileDialog()
        dlg.show_all()
        ret = dlg.run()
        if ret == Gtk.ResponseType.ACCEPT:
            pdir = os.path.join(filesystem.app_data(),
                                u"profiles", dlg.g_entry.get_text().decode("utf-8"))
            if not os.path.exists(pdir):
                try:
                    os.makedirs(pdir)
                    self.g_liststore.append((dlg.g_entry.get_text().decode("utf-8"),))
                    self.g_tw.set_cursor((len(self.g_liststore)-1,))
                except OSError, e:
                    gu.display_exception_message(e)
        dlg.destroy()
    def on_rename_profile(self, w):
        if self.m_default_profile == self.get_profile():
            rename_default = True
        else:
            rename_default = False
        dlg = RenameProfileDialog(self.get_profile())
        dlg.show_all()
        ret = dlg.run()
        if ret == Gtk.ResponseType.ACCEPT:
            path, column = self.g_tw.get_cursor()
            it = self.g_liststore.get_iter(path)
            try:
                os.rename(os.path.join(
                    filesystem.app_data(), u"profiles", self.get_profile()),
                    os.path.join(filesystem.app_data(),
                        u"profiles", dlg.g_entry.get_text().decode("utf-8")))
                if rename_default:
                    self.m_default_profile = dlg.g_entry.get_text().decode("utf-8")
            except OSError, e:
                gu.display_exception_message(e)
                dlg.destroy()
                return
            path, column = self.g_tw.get_cursor()
            self.g_liststore.set(self.g_liststore.get_iter(path),
                0, dlg.g_entry.get_text().decode("utf-8"))
        dlg.destroy()
    def on_delete_profile(self, w):
        if gu.dialog_yesno(_(u"Permanently delete the user profile «%s»?") % self.get_profile(), self):
            path, column = self.g_tw.get_cursor()
            it = self.g_liststore.get_iter(path)
            try:
                shutil.rmtree(os.path.join(filesystem.app_data(), u"profiles", self.get_profile()))
            except OSError, e:
                gu.display_exception_message(e)
                return
            self.g_liststore.remove(it)
            if not self.g_liststore.iter_is_valid(it):
                it = self.g_liststore[-1].iter
            self.g_tw.set_cursor(self.g_liststore.get_path(it))
    def on_cursor_changed(self, treeview):
        path, column = self.g_tw.get_cursor()
        if path:
            self.g_delete_profile.set_sensitive(list(path) != [0])
            self.g_rename_profile.set_sensitive(list(path) != [0])
    def get_profile(self):
        """
        Return None if the standard profile is selected.
        Return the directory name for other profiles.
        """
        cursor = self.g_tw.get_cursor()
        if list(cursor[0]) == [0]:
            return None
        it = self.g_liststore.get_iter(cursor[0])
        return self.g_liststore.get(it, 0)[0].decode("utf-8")


class ProfileManager(ProfileManagerBase):
    def __init__(self, default_profile):
        ProfileManagerBase.__init__(self, default_profile)
        self.add_button(Gtk.STOCK_QUIT, Gtk.ResponseType.CLOSE)
        b = self.add_button(_("_Start GNU Solfege"), Gtk.ResponseType.ACCEPT)
        b.grab_focus()
        self.set_default_response(Gtk.ResponseType.ACCEPT)


class ChangeProfileDialog(ProfileManagerBase):
    def __init__(self, default_profile):
        ProfileManagerBase.__init__(self, default_profile)
        self.add_button(Gtk.STOCK_APPLY, Gtk.ResponseType.ACCEPT)

