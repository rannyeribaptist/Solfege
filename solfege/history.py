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
class History:
    def __init__(self):
        self.m_list = []
        self.m_idx = -1
        self.m_lock = 0
    def add(self, data):
        """
        Add history at the current position. Data after the current
        position is lost.
        """
        if self.m_lock:
            return
        # First we remove if necessary
        self.m_list = self.m_list[:self.m_idx + 1]
        # we don't want duplicate entries in the history
        if not self.m_list or self.m_list[-1][0] != data:
            self.m_list.append([data, None])
            self.m_idx = self.m_idx + 1
    def set_adj_of_current(self, adj):
        if self.m_lock:
            raise Exception("Called set_adj_of_current when locked.")
        self.m_list[self.m_idx][1] = adj
    def back(self):
        if self.m_idx > 0:
            self.m_idx = self.m_idx - 1
    def forward(self):
        if self.m_idx + 1 < len(self.m_list):
            self.m_idx = self.m_idx + 1
    def get_current(self):
        if self.m_idx >= 0:
            return self.m_list[self.m_idx]
    def lock(self):
        "Do not record any history"
        self.m_lock = 1
    def unlock(self):
        self.m_lock = 0

