#!/usr/bin/python

import pprint
import sys
import os.path
import re
import optparse
import glob
import subprocess

import depgraph2dot

solfege_modules = ('solfege')
# The keys of this dict is the module names.
# The values are the module names, for example solfege.application.SolfegeApp
deps = {}

class ModuleInfo(object):
    def __init__(self, fn):
        assert os.path.isfile(fn)
        head, tail = os.path.split(fn)
        m, e = os.path.splitext(tail)
        assert os.path.isdir(head)
        assert e == '.py'
        if m == '__init__':
            self.m_modulename = head.replace("/", ".")
        else:
            self.m_modulename = ".".join(os.path.splitext(fn)[0].split("/"))
        assert "/" not in self.m_modulename
        self.m_location = head
        self.m_filename = fn
        self.m_usage = set()

# import os, sys, solfege.mpd
re2 = re.compile("^(?P<imp>import)\s+(?P<modulelist>((\w[\.\w]+,\s*)*)\w[\.\w]+)$")
# import solfege.ElementTree as et
re3 = re.compile("^(?P<imp>import)\s+(?P<module>\w[\.\w]+)\s+as\s+(?P<asmodule>\w+)")
re5 = re.compile("^from\s+(?P<module>\w[\.\w]+)\s+import\s+(?P<imodule>\w[\.\w]+)\s+as\s+(?P<asmodule>\w[\.\w]+)$")
re6 = re.compile("^from\s+(?P<module>solfege(\.\w+)*)\s+import\s+((?P<modulelist>((\w[\.\w]+,\s*)*)\w[\.\w]+)|\*)$")
re_comma = re.compile(",\s*")
def test_re():
    m = re2.match("import app")
    assert m.group('imp') == 'import'
    assert m.group('modulelist') == 'app'
    m = re2.match("import app, abstract")
    assert m.group('modulelist') == "app, abstract"
    m = re2.match("import app, abstract \\")
    assert m is None
    m = re2.match("import mpd.interval")
    assert m.group('modulelist') == "mpd.interval"
    m = re2.match("import app, mpd.interval")
    assert m.group('modulelist') == "app, mpd.interval"
    m = re2.match("import app, .interval")
    assert m is None
    m = re3.match("import abc as DE")
    assert m.group('module') == 'abc'
    assert m.group('asmodule') == 'DE'
    m = re3.match("import solfege.mpd.musicalpitch as mi")
    assert m.group('module') == 'solfege.mpd.musicalpitch'
    assert m.group('asmodule') == 'mi'
    m = re5.match("from os.path import isfile as asfile")
    assert m.group('module') == 'os.path'
    assert m.group('imodule') == 'isfile'
    assert m.group('asmodule') == 'asfile'
    m = re6.match("from solfege import i18n, abstract")
    assert m.group('modulelist') == 'i18n, abstract'
    m = re6.match("from solfege.mpd import musicalpitch")
    assert m.group('module') == 'solfege.mpd'
    assert m.group('modulelist') == 'musicalpitch'
    m = re6.match("from solfege.mpd.rat import Rat")
    assert m.group('module') == 'solfege.mpd.rat'
    assert m.group('modulelist') == 'Rat'

def name_of_imported(info, importname):
    """
    """
    if "." not in importname:
        return "%s.%s" % (info.m_location, importname)
    else:#if importname.count(".") == 1:
        package, modulename = importname.split(".")
        assert package in solfege_modules
        return importname


def test_name_of_imported():
    info = ModuleInfo("solfege/application.py")
    assert name_of_imported(info, "abstract") == "solfege.abstract"

