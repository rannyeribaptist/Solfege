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

import os
import re
import signal
import subprocess
import sys

from solfege import filesystem

if sys.platform == 'win32':
    import ctypes


def get_drives():
    """
    Windows only function.
    ----------------------
    Return available drives.
    """
    # First we do this with maxlen = 1 to figure out how long string we need.
    i = ctypes.c_int(0)
    v = ctypes.create_string_buffer('\000')
    retval = ctypes.windll.kernel32.GetLogicalDriveStringsW(i, v)
    if retval == 0:
        raise Exception("get_drives failed. Retval==0")
    # GetLogicalDriveStringsW will return the number of chars needed.
    # So now we get the real data.
    maxlen = retval
    i = ctypes.c_int(maxlen - 1)
    v = ctypes.create_string_buffer('\000' * maxlen)
    retval = ctypes.windll.kernel32.GetLogicalDriveStringsA(i, v)
    return [x for x in v.raw.split("\000") if x]


class OsUtilsException(Exception):
    pass

class RunningExecutableFailed(OsUtilsException):
    def __init__(self, cmd):
        OsUtilsException.__init__(self,
          _("Running the command %s failed.") % cmd)

class ExecutableDoesNotExist(OsUtilsException):
    """
    We should raise this exception if os.system fails and returns
    anything else than 0.
    """
    def __init__(self, cmd):
        OsUtilsException.__init__(self,
          _("The executable '%s' does not exist.") % cmd)


class BinaryBaseException(OsUtilsException):
    def __init__(self, binary, exception):
        OsUtilsException.__init__(self)
        self.msg2 = _("Tried `%(bin)s`:\n\n\t%(exception)s\n\n"
            "Please check that the program is installed. If you did not supply "
            "the full path to the program in the preferences window (Ctrl-F12), "
            "you must make sure the program is on your PATH.") % {
             'bin': str(binary).decode(sys.getfilesystemencoding(), 'replace'),
             'exception': str(exception).decode(
                 sys.getfilesystemencoding(), 'replace')}

class BinaryForProgramException(BinaryBaseException):
    def __init__(self, program_name, binary, exception):
        BinaryBaseException.__init__(self, binary, exception)
        self.msg1 = _("Failed to execute a binary for %s") % program_name

class BinaryForMediaPlayerException(BinaryBaseException):
    def __init__(self, typeid, binary, exception):
        BinaryBaseException.__init__(self, binary, exception)
        self.msg1 = _("Failed to execute media player for %s files") % typeid.upper()

class BinaryForMediaConvertorException(BinaryBaseException):
    r = re.compile("app/(?P<from>[a-z0-9]+)_to_(?P<to>[a-z0-9]+)_cmd")
    def __init__(self, varname, binary, exception):
        BinaryBaseException.__init__(self, binary, exception)
        m = self.r.match(varname)
        self.msg1 = _("Failed to execute binary to convert from %(from)s to %(to)s") % {
            'to': m.group('to').upper(),
            'from': m.group('from').upper()
        }


__all__ = [
    'OsUtilsException',
    'ExecutableDoesNotExist',
    'BinaryForProgramException',
]


if sys.version_info < (2, 6):
    # PY26
    class Popen(subprocess.Popen):
        """
        We define this class because Popen.kill was added in Python 2.6,
        and we want to run with 2.5 too.
        """
        def __init__(self, *args, **kwargs):
            subprocess.Popen.__init__(self, *args, **kwargs)
        def kill(self):
            if sys.platform == 'win32':
                # http://code.activestate.com/recipes/347462/
                PROCESS_TERMINATE = 1
                handle = ctypes.windll.kernel32.OpenProcess(PROCESS_TERMINATE, False, self.pid)
                ctypes.windll.kernel32.TerminateProcess(handle, -1)
                ctypes.windll.kernel32.CloseHandle(handle)
            else:
                os.kill(self.pid, signal.SIGKILL)
                self.wait()
else:
    Popen = subprocess.Popen

class PopenSingleton(object):
    """
    A special version of Popen that will kill the previous program
    started. We use this when running programs using the cmdline lessonfile
    command, and possible other places where we want to run external program
    that should be killed before a new is run.
    """

    class __impl(Popen):
        """ Implementation of the singleton interface """

        def spam(self):
            """ Test method, return singleton id """
            return id(self)

    # storage for the instance reference
    __instance = None

    def __init__(self, *args, **kwargs):
        """ Create singleton instance """
        # Check whether we already have an instance
        if PopenSingleton.__instance is not None:
            PopenSingleton.__instance.kill()
            PopenSingleton.__instance = None
        if PopenSingleton.__instance is None:
            # Create and remember instance
            PopenSingleton.__instance = PopenSingleton.__impl(*args, **kwargs)

        # Store instance reference as the only member in the handle
        self.__dict__['_PopenSingleton__instance'] = PopenSingleton.__instance

    def __getattr__(self, attr):
        """ Delegate access to implementation """
        return getattr(self.__instance, attr)

    def __setattr__(self, attr, value):
        """ Delegate access to implementation """
        return setattr(self.__instance, attr, value)


def find_progs(execs):
    """
    Return a list of full path names to the executables named in execs
    if they are found on the path. Avoid duplicates caused by the same
    directory listed more than once in the PATH variable.

    execs - a tuple of possible executable names
    """
    assert isinstance(execs, (list, tuple,))
    retval = set()
    for p in os.environ['PATH'].split(os.pathsep):
        for e in execs:
            ex = os.path.join(p, e)
            if os.path.isfile(ex):
                retval.add(ex)
    return retval


def find_mma_executables(ignore_drives):
    """
    Return a set of command lines that we think will run MMA.
    ignore_drives is only used on win32. It is ignored on other operating
    systems.
    """
    if sys.platform != 'win32':
        return find_progs(("mma",))
    else:
        retval = set()
        for drive in get_drives():
            if drive.upper() in ignore_drives:
                continue
            try:
                for dirname in os.listdir(drive):
                    if dirname.lower().startswith('mma'):
                        dir = os.path.join(drive, dirname)
                        mma_py = os.path.join(drive, dirname, "mma.py")
                        if os.path.exists(mma_py):
                            retval.add(mma_py)
                        mma_bat = os.path.join(drive, dirname, "mma.bat")
                        if os.path.exists(mma_bat):
                            retval.add(mma_bat)
            except WindowsError:
                # People have had this exception raised:
                # WindowsError: [Error 21] The device is not ready: 'X:\\*.*'
                # So we choose to continue with the next drive if anything
                # unexcepted happens.
                continue
    return retval

def find_csound_executables():
    """
    Return a list of possible csound executables.
    Currently we return the name of the csound binary found as
    %PROGRAMFILES%\csound\bin\csound.exe
    """
    retval = find_progs(('csound.exe', 'csound'))
    if sys.platform == 'win32':
        fn = os.path.join(filesystem.win32_program_files_folder(),
            "csound", "bin", "csound.exe")
        if os.path.exists(fn):
            retval.add(fn)
    return retval

