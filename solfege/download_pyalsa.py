# vim: set fileencoding=utf-8 :
# GNU Solfege - free ear training software
# Copyright (C) 2010, 2011  Tom Cato Amundsen
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


import os
import sys
import urllib

from gi.repository import Gtk

import solfege
from solfege import gu

pyalsa_ver = "1.0.26"

try:
    import pyalsa
except ImportError:
    pyalsa = None


def download():
    pdir = os.path.expanduser("~")
    url = "ftp://ftp.alsa-project.org/pub/pyalsa/pyalsa-%s.tar.bz2" % pyalsa_ver
    bz2 = "pyalsa-%s.tar.bz2" % pyalsa_ver
    _pyalsa_ver = pyalsa_ver
    bz2abs = os.path.join(pdir, bz2)

    m = Gtk.MessageDialog(solfege.win, Gtk.DialogFlags.MODAL, Gtk.MessageType.QUESTION,
            message_format="Download python modules?")
    m.add_button("Cancel", Gtk.ResponseType.CANCEL)
    m.add_button(Gtk.STOCK_EXECUTE, Gtk.ResponseType.ACCEPT)
    m.format_secondary_markup(u"""This will download «%(url)s» and build it in a subdirectory of %(pdir)s.

This is what the program will do for you:

<span font_family="monospace">$ wget %(url)s
$ tar xjf %(bz2)s
$ cd pyalsa-%(_pyalsa_ver)s
$ python setup.py build</span>

You will be given instructions how to make Solfege find the module after
it have been built.

If you get an error message about missing alsa/asoundlib.h, then you
must install the ALSA kernel headers. On Debian or Ubuntu you do this
by installing the libasound2-dev package.
____________________________________________________________________________________________________
""" % locals())
    # The long ____ in the string above is there to make the dialog wider
    # so that the command lines does not wrap.
    m.set_default_response(Gtk.ResponseType.YES)
    ret = m.run()
    m.destroy()
    if ret in (Gtk.ResponseType.CANCEL, Gtk.ResponseType.DELETE_EVENT):
        return
    logwin = gu.LogWindow(solfege.win)
    def progress_callback(count, size, total):
        if total == -1:
            total = 'unknown'
        logwin.write("Downloading %s of %s bytes\n" % (count * size, total))
    try:
        if not os.path.exists(bz2abs):
            urllib.urlretrieve(url, bz2abs, progress_callback)
    except IOError, e:
        logwin.write(str(e).decode(sys.getfilesystemencoding(), 'replace'))
        logwin.write("\nFailed to download alsa Python modules.")
        logwin.run_finished()
        return
    try:
        logwin.popen(["tar", "xjf", bz2], cwd=pdir)
    except OSError, e:
        logwin.write("\nExtracting %s failed.\n" % bz2)
        logwin.write("Make sure tar and bz2 is installed.\n")
        logwin.write("Could not build ALSA python module.\n")
        logwin.run_finished()
        return
    try:
        ret = logwin.popen(["python", "setup.py", "build"],
            cwd=os.path.join(pdir, "pyalsa-%s" % pyalsa_ver))
        if ret != 0:
            logwin.write("\nRunning the python interpreter failed.\nCould not build ALSA python module.")
            logwin.run_finished()
            return
    except OSError, e:
        logwin.write("\nRunning the python interpreter failed.\nCould not build ALSA python module.")
        logwin.run_finished()
        return
    sys.path.append(os.path.join(pdir, "pyalsa-%s" % pyalsa_ver))
    import pyalsa
    reload(pyalsa)
    print pyalsa
    logwin.write("\npyalsa module: %s\n\n" % str(pyalsa))
    logwin.write("The module is built. Now you must make Solfege find it.\n")
    logwin.write("There are some ways to do it:\n")
    logwin.write("\nIf you run bash, you can add this to ~/.bashrc:\n")
    logwin.write("export PYTHONPATH=%s\n\n" % os.path.join(pdir, "pyalsa-%s" % pyalsa_ver))
    logwin.write("Or start solfege this way:\n")
    logwin.write("$ PYTHONPATH=%s solfege\n" % os.path.join(pdir, "pyalsa-%s" % pyalsa_ver))
    logwin.write("\nOr install it so that it is found automatically:")
    logwin.write(("\n$ cd %(pdir)s/pyalsa-" % locals())+pyalsa_ver)
    logwin.write("\n$ sudo python setup.py install")
    logwin.write("\n\nOr if you don't have sudo setup:")
    logwin.write('\n$ su -c "python setup.py install"')
    logwin.write("")

    logwin.run_finished()

