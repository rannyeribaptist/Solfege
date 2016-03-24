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
import os

class SoundInitException(Exception):
    pass

class SyscallException(SoundInitException):
    def __init__(self, msg, n):
        SoundInitException.__init__(self)
        self.m_msg = msg
        self.m_errno = n
    def __str__(self):
        return self.m_msg + "\n%s" % os.strerror(self.m_errno)

class SeqNoSynthsException(SoundInitException):
    def __init__(self, dev):
        SoundInitException.__init__(self)
        self.m_dev = dev
    def __str__(self):
        return "SNDCTL_SEQ_NRSYNTHS report that there are no synths on %s." % self.m_dev


