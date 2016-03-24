# GNU Solfege - free ear training software
# Copyright (C) 2000, 2001, 2002, 2003, 2004, 2005, 2007, 2008, 2011  Tom Cato Amundsen
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
Modules that have translated messages need to import this module
to make pydoc work.
"""
import gettext
import locale
import os
import sys
import textwrap
import traceback

def _i(s):
    """
    used for translated strings with a prefix, like these:
    _("interall|m3")
    _("View-menu|_Toolbar")
    This function is required because if a entry is not translated, then
    only the string after | should be returned.
    """
    ns = _(s)
    if ns == s:
        return "%s" %(s.split('|')[-1])
    else:
        return "%s" % ns

def langs():
    ret = []
    for k in ('LANGUAGE', 'LC_ALL', 'LC_MESSAGES', 'LANG'):
        if k in os.environ:
            v = os.environ.get(k)
            if v:
                ret = v.split(':')
            break
    if 'C' not in ret:
        ret.append('C')
    retval = []
    for l in ret:
        s = locale.normalize(l)
        if len(s) >= 5 and s[2] == '_':
            retval.append(s[:5])
            retval.append(s[:2])
        else:
            retval.append(s)
    return retval

def _nop(s):
    return unicode(s)

def setup(prefix, config_locale=None):
    global locale_setup_failed
    # Gettext and gtk+ chech the variables in this order.
    try:
        locale.setlocale(locale.LC_ALL, '')
    except locale.Error, e:
        print
        print "\n".join(textwrap.wrap(
            "Failed to run locale.setlocale(locale.LC_ALL, '') "
            "Will continue without translated messages. "
            "This is not a bug in GNU Solfege. See the README file "
            "for more details."))
        print "\nIgnored the following error:"
        traceback.print_exc(file=sys.stdout)
        print
        import __builtin__
        locale_setup_failed = True
        __builtin__.__dict__['_no_xgettext'] = _nop
        __builtin__.__dict__['_'] = _nop
        __builtin__.__dict__['_i_no_xgettext'] = _nop
        __builtin__.__dict__['_i'] = _nop
        __builtin__.__dict__['ungettext'] = _nop
        return
    varlist = ('LANGUAGE', 'LC_MESSAGES')
    if not config_locale:
        config_locale = 'system default'
    if (config_locale != 'system default') and (sys.platform != 'win32'):
        for n in varlist:
            os.environ[n] = config_locale
    # FIXME can we remove this whole if block, not that set run
    # locale.setlocale(locale.LC_ALL, '') at program start??
    if (sys.platform == 'win32') and (config_locale == 'system default'):
        envar = None
        for varname in varlist:
            if varname in os.environ:
                envar = varname
                break
        if not envar:
            # We have to set the value ourselves if we don't have
            # a environment variable set.
            s = locale.getdefaultlocale()[0]
            if s:
                s = locale.normalize(s)
                os.environ['LANGUAGE'] = s
    import __builtin__
    t = gettext.translation("solfege",
                           os.path.join(prefix, 'share', 'locale'),
                           fallback=True)
    __builtin__.__dict__['_'] = t.ugettext
    __builtin__.__dict__['_no_xgettext'] = t.ugettext
    __builtin__.__dict__['_i'] = _i
    __builtin__.__dict__['_i_no_xgettext'] = _i
    __builtin__.__dict__['ungettext'] = t.ungettext
    # plurals usage:
    # i =  'some integer value'
    # ungettext("%i car", "%i cars", i) % i


