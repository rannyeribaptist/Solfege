# GNU Solfege - free ear training software
# vim: set fileencoding=utf-8 :
# Copyright (C) 2006, 2007, 2008, 2009, 2011 Tom Cato Amundsen
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

# Lesson file related GUI code.

from __future__ import absolute_import

############################
# Python Standard Library
############################
import warnings

###################
from gi.repository import Gtk

###################
# Solfege modules
###################
from solfege import gu
from solfege import frontpage
from solfege import lessonfile
from solfege import mpd
import solfege


def rn_markup(s):
    v = []
    for p1, p2, p3, sep in lessonfile.rnc_markup_tokenizer(s):
        v.append('<span font_family="serif"><span size="xx-large">%s</span><span size="small">%s</span><span size="x-large">%s%s</span></span>' % (p1, p2, p3, sep))
    return "".join(v)

def chordname_markup(s):
    v = []
    for nn, mod, sup, bass in lessonfile.chordname_markup_tokenizer(s):
        if bass:
            bass = u"/%s" % mpd.MusicalPitch.new_from_notename(bass).get_user_notename()
        nn = mpd.MusicalPitch.new_from_notename(nn).get_user_notename()
        nn = nn[0].upper() + nn[1:]
        v.append('%s%s<span size="large" rise="11000">%s</span>%s' % (nn, mod, sup, bass))
    return u'<span font_family="serif" size="xx-large">%s</span>' % u" ".join(v)

def new_labelobject(label):
    """
    label can be one of the following types:
    * unicode string
    * lessonfile.LabelObject instance

    Return a gtk widget of some sort that displays the label.
    FIXME:
        If we in the future want some labels, for example chordlabel,
        to be transposable, then new_labelobject should return objects
        that are derived from Gtk.Label, and they should have a
        a is_transposable method. Then Gui.on_new must call
        QuestionNameButtonTable and make it transpose the labels.
        But I don't think translated labels should have high priority.
    """
    if isinstance(label, basestring):
        # We hope all strings are unicode, but check for basestring just
        # in case some modules are wrong.
        l = Gtk.Label(label=_i(label))
        l.show()
    else:
        if isinstance(label, tuple):
            # I think only old code
            # that has  been removed. But let us keep the code until
            # we have a chance to review.
            warnings.warn("lessonfilegui.new_labelobject: label is a tuple.",
                          DeprecationWarning)
            labeltype, labeldata = label
        else:
            labeltype = label.m_labeltype
            labeldata = label.m_labeldata
        if labeltype == 'progressionlabel':
            l = gu.HarmonicProgressionLabel(labeldata)
            l.show_all()
        else:
            l = Gtk.Label()
            if labeltype == 'rnc':
                l.set_markup(rn_markup(labeldata))
            elif labeltype == 'chordname':
                l.set_markup(chordname_markup(labeldata))
            elif labeltype == 'plabel':
                l.set_markup("""<span font_family="serif"><span size="xx-large">%s</span><span size="small">%s</span><span size="x-large">%s</span></span>""" % labeldata)

            elif labeltype == 'pangomarkup':
                l.set_markup(labeldata)
            l.show()
    return l


class LabelObjectBox(gu.AlignedHBox):
    def __init__(self, lf, v):
        """
        lf is the lesson file (aka m_P of the teacher object)
        v is a list of element names defind in the lesson file lf,
        for example:
           ['I', 'IV', 'V', 'I']
        Return a HBox that presents a label with the label names
        separated by "-".
        """
        gu.AlignedHBox.__init__(self) 
        self.setup_pre()
        for i, k in enumerate(v):
            if k in lf.m_elements:
                l = new_labelobject(lf.m_elements[k]['label'])
            else:
                l = Gtk.Label(label=k)
            self.pack_start(l, False, False)
            if i != len(v) - 1:
                l = Gtk.Label(label="-")
                self.pack_start(l, False, False)
        self.setup_post()
        self.show_all()


class ExercisesMenuAddIn(object):
    def create_learning_tree_menu(self):
        """
        Create and return a Gtk.Menu object that has submenus that
        let us select all lessons on the learning tree.
        """
        def create_menu(page):
            menu = Gtk.Menu()
            for column in page:
                for section in column:
                    item = Gtk.MenuItem(section.m_name)
                    for link in section:
                        if isinstance(link, frontpage.Page):
                            item = Gtk.MenuItem(link.m_name)
                            menu.append(item)
                            item.set_submenu(create_menu(link))
                        else:
                            assert isinstance(link, unicode)
                            # This will also alert us if the file is not
                            # found or not parsable:
                            try:
                                if lessonfile.infocache.get(link, 'module') not in ('melodicinterval', 'harmonicinterval', 'idbyname'):
                                    continue
                            except lessonfile.infocache.InfoCacheException:
                                continue

                            # We don't want to add these lesson files because we know
                            # that they cannot be exported. It would be better
                            # to catch these with a more generic algorithm, but
                            # then we would have to parse all the files, and that
                            # would be too slow.
                            if link in (
                                    # melodic-interval-self-config
                                    "f62929dc-7122-4173-aad1-4d4eef8779af",
                                    # harmonic-interval-self-config
                                    "466409e7-9086-4623-aff0-7c27f7dfd13b",
                                    # the csound-fifth-* files:
                                    "b465c807-d7bf-4e3a-a6da-54c78d5b59a1",
                                    "aa5c3b18-664b-4e3d-b42d-2f06582f4135",
                                    "5098fb96-c362-45b9-bbb3-703db149a079",
                                    "3b1f57e8-2983-4a74-96da-468aa5414e5e",
                                    "a06b5531-7422-4ea3-8711-ec57e2a4ce22",
                                    "e67c5bd2-a275-4d9a-96a8-52e43a1e8987",
                                    "1cadef8c-859e-4482-a6c4-31bd715b4787",
                                    ):
                                continue
                            item = Gtk.MenuItem(_(lessonfile.infocache.get(link, 'title')))
                            item.connect('activate', self.on_select_exercise, link)
                            menu.append(item)
            return menu

        menu = create_menu(solfege.app.m_frontpage_data)
        menu.show_all()
        self._menu_hide_stuff(menu)
        return menu
    def _menu_hide_stuff(self, menu):
        """
        Hide the menu if it has no menu items, or all menu items are hidden.
        """
        for sub in menu.get_children():
            assert isinstance(sub, Gtk.MenuItem)
            if sub.get_submenu():
                self._menu_hide_stuff(sub.get_submenu())
                if not [c for c in sub.get_submenu().get_children() if c.get_property('visible')]:
                    sub.hide()

