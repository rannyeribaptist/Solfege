# GNU Solfege - free ear training software
# Copyright (C) 2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2011  Tom Cato Amundsen
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

import optparse
import sys

class SolfegeOptionParser(optparse.OptionParser):
    def __init__(self):
        optparse.OptionParser.__init__(self)
        self.add_option('-v', '--version', action='store_true', dest='version')
        self.add_option('-w', '--warranty', action='store_true', dest='warranty',
            help=_('Show warranty and copyright.'))
        self.add_option('--no-splash', action='store_true', dest='no_splash',
            help=_('Do not show the startup window.'),
            default=False)
        self.add_option('--verbose-sound-init', action='store_true',
            default=False,
            dest='verbose_sound_init',
            help=_('Display more info about the sound setup.'))
        self.add_option('--no-sound', action='store_true', dest='no_sound',
            default=False,
            help=_('Do not play any sounds. Instead some data is printed to standard output. Use this for debugging and porting.'))
        self.add_option('--debug', action='store_true', dest='debug',
            help=_('Include features used by the Solfege developers to debug the program.'))
        self.add_option('--debug-level', dest="debug_level",
            # translators: dont transate the actual debug levels
            help=_('Valid debug values are: debug, info, warning, error, critical'))
        self.add_option('--disable-exception-handler', action='store_true',
            dest='disable_exception_handler',
            help=_("Disable the exception handling in Gui.standard_exception_handler."))
        self.add_option('--no-random', action='store_true', dest='no_random',
            help=_('For debugging only: Select questions from lesson files in sequential order.'))
        self.add_option('--show-gtk-warnings', action='store_true',
            dest='show_gtk_warnings',
            help=_('Show GtkWarnings and PangoWarnings in the traceback window.'))
        self.add_option('-P', dest="profile",
            help=_('Start with <profile>. Create the profile if it does not exist.'))
        self.add_option('--make-screenshots', action='store_true',
            dest='screenshots',
            help=_("Create or update the screenshots for the user manual. Intended for developers of this program."))
    def print_help(self, outfile=None):
        if outfile is None:
            outfile = sys.stdout
        encoding = outfile.encoding
        if not encoding:
            encoding = "iso-8859-1"
        outfile.write(self.format_help().encode(encoding, 'replace'))



