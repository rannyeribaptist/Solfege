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
class SynthCommon(object):
    def __init__(self):
        self.__test_saved_play_midieventstream = None
    def start_testmode(self):
        assert self.__test_saved_play_midieventstream is None
        self.m_test_stream = None
        self.__test_saved_play_midieventstream = self.play_midieventstream
        self.play_midieventstream = self.testmode_play_midieventstream
    def end_testmode(self):
        assert self.__test_saved_play_midieventstream is not None
        self.play_midieventstream = self.__test_saved_play_midieventstream
        self.__test_saved_play_midieventstream = None
        return self.flush_testdata()
    def flush_testdata(self, details=0):
        if self.m_test_stream:
            return self.m_test_stream.str_repr(details)
        return ""
    def testmode_play_midieventstream(self, midieventstream):
        # twostep operation because we want to sort the events
        # in a specific order
        self.m_test_stream = midieventstream

