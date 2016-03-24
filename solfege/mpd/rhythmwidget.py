# GNU Solfege - free ear training software
# Copyright (C) 2011  Tom Cato Amundsen
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

import copy
import os

from gi.repository import GObject, Gdk, Gtk


if __name__ == '__main__':
    import sys
    sys.path.insert(0, ".")
    import solfege.i18n
    solfege.i18n.setup(".")

from solfege.mpd import Duration
from solfege.mpd import MusicalPitch
from solfege.mpd import elems
from solfege.mpd import engravers
from solfege.mpd.musicdisplayer import MusicDisplayer


class RhythmWidgetController(Gtk.HBox):
    def __init__(self, rwidget):
        """
        rwidget is the RhythmWidget we are controlling
        """
        Gtk.HBox.__init__(self)
        self.g_rwidget = rwidget
        self.g_rwidget.connect('cursor-moved', self.on_cursor_moved)
        for k in (1, 2, 4, 8, 16, 32):
            im = Gtk.Image()
            im.set_from_file(os.path.join("graphics", "note-%i.svg"% k))
            b = Gtk.Button()
            b.add(im)
            self.pack_start(b, False, False, 0)
            def f(widget, i):
                added = self.g_rwidget.on_add_item(elems.Note(
                    MusicalPitch.new_from_notename("c"),
                    Duration(i, 0)))
                if self.g_add_dots_toggle.get_active():
                    self.g_rwidget.on_toggle_dots(1)
                if added:
                    self.g_rwidget.cursor_next()
                self.g_rwidget.grab_focus()
            b.connect('clicked', f, k)
        for k in (1, 2, 4, 8, 16, 32):
            im = Gtk.Image()
            im.set_from_file(os.path.join("graphics", "rest-%i.svg" % k))
            b = Gtk.Button()
            b.add(im)
            self.pack_start(b, False, False, 0)
            def f(widget, i):
                added = self.g_rwidget.on_add_item(elems.Rest(
                    Duration(i, 0)))
                if self.g_add_dots_toggle.get_active():
                    self.g_rwidget.on_toggle_dots(1)
                if added:
                    self.g_rwidget.cursor_next()
                self.g_rwidget.grab_focus()
                self.g_rwidget.score_updated()
            b.connect('clicked', f, k)
        # For simplicity, we use two buttons. One normal button for
        # adding dots, and a ToggleButton that will put a dot on new notes.
        im = Gtk.Image()
        im.show()
        im.set_from_file(os.path.join("graphics", "add-dot.svg"))
        self.g_add_dots = b = Gtk.Button()
        self.g_add_dots.set_no_show_all(True)
        b.add(im)
        b.connect('clicked', self.on_toggle_dots, 1)
        self.pack_start(b, False, False, 0)
        #
        im = Gtk.Image()
        im.set_from_file(os.path.join("graphics", "dot-mode.svg"))
        self.g_add_dots_toggle = b = Gtk.ToggleButton()
        b.connect('clicked', lambda w: self.g_rwidget.grab_focus())
        b.add(im)
        self.pack_start(b, False, False, 0)
        #
        im = Gtk.Image()
        im.set_from_file(os.path.join("graphics", "remove-dot.svg"))
        b = Gtk.Button()
        b.add(im)
        b.connect('clicked', self.on_toggle_dots, -1)
        self.pack_start(b, False, False, 0)
        im = Gtk.Image()
        im.set_from_file(os.path.join("graphics", "tie.svg"))
        b = Gtk.Button()
        b.add(im)
        b.connect('clicked', self.on_toggle_tie)
        self.pack_start(b, False, False, 0)
        im = Gtk.Image()
        im.set_from_stock(Gtk.STOCK_DELETE, Gtk.IconSize.MENU)
        b = Gtk.Button()
        b.add(im)
        b.connect('clicked', self.ctrl_on_delete)
        self.pack_start(b, False, False, 0)
        self.g_mode = Gtk.ToggleButton(_i("insert-overwrite|INSRT"))
        self.g_mode.connect('clicked', self.ctrl_on_ins)
        self.g_rwidget.m_ins_mode = not self.g_mode.get_active()
        self.pack_start(self.g_mode, False, False, 0)
        self.show_all()
    def ctrl_on_ins(self, button):
        self.g_rwidget.m_ins_mode = not self.g_mode.get_active()
        self.g_mode.set_label({False: _i("insert-overwrite|INSRT"),
            True: _i("insert-overwrite|OVER")}[button.get_active()])
        self.g_rwidget.grab_focus()
    def ctrl_on_delete(self, button):
        self.g_rwidget.delete()
        self.g_rwidget.grab_focus()
    def on_toggle_dots(self, button, delta):
        self.g_rwidget.on_toggle_dots(delta)
        self.g_rwidget.grab_focus()
    def on_toggle_tie(self, button):
        self.g_rwidget.on_toggle_tie()
        self.g_rwidget.grab_focus()
    def set_editable(self, b):
        self.g_rwidget.m_editable = b
        self.g_rwidget.queue_draw()
        self.set_sensitive(b)
    def on_cursor_moved(self, *w):
        e = self.g_rwidget.m_score.voice11.m_tdict[self.g_rwidget.get_cursor_timepos()]
        if isinstance(e['elem'][0], elems.Skip):
            self.g_add_dots.hide()
            self.g_add_dots_toggle.show()
        else:
            self.g_add_dots.show()
            self.g_add_dots_toggle.hide()


