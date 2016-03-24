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

"""
This code does not work. Also notice that is is not imported by
    from exercises import *
since it will try to import solfege_c_midi even if it is not available.
"""

from gi.repository import GObject

from solfege import abstract
from solfege import gu
from solfege import utils
from solfege import lessonfile
import solfege.soundcard.solfege_c_midi
from solfege import soundcard

class Teacher(abstract.Teacher):
    def __init__(self, exname):
        abstract.Teacher.__init__(self, exname)
        self.lessonfileclass = lessonfile.HeaderLessonfile

class Gui(abstract.Gui):
    def __init__(self, teacher):
        abstract.Gui.__init__(self, teacher)
        self.g_hz = gu.bLabel(self.practise_box, "")
        self.g_notename = gu.bLabel(self.practise_box, "")
        self.g_cent = gu.bLabel(self.practise_box, "")
    def on_start_practise(self):
        soundcard.solfege_c_midi.dsp_open_record()
        #self.__idle_tag = GObject.idle_add(self.update_view)
        self.__idle_tag = GObject.timeout_add(300, self.update_view)
    def update_view(self):
        freq = soundcard.solfege_c_midi.idle_loop()
        print freq
        notename, cent = utils.freq_to_notename_cent(freq)
        self.g_hz.set_text(str(freq))
        self.g_notename.set_text(notename)
        self.g_cent.set_text(str(cent))
        return True
    def on_end_practise(self):
        #Gtk.idle_remove(self.__idle_tag)
        GObject.source_remove(self.__idle_tag)
        soundcard.solfege_c_midi.dsp_close()
