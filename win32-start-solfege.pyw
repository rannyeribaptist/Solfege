import os
import sys
from subprocess import Popen

prefix =  os.path.split(os.path.dirname(os.path.abspath(sys.argv[0])))[0]

if len(sys.argv) > 1 and sys.argv[1] == 'srcdir':
    python = os.path.join(prefix, "solfege", "win32", "python", "python.exe")
    cmd = [python, "solfege.py"] + sys.argv[2:]
else:
    sys.path.append("../share/solfege")
    if '--debug' in sys.argv:
        p = "python.exe"
    else:
        p = "pythonw.exe"
    python = os.path.join(prefix, "python", p)
    cmd = [python, "solfege"] + sys.argv[1:]

from solfege import winlang

lang = winlang.win32_get_langenviron()
if lang and (lang != 'system default'):
    os.environ['LANGUAGE'] = lang

Popen(cmd + sys.argv[1:])