def usage_of_module(info):
    f = open(info.m_filename, 'rU')
    for line in f.readlines():
        line = line.strip("\n")
        if line.startswith('from __future__'):
            continue
        elif line.startswith('import '):
            m = re2.match(line)
            # re2 is simples import statement. Example:"
            # import os, re, solfege.mpd.musicalpitch
            if m:
                for module in re_comma.split(m.group('modulelist')):
                    module = module.strip()
                    if module.startswith("solfege."):
                        deps[info.m_modulename].m_usage.add(module)
                    continue
                continue
            m = re3.match(line)
            if m:
                if m.group('module').startswith("solfege."):
                    deps[info.m_modulename].m_usage.add(m.group('module'))
                continue
            raise Exception("import statement failed.")
        elif line.startswith('from '):
            m = re6.match(line)
            if m:
                if line.endswith("import *"):
                    deps[info.m_modulename].m_usage.add(m.group('module'))
                    continue
                for mod in re_comma.split(m.group('modulelist')):
                    module_name = "%s.%s" % (m.group('module'), mod.strip())
                    mfn = "%s.py" % module_name.replace(".", "/")
                    package_init = "%s/__init__.py" % module_name.replace(".", "/")
                    if os.path.isfile(mfn):
                        deps[info.m_modulename].m_usage.add(module_name)
                    elif os.path.isfile(package_init):
                        deps[info.m_modulename].m_usage.add("%s.%s" % (m.group('module'), mod))
                    else:
                        deps[info.m_modulename].m_usage.add(m.group('module'))
                continue
            m = re5.match(line)
            if m:
                if m.group('module').startswith("solfege."):
                    raise Exception("Not implemented yet")
                    deps[info.m_modulename].m_usage.add(name_of_imported(info, m.group('module')))
                continue
            print "line::::", line

def do_file(fn):
    global deps
    info = ModuleInfo(fn)
    assert info.m_modulename not in deps
    deps[info.m_modulename] = info
    usage_of_module(info)


opt_parser = optparse.OptionParser(description="""
We use this to create a graph showing how the modules in Solfege
import each other. Typical usage is:
./tools/create_depgraph.py -a | ./tools/depgraph2dot.py | dot -T png -o classhier.png
""")
opt_parser.add_option('-t', action='store_true', dest='run_testsuite',
                      help="Run small test suite and exit.")
opt_parser.add_option('-o', dest='outfile',
                      help="Save to OUTFILE instead of STDOUT")
opt_parser.add_option('-a', action='store_true', dest='all_files',
                      help="Scan all source files")
opt_parser.add_option('-s', action='store_true', dest='simplify')
opt_parser.add_option('-g', action='store_true', dest='do_all',
            help="Run all scripts to create the png image")

options, args = opt_parser.parse_args()
if options.run_testsuite:
    test_re()
    test_name_of_imported()
    sys.exit()

if options.all_files:
    v = glob.glob("solfege/*.py") + glob.glob("solfege/soundcard/*.py") + glob.glob("solfege/mpd/*.py") + glob.glob("solfege/exercises/*.py")
else:
    v = []
for fn in args + v:
    do_file(fn)


def replace_modules(to_module, remove_modules):
    """
    to_module is the name of the a module
    remove_modules is a list of names
    """
    for k in deps.keys():
        for ex in remove_modules:
            if k == ex:
                for dep in deps[k].m_usage:
                    if dep not in deps[to_module].m_usage:
                        deps[to_module].m_usage.add(dep)
    for ex in remove_modules:
        del deps[ex]
    for k in deps.keys():
        for ex in remove_modules:
            if ex in deps[k].m_usage:
                deps[k].m_usage.remove(ex)
                if to_module not in deps[k].m_usage:
                    deps[k].m_usage.add(to_module)


def remove_module(modulename):
    for k in deps:
        if modulename in deps[k].m_usage:
            deps[k].m_usage.remove(modulename)
    if modulename in deps:
        del deps[modulename]


if options.simplify:
    # This loop will add all depsendencies of all exercies to
    # 'solfege.exercises'
    for k, info in deps.items():
        if k.startswith("solfege.exercises"):
            if k == 'solfege.exercises.__init__':
                continue
            for d in deps[k].m_usage:
                deps['solfege.exercises'].m_usage.add(d)
    # Delete all exercise modules, but not 'solfege.exercises'
    for key in [k for k in deps if k.startswith('solfege.exercises.')]:
        del deps[key]
    remove_module('solfege.gu')
    remove_module('solfege.cfg')

d = {'depgraph': {}, 'types': {}}
for info in deps.values():
    nd = {}
    for x in info.m_usage:
        nd[x] = 1
    d['depgraph'][info.m_modulename] = nd
    d['types'][info.m_modulename] = 1

if options.outfile:
    f = open(options.outfile, "w")
    pprint.pprint(d, f)
    f.close()

if options.do_all:
    dot = depgraph2dot.DD()
    dot._data = d
    dot.main([])
    subprocess.call(('dot', '-T', 'png', '-o', 'classhier.png', 'ut.dots'))
    subprocess.call(('eog', 'classhier.png'))
    #os.remove('ut.dots')

