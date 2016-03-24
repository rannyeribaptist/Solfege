# GNU Solfege - free ear training software

# Copied from http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/473846
# Copyright Christopher Arndt under the Python License.

from __future__ import absolute_import

import _winreg
import re
import os
SHELL_FOLDERS = r'Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders'
HKCU = _winreg.HKEY_CURRENT_USER

# helper functions
def _substenv(m):
    return os.environ.get(m.group(1), m.group(0))

_env_rx = None
def expandvars(s):
    """Expand environment variables of form %var%.

    Unknown variables are left unchanged.
    """

    global _env_rx

    if '%' not in s:
        return s
    if _env_rx is None:
        _env_rx = re.compile(r'%([^|<>=^%]+)%')
    return _env_rx.sub(_substenv, s)

def _get_reg_value(key, subkey, name):
    """Return registry value specified by key, subkey, and name.

    Environment variables in values of type REG_EXPAND_SZ are expanded
    if possible.
    """

    key = _winreg.OpenKey(key, subkey)
    try:
        ret = _winreg.QueryValueEx(key, name)
    except WindowsError:
        return None
    else:
        key.Close()
        if ret[1] == _winreg.REG_EXPAND_SZ:
            return expandvars(ret[0])
        else:
            return ret[0]


def _get_reg_user_value(key, name):
    """Return a windows registry value from the CURRENT_USER branch."""

    return _get_reg_value(HKCU, key, name)

def get_appdata():
    """Return path of directory where apps should store user specific data."""

    return _get_reg_user_value(SHELL_FOLDERS, 'AppData')