class RhythmWidget(MusicDisplayer):
    """
    Rhythm widget editor.
    Before editing, we feed it a Score objects with notes and/or
    skips. The user is not allowed to add skips in the middle of
    the rhythm. Only rests.
    """
    skipdur = Duration(4, 0)
    NOTE_INPUT = 1
    REST_INPUT = 2
    def __init__(self):
        MusicDisplayer.__init__(self)
        #self.g_d.connect("draw", self.on_draw)
        self.add_events(Gdk.EventMask.KEY_RELEASE_MASK)
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.connect("key-press-event", self.on_key_press)
        #self.set_flags(Gtk.CAN_FOCUS)
        def f(*w):
            self.grab_focus()
        self.connect("button-press-event", f)
        self.m_cursor = None
        self.m_input_mode = RhythmWidget.NOTE_INPUT
    def get_cursor_timepos(self):
        """
        Return the timepos the cursor has. Return None if the
        cursor is not visible, for example when the staff is completely
        empty.
        """
        if self.m_cursor is None:
            return
        if not self.m_score.m_staffs:
            return None
        timeposes = self.m_score.m_staffs[0].get_timeposes()
        if timeposes:
            return self.m_score.m_staffs[0].get_timeposes()[self.m_cursor]
        return
    def cursor_prev(self):
        if self.m_cursor > 0:
            self.m_cursor -= 1
            self.adjust_hadjustment()
            self.emit('cursor-moved')
    def cursor_next(self):
        if self.m_cursor < len(self.m_score.m_staffs[0].get_timeposes()) - 1:
            self.m_cursor += 1
            self.adjust_hadjustment()
            self.emit('cursor-moved')
    def backspace(self):
        if self.m_cursor > 0:
            self.cursor_prev()
            self.delete()
            self.adjust_hadjustment()
            self.emit('cursor-moved')
    def on_key_press(self, window, event):
        if not self.m_editable:
            return
        key_dict = {Gdk.KEY_1: 1,
                    Gdk.KEY_2: 2,
                    Gdk.KEY_3: 4,
                    Gdk.KEY_4: 8,
                    Gdk.KEY_5: 16,
                    Gdk.KEY_6: 32,
        }
        if event.keyval in (Gdk.KEY_Right, Gdk.KEY_KP_Right):
            self.cursor_next()
            self.queue_draw()
        elif event.keyval in (Gdk.KEY_Left, Gdk.KEY_KP_Left):
            self.cursor_prev()
            self.queue_draw()
        elif event.keyval == Gdk.KEY_BackSpace:
            self.backspace()
        elif event.keyval in (Gdk.KEY_Delete, Gdk.KEY_KP_Delete):
            self.delete()
        elif event.keyval in key_dict:
            if self.m_input_mode == self.NOTE_INPUT:
                added = self.on_add_item(elems.Note(MusicalPitch.new_from_notename("c"),
                    Duration(key_dict[event.keyval], 0)))
            else:
                assert self.m_input_mode == self.REST_INPUT
                added = self.on_add_item(elems.Rest(
                    Duration(key_dict[event.keyval], 0)))
            if added:
                self.cursor_next()
            self.queue_draw()
            self.grab_focus()
        elif event.keyval == Gdk.KEY_period:
            self.on_toggle_dots(1)
        elif event.keyval == Gdk.KEY_colon:
            self.on_toggle_dots(-1)
        elif event.keyval == Gdk.KEY_t:
            self.on_toggle_tie()
        elif event.keyval == Gdk.KEY_r:
            if self.m_input_mode == self.NOTE_INPUT:
                self.m_input_mode = self.REST_INPUT
            else:
                self.m_input_mode = self.NOTE_INPUT
    def on_toggle_tie(self):
        timepos = self.get_cursor_timepos()
        if not isinstance(self.m_score.voice11.m_tdict[timepos]['elem'][0], elems.Note):
            return
        if self.m_score.voice11.m_tdict[timepos]['elem'][0].m_tieinfo in (None, 'end'):
            if self.m_score.voice11.tie_timepos(timepos):
                self.score_updated()
        elif self.m_score.voice11.m_tdict[timepos]['elem'][0].m_tieinfo in ('start', 'go'):
            if self.m_score.voice11.untie_next(timepos):
                self.score_updated()
    def delete(self):
        timepos = self.get_cursor_timepos()
        self.m_score.voice11.del_elem(timepos)
        self.score_updated()
    def on_toggle_dots(self, delta):
        """
        delta is the number of dots to add or remove.
        Return True if the number of dots was changed.
        Return False if not allowed.
        """
        timepos = self.get_cursor_timepos()
        elem = self.m_score.voice11.m_tdict[timepos]['elem'][0]
        if isinstance(elem, elems.Skip):
            return False
        if elem.m_duration.m_dots + delta < 0:
            return False
        new_elem = copy.deepcopy(self.m_score.voice11.m_tdict[timepos]['elem'][0])
        new_elem.m_duration.m_dots += delta
        if self.m_score.voice11.try_set_elem(new_elem, timepos, False):
            self.score_updated()
        return True
    def on_add_item(self, item):
        """
        Return True if an item was added.
        Return False if it was not added.
        """
        if self.m_score.voice11.try_set_elem(item, self.get_cursor_timepos(),
                self.m_ins_mode):
            self.score_updated()
            self.adjust_hadjustment()
            return True
        return False
    def set_score(self, score, cursor=0):
        self.m_score = score
        self.m_cursor = cursor
        self.score_updated()
    def score_updated(self):
        """
        Redraw the staff. This should be called whenever m_score is updated.
        It is not necessary to call when only the cursor have been moved.
        """
        self.m_scorecontext = engravers.ScoreContext(self.m_score)
        self.m_engravers = self.m_scorecontext.m_contexts
        self._display()
        if self.m_score.m_staffs:
            timeposes = self.m_score.m_staffs[0].get_timeposes()
            if self.m_cursor > len(timeposes) - 1:
                self.m_cursor = len(timeposes) - 1
        else:
            self.m_cursor = None
        self.emit('score-updated')
    def on_draw(self, darea, ct):
        MusicDisplayer.on_draw(self, darea, ct)
        timepos = self.get_cursor_timepos()
        if not timepos:
            return
        engraver = None
        for e in self.m_scorecontext.m_contexts[0].m_engravers[timepos]['elem']:
            if isinstance(e, (engravers.NoteheadEngraver,
                              engravers.RestEngraver,
                              engravers.SkipEngraver)):
                engraver = e
                break
        if not engraver:
            return
        y = engravers.dim20.first_staff_ypos + 10
        self.m_cursor_xpos = engraver.m_xpos
        ct.set_source_rgb(1.0, 0, 0)
        ct.rectangle(engraver.m_xpos, y, 10, 3)
        ct.stroke()
    def adjust_hadjustment(self):
        # Auto scrolling
        adj = self.get_hadjustment()
        if self.m_cursor_xpos > adj.get_value() + adj.get_page_size() * 0.7:
            x = self.m_cursor_xpos - adj.get_page_size() * 0.7
            if x > adj.upper - adj.get_page_size():
                x = adj.upper - adj.get_page_size()
            adj.set_value(x)
        if self.m_cursor == 0:
            adj.set_value(0.0)
        if self.m_cursor_xpos < adj.get_value() + adj.get_page_size() * 0.3:
            x = self.m_cursor_xpos - adj.get_page_size() * 0.3
            if x < 0:
                x = 0
            adj.set_value(x)

GObject.signal_new('cursor-moved', RhythmWidget, GObject.SignalFlags.RUN_FIRST,
    None, tuple())
GObject.signal_new('score-updated', RhythmWidget, GObject.SignalFlags.RUN_FIRST,
    None, tuple())

class TestWin(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self)
        vbox = Gtk.VBox()
        self.add(vbox)
        self.set_default_size(600, 400)
        self.w = RhythmWidget()
        s = elems.Score()
        s.add_staff(staff_class=elems.RhythmStaff)
        s.add_bar(elems.TimeSignature(3, 4))
        s.add_bar(elems.TimeSignature(3, 4))
        s.voice11.fill_with_skips()
        self.w.set_score(s)
        vbox.pack_start(self.w, True, True, 0)
        #
        c = RhythmWidgetController(self.w)
        vbox.pack_start(c, False, False, 0)
        c.show()
        c.set_editable(True)
        self.connect('delete_event', self.quit)
    def quit(self, *w):
        Gtk.main_quit()

if __name__ == '__main__':
    w = TestWin()
    w.show_all()
    Gtk.main()
