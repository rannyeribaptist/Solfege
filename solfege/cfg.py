# coding: utf-8
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
TODO:
    - cfg.get_list
    - cfg.set_list
    - watches outside ConfigUtils
>>> import cfg
>>> cfg.initialise(None, "default.config", "~/.cfg-test")
>>> cfg.set_string("section/stringvar", "value")
>>> cfg.get_string("section/stringvar")
'value'
>>> cfg.set_int("section/intvar", 14)
>>> cfg.get_int("section/intvar")
14
>>> cfg.set_float("section/floatvar", 3.141592)
>>> cfg.get_float("section/floatvar") == 3.141592
1
>>> cfg.set_bool("section/boolvar", 4)
>>> cfg.get_bool("section/boolvar")
1
>>> cfg.set_bool("section/boolvar", 0)
>>> cfg.get_bool("section/boolvar")
0
>>> cfg.set_list("section/listv", [1, 2, 3])
>>> cfg.get_list("section/listv")
[1, 2, 3]
>>> c = ConfigUtils("section")
>>> c.get_string("section/stringvar")
'value'
>>> c.get_int("section/intvar")
14
>>> c.get_bool("section/boolvar")
0
>>> c.get_float("section/floatvar") == 3.141592
1
>>> cfg.initialise(None, None, "~/.solfege-cfg-testing")
>>> c.get_string("ss/a")
''
>>> c.get_string("ss/a=hei")
'hei'
>>> c.get_int("ss/a=3")
3
>>> c.get_list("ss/a")
[]
>>> c.get_list("ss/a=[1, 2, 3]")
[1, 2, 3]
>>> comment_re.match("# basd") != None
True
>>> section_re.match("#[section]") == None
True
>>> section_re.match(" [section]") == None
True
>>> section_re.match("[section]") != None
True
>>> value_re.match("key=value") != None
True
>>> value_re.match("#key=value") == None
True
>>> value_re.match(" key=value") == None
True
"""

import codecs
import logging
import os
import re

from solfege import filesystem

# match both "section-name" and "user:dir/module"
section_re = re.compile("^\[([\w\:\/-_]*?)\]")
value_re = re.compile(  "^([\w-]*?)=(.*)")
comment_re = re.compile("#.*")

_blocked_watches = {}
_watches = {}
_watch_counter = {}
_user_filename = None
_app_defaults_filename = None
_system_filename = None
data = {}

def split(key):
    v = key.rpartition(u"/")
    return v[0], v[2]

def parse_file_into_dict(dictionary, filename):
    f = codecs.open(filename, "rU", "utf-8")
    section = None
    for lineno, line in enumerate(f):
        line = line.strip()
        section_m = section_re.match(line)
        value_m = value_re.match(line)
        comment_m = comment_re.match(line)
        if comment_m:
            pass
        elif section_m:
            section = section_m.groups()[0]
            if section not in dictionary:
                dictionary[section] = {}
        elif value_m:
            assert section
            dictionary[section][value_m.groups()[0]] = value_m.groups()[1]
        elif not line.strip():
            pass
        else:
            raise CfgParseException(filename, lineno)
    f.close()
    return dictionary


def sync():
    dump(data, _user_filename)

def _maybe_create_key(key):
    section, k = split(key)
    if section not in data:
        data[section] = {}

def iterate_sections():
    for n in data.keys():
        yield n
########################
## set_XXXX functions ##
########################

def set_string(key, val):
    _maybe_create_key(key)
    section, k = split(key)
    if not isinstance(val, unicode):
        val = val.decode("utf-8")
    oldval = get_string(key)
    data[section][k] = val
    if key in _watches and (oldval != get_string(key)):
        if key in _blocked_watches and _blocked_watches[key] > 0:
            return
        for cb in _watches[key].values():
            cb(key)

def set_int(key, val):
    assert isinstance(val, int)
    _maybe_create_key(key)
    section, k = split(key)
    oldval = get_string(key)
    data[section][k] = str(val)
    if key in _watches and (oldval != get_string(key)):
        if key in _blocked_watches and _blocked_watches[key] > 0:
            return
        for cb in _watches[key].values():
            cb(key)

def set_float(key, val):
    assert isinstance(val, (float, int))
    _maybe_create_key(key)
    section, k = split(key)
    oldval = get_string(key)
    data[section][k] = str(val)
    if key in _watches and (oldval != get_string(key)):
        if key in  _blocked_watches and _blocked_watches[key] > 0:
            return
        for cb in _watches[key].values():
            cb(key)

def set_bool(key, val):
    _maybe_create_key(key)
    if val:
        set_string(key, "true")
    else:
        set_string(key, "false")

def set_list(key, val):
    set_string(key, str(val))

########################
## get_XXX functions ##
########################

def get_string(key):
    if len(key.split("=")) == 2:
        key, default = key.split("=")
    else:
        default = ""
    section, k = split(key)
    try:
        return data[section][k]
    except KeyError:
        return default

def get_int(key):
    if len(key.split("=")) == 2:
        key, default = key.split("=")
    else:
        default = 0
    section, k = split(key)
    try:
        # UGH win32 fix
        if not data[section][k]:
            return 0
        return int(float(data[section][k]))
    except KeyError:
        return int(default)

def get_float(key):
    if len(key.split("=")) == 2:
        key, default = key.split("=")
    else:
        default = 0
    section, k = split(key)
    try:
        return float(data[section][k])
    except KeyError:
        return float(default)

def get_list(key):
    if len(key.split("=")) == 2:
        key, default = key.split("=")
    else:
        default = []
    section, k = split(key)
    try:
        return eval(data[section][k])
    except KeyError:
        return default

def get_bool(key):
    if get_string(key) == 'true':
        return 1
    elif get_string(key) == 'false':
        return 0
    else:
        return 0

#####################################
def del_key(key):
    section, k = split(key)
    #FIXME watches
    if section not in data:
        return
    if k not in data[section]:
        return
    del data[section][k]
    if not data[section]:
        del data[section]

def del_section(section):
    #FIXME watches
    if section not in data:
        # Trying to delete a deleted section
        return
    del data[section]

######################################
## reading and writing the database ##
######################################

def dump(datadict, fn):
    f = codecs.open(fn, 'w', 'utf-8')
    for section in datadict:
        f.write("[%s]\n" % section)
        for name in datadict[section]:
            f.write("%s=%s\n" % (name, datadict[section][name]))
        f.write("\n")
    f.close()

def drop_user_config():
    """
    Reread the config data, but only read the systems defaults from
    /usr/share/solfege/default.config and /etc/solfege, not
    $HOME/.solfegerc
    """
    global data, _watches, _watch_counter, _blocked_watches
    data = {}
    _watches = {}
    _watch_counter = 0
    _blocked_watches = {}
    data = parse_file_into_dict(data, _app_defaults_filename)
    if _system_filename and os.path.isfile(_system_filename):
        data = parse_file_into_dict(data, _system_filename)

def reread_data():
    global data, _watches, _watch_counter, _blocked_watches
    _watches = {}
    _watch_counter = 0
    _blocked_watches = {}
    if _app_defaults_filename:
        data = parse_file_into_dict({}, _app_defaults_filename)
    if _system_filename:
        data = parse_file_into_dict(data, _system_filename)
    if _user_filename and os.path.isfile(_user_filename):
        data = parse_file_into_dict(data, _user_filename)

class CfgParseException(Exception):
    def __init__(self, filename, lineno):
        Exception.__init__(self)
        self.m_filename = filename
        self.m_lineno = lineno
    def __str__(self):
        return "CfgParseException: Failed to parse line %(lineno)i of the file '%(filename)s'" % {'lineno': self.m_lineno, 'filename': self.m_filename}

def initialise(app_defaults_filename, system_filename, user_filename):
    """
    app_defaults_filename: file must exist!
    system_filename: sys admin can override app_defaults_filename
    user_filename: the state of the app is stored here, also user config.
    """
    global data, _watches, _watch_counter, _blocked_watches
    global _app_defaults_filename, _system_filename, _user_filename
    _watches = {}
    _watch_counter = 0
    _blocked_watches = {}
    _app_defaults_filename = app_defaults_filename
    _system_filename = system_filename
    _user_filename = user_filename = filesystem.expanduser(user_filename)
    if app_defaults_filename:
        try:
            data = parse_file_into_dict({}, app_defaults_filename)
        except CfgParseException:
            print "-" * 60
            print "The program failed to parse default.config. This means that"
            print "you have modified the file, because it was ok then Solfege"
            print "was released. Fix the file yourself, or reinstall Solfege."
            print "-" * 60
            raise
    else:
        data = {}
    if system_filename and os.path.isfile(system_filename):
        data = parse_file_into_dict(data, system_filename)
    if os.path.isfile(user_filename):
        data = parse_file_into_dict(data, user_filename)


class ConfigUtils(object):
    def __init__(self, exname):
        self.m_exname = exname
    def block_watch(self, name):
        """
        Stop functions watching a name being called. You have to call the
        same number of unblock_watch calls as block_calls to remove a blocking.
        """
        name = self._expand_name(name)
        if name not in _blocked_watches:
            _blocked_watches[name] = 0
        _blocked_watches[name] += 1
    def unblock_watch(self, name):
        name = self._expand_name(name)
        assert name in _blocked_watches
        assert _blocked_watches[name] > 0
        _blocked_watches[name] -= 1
    def add_watch(self, name, callback):
        global _watch_counter
        name = self._expand_name(name)
        if name not in _watches:
            _watches[name] = {}
        _watches[name][_watch_counter] = callback
        _watch_counter += 1
        return _watch_counter - 1
    def remove_watch(self, name, watch_id):
        name = self._expand_name(name)
        if name in _watches:
            if watch_id in _watches[name]:
                del _watches[name][watch_id]
                if _watches[name] == {}:
                    del _watches[name]
            else:
                logging.warning("cfg.remove_watch: id don't exist: %s", watch_id)
        else:
            logging.warning("cfg.remove_watch: name is not watched: %s", name)
    def _expand_name(self, name):
        if name.count("/") == 0:
            return "%s/%s" % (self.m_exname, name)
        return name
    ######
    # set
    ######
    def set_string(self, name, val):
        set_string(self._expand_name(name), val)
    def set_int(self, name, val):
        set_int(self._expand_name(name), val)
    def set_float(self, name, val):
        set_float(self._expand_name(name), val)
    def set_bool(self, name, val):
        set_bool(self._expand_name(name), val)
    def set_list(self, name, val):
        set_list(self._expand_name(name), val)
    ######
    # get
    ######
    def _get(self, func, name, default=""):
        return func(self._expand_name(name)+default)
    def get_string(self, name):
        r = self._get(get_string, name)
        if r is None:
            return ""
        else:
            return r
    def get_int(self, name):
        return self._get(get_int, name)
    def get_int_with_default(self, name, default):
        assert type(default) is type(0)
        return self.get_int(name+"=%i" % default)
    def get_float(self, name):
        return self._get(get_float, name)
    def get_bool(self, name):
        return self._get(get_bool, name)
    def get_list(self, name):
        try:
            if '=' in name:
                return eval(self._get(get_string, name))
            return eval(self._get(get_string, name, "=[]"))
        except SyntaxError:
            return []


