# GNU Solfege - free ear training software
# Copyright (C) 2000, 2001, 2002, 2003, 2004, 2007, 2008, 2011  Tom Cato Amundsen
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

from gi.repository import GObject
from gi.repository import Gtk

from solfege import cfg
from solfege import gu
from solfege import mpd

class IntervalCheckBox(Gtk.HBox):
    """
    Emit 'value-changed' if the state of an interval has changed.
    """
    __gsignals__ = {
        'value-changed': (GObject.SIGNAL_RUN_FIRST, None,
                      (str,))
    }
    def __init__(self):
        Gtk.HBox.__init__(self)
        self.checkbox_dict = {}
        for x in range(1, mpd.interval.max_interval + 1):
            self.checkbox_dict[x] = c \
                = Gtk.ToggleButton(mpd.interval.short_name[x])
            c.connect('toggled', self.on_toggle)
            c.show()
            self.pack_start(c, True, True, 0)
    def on_toggle(self, _o):
        self.emit('value-changed', self.get_value())
    def get_value(self):
        """
        Return a list with the integer value for the intervals
        that are active.
        """
        return [x for x in self.checkbox_dict.keys() \
                if self.checkbox_dict[x].get_active()]
    def set_value(self, v):
        """
        Set the state of the intervals.
        v is a list of integers representing the intervals that are
        active.
        """
        for key, btn in self.checkbox_dict.items():
            self.checkbox_dict[key].set_active(key in v)
        return


class nIntervalCheckBox(IntervalCheckBox, cfg.ConfigUtils):
    def __init__(self, exname, varname):
        IntervalCheckBox.__init__(self)
        cfg.ConfigUtils.__init__(self, exname)
        self.m_varname = varname
        intervals = self.get_list(self.m_varname)
        if not intervals:
            intervals = range(1, mpd.interval.max_interval)
            self.set_list(varname, intervals)
        self.set_value(intervals)
        self.add_watch(self.m_varname, self._watch_cb)
    def _watch_cb(self, name):
        self.set_value(self.get_list(self.m_varname))
    def on_toggle(self, _o):
        IntervalCheckBox.on_toggle(self, _o)
        self.set_list(self.m_varname, self.get_value())


