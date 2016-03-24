#/usr/bin/python
# GNU Solfege - free ear training software
# Copyright (C) 2006, 2007, 2008, 2011  Tom Cato Amundsen
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

import glob
import subprocess
import os.path
import sys
import pprint
import re
sys.path.append(".")


def create_languages_py():
    f = file("solfege/languages.py", "w")

    print >> f, "# Generated at build time by tools/buildscript.py"
    print >> f, "# Do not edit. Changes will be lost."
    print >> f, "C_locale_idx = 1"
    print >> f, "languages = ["
    print >> f, "  'system default',"
    print >> f, "  'English/United States [en-us]',"
    for fn in glob.glob("po/*.po"):
        print >> f, "   '%s'," % os.path.splitext(os.path.basename(fn))[0]
    print >> f, "]"
    f.close()


def create_manpage():
    sys.argv = ['solfege']
    import solfege.i18n
    solfege.i18n.setup(".")
    import solfege.optionparser
    options = solfege.optionparser.SolfegeOptionParser().format_help().encode('iso-8859-1', 'replace')
    v = options.split("\n")
    del v[0]
    del v[0]
    del v[0]
    options = "\n".join(v)
    # This option is so long that it messes with the columns,
    # and it confuses txt2man.
    options = re.sub('--disable-exception-handler\s*',
                     '--disable-exception-handler  ', options)
    s = open("solfege.1.txt", "r").read()
    s = s.replace('XXOPTIONS', options)
    print >> sys.stdout, s


def get_last_git_sha(git=None):
    import os
    if git:
        gitcmd = git
    else:
        gitcmd = "git"
    p = subprocess.Popen(("%s log -n 1" % gitcmd).split(),
                         stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT)
    while 1:
        p.poll()
        if p.returncode is not None:
            break
        while True:
            s = p.stdout.readline()
            if s.startswith("commit"):
                return s.split(" ")[1].strip()
            if not s:
                return
    raise Exception("git_last_git_sha failed")


def create_versions_file(git):
    version_info = {'git_sha': get_last_git_sha(git)}
    with open("solfege/_version.py", "w") as f:
        print >> f, "version_info =",
        pprint.pprint(version_info, stream=f)
