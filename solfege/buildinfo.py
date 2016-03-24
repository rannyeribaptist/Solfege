# solfege/buildinfo.py.  Generated from buildinfo.py.in by configure.
#
# GNU Solfege - free ear training software
# Copyright (C) 2000, 2001, 2002, 2003, 2004, 2005, 2006  Tom Cato Amundsen
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

from solfege._version import version_info

VERSION_STRING = '3.22.2'
REVISION_ID = 'tca@gnu.org-20131005204946-k0k0e5z23bk8lqfp'
HAVE_LINUX_AWE_VOICE_H = "@HAVE_LINUX_AWE_VOICE_H@" == "yes"
ENABLE_TUNER = "no" == "yes"
prefix = "/usr/local"

def is_release():
    """
    Return True if we are a official release, either devel or stable.
    Return False if we are running from a bzr branch.
    """
    return (version_info['revision_id'] == REVISION_ID and
            'bzr-checkout' not in VERSION_STRING)


def get_bzr_revision_info_list():
    return (u"branch_nick: %s" % version_info['branch_nick'],
            u"revno: %s" % version_info['revno'],
            u"revision_id: %s" % (version_info['revision_id']).decode("ascii"),
            u"clean: %s" % version_info['clean'])


def get_bzr_revision_info_pmwiki():
    return u"[[<<]]".join(get_bzr_revision_info_list())