class MultipleIntervalConfigWidget(Gtk.VBox, cfg.ConfigUtils):
    """
    This class gives  you some spin buttons and two rows of buttons
    where you select what intervals to use for exercises where you
    select one or more intervals.
    """
    def __init__(self, exname):
        Gtk.VBox.__init__(self)
        cfg.ConfigUtils.__init__(self, exname)
        self.MAX_INT = self.get_int('maximum_number_of_intervals')
        if self.MAX_INT == 0:
            self.MAX_INT = 12
        self._watched_interval_id = None
        self._watched_interval = None
        self.m_ignore_iclick = 0
        box = gu.bHBox(self, expand=False)
        box.set_spacing(gu.PAD_SMALL)
        box.pack_start(Gtk.Label(_("Number of intervals:")), False, False, 0)
        self.g_num_int_spin = gu.nSpinButton(self.m_exname,
                       'number_of_intervals',
                       Gtk.Adjustment(1, 1, self.MAX_INT, 1, self.MAX_INT))
        self.add_watch('number_of_intervals', self.on_num_int_spin)
        box.pack_start(self.g_num_int_spin, False, False, 0)
        self.g_all_int_button = gu.bButton(box,
                  _("Configure all intervals in this exercise like this"),
                  self.configure_all_like_active_interval, expand=False)
        self.add_watch('number_of_intervals', lambda n, self=self: \
               self.g_all_int_button.set_sensitive(self.get_int(n)!=1))

        box = gu.bHBox(self, expand=False)
        box.set_spacing(gu.PAD_SMALL)
        box.pack_start(Gtk.Label(
                _("Toggle buttons are for interval number:")), False, False, 0)
        self.m_int_sel_adjustment \
             = Gtk.Adjustment(1, 1, self.get_int('number_of_intervals'), 1)
        self.g_int_sel_spin = gu.nSpinButton(self.m_exname,
                  'cur_edit_interval', self.m_int_sel_adjustment, digits=0)
        self.g_int_sel_spin.connect('changed', self.on_int_sel_spin)
        box.pack_start(self.g_int_sel_spin, False, False, 0)
        table = Gtk.Table()
        self.pack_start(table, False, False, 0)

        label = Gtk.Label(label=_("Up:"))
        label.set_alignment(1.0, 0.5)
        table.attach(label, 0, 1, 0, 1, xpadding=gu.PAD_SMALL)
        self.g_interval_chk = {}
        V = self.get_list("ask_for_intervals_%i"
                  % (self.g_int_sel_spin.get_value_as_int()-1))
        for x in range(1, mpd.interval.max_interval + 1):
            self.g_interval_chk[x] = c = Gtk.ToggleButton(mpd.interval.short_name[x])
            if x in V:
                c.set_active(True)
            c.show()
            c.connect('clicked', self.on_interval_chk_clicked, x)
            table.attach(c, x, x+1, 0, 1)

        box = gu.bHBox(self, expand=False)
        label = Gtk.Label(label=_("Down:"))
        label.set_alignment(1.0, 0.5)
        table.attach(label, 0, 1, 1, 2, xpadding=gu.PAD_SMALL)
        v = range(mpd.interval.min_interval, 0)
        v.reverse()
        for x in v:
            self.g_interval_chk[x] = c = Gtk.ToggleButton(mpd.interval.short_name[-x])
            if x in V:
                c.set_active(True)
            c.show()
            c.connect('clicked', self.on_interval_chk_clicked, x)
            table.attach(c, -x, -x+1, 1, 2)
        table.show_all()
        if self.g_num_int_spin.get_value_as_int() == 1:
            self.g_all_int_button.set_sensitive(False)
        gu.bButton(self, _("Reset to default values"), self.reset_to_default,
                  False, False)
        self._watch_interval(self.get_int('cur_edit_interval')-1)
    def reset_to_default(self, _o):
        self.set_int('cur_edit_interval', 1)
        self.set_int('number_of_intervals', 1)
        self.set_list('ask_for_intervals_0', range(-12, 0)+range(1, 13))
    def configure_all_like_active_interval(self, _o):
        v = self.get_list('ask_for_intervals_%i' \
                               % (self.g_int_sel_spin.get_value_as_int()-1))
        for i in range(self.get_int('number_of_intervals')):
            self.set_string('ask_for_intervals_%i' % i, str(v))
    def on_interval_chk_clicked(self, widget, interval):
        if self.m_ignore_iclick:
            return
        i = self.g_int_sel_spin.get_value_as_int() - 1
        v = self.get_list('ask_for_intervals_%i' % i)
        if widget.get_active():
            if not interval in v:
                v.append(interval)
        else:
            if interval in v:
                del v[v.index(interval)]
        self.set_list('ask_for_intervals_%i' % i, v)
    def on_num_int_spin(self, _o):
        adj = Gtk.Adjustment(self.get_int('cur_edit_interval'), 1,
                  self.get_int('number_of_intervals'), 1, self.MAX_INT)
        self.g_int_sel_spin.set_adjustment(adj)
        self.g_int_sel_spin.update()
    def on_int_sel_spin(self, spin):
        self._watch_interval(spin.get_value_as_int()-1)
        self.update_togglebuttons(spin.get_value_as_int()-1)
    def update_togglebuttons(self, i):
        self.m_ignore_iclick = 1
        v = self.get_list('ask_for_intervals_%i' % i)
        for i in range(mpd.interval.min_interval, 0)+range(1, mpd.interval.max_interval + 1):
            self.g_interval_chk[i].set_active(i in v)
        self.m_ignore_iclick = 0
    def _watch_interval(self, i):
        """
        Add a watch for the correct ask_for_intervals_%i variable.
        Remove old watches. Do nothing if we are already watching the
        correct data.
        """
        if self._watched_interval == i:
            return
        if self._watched_interval is not None:
            self.remove_watch('ask_for_intervals_%i' % self._watched_interval,
                          self._watched_interval_id)
        self._watched_interval = i
        self._watched_interval_id = self.add_watch('ask_for_intervals_%i' % i,
                                                  self._interval_watch_cb)
    def _interval_watch_cb(self, name):
        self.update_togglebuttons(self._watched_interval)
