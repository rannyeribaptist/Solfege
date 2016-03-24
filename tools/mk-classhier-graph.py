#!/usr/bin/python

import re
import sys
import os
import textwrap

if len(sys.argv) == 1 or sys.argv[1] == '-h':
    print "\nUsage:"
    print "\t./tools/classhier.py file1.py file2.py ...\n"
    print "\n\t".join(textwrap.wrap("\tGenerate a nice graph of the class hierarchy in the files supplied as arguments."))
    print
    sys.exit(0)

class ClassInfo(object):
    def __init__(self, module, name):
        self.module = module
        self.name = name

class ClassDb(object):
    def __init__(self):
        self.db = {}
    def add_classdef(self, mod, name):
        """
        mod - the module the class is defined in
        name - the name of the class
        """
        if mod not in self.db:
            self.db[mod] = {}
        self.db[mod][name] = []
    def add_class_parent(self, mod, name, parent):
        """
        mod - the module the class is defined in
        name - the name of the class
        parent - a (mod, name) tuple of one parent
        """
        self.db[mod][name].append(parent)
    def has_class(self, mod, name):
        return mod in self.db and name in self.db[mod]
    def write(self, filename, filetype):
        def fmt(mod, cls):
            return cls
            return r'"%s %s"' % (mod.replace(".", "_"), cls)
        f = open(filename, 'w')
        if filetype == 'fdp':
            joinstr = " -- "
            print >> f, "graph G {"
            print >> f, "overlap=false;"
            print >> f, "splines=true;"
        elif filetype == 'dot':
            print >> f, "digraph G {"
            #print >> f, 'size = "8,10";'
            print >> f, 'ratio = fill;'
            print >> f, 'margin = 1;'
            print >> f, 'center = 1;'
            print >> f, 'bgcolor=white;'
            print >> f, 'edge [color=blue,arrowhead=normal,arrowsize=1.5];'
            print >> f, "rankdir=LR;"

            joinstr = " -> "
        for mod in self.db:
            for cl in self.db[mod]:
                this_mod = mod.replace(".", "_")
                #print >> f, fmt(mod, cl)
                for parent in self.db[mod][cl]:
                    p = r'"%s\n%s"' % (this_mod, parent)
                    print >> f, r'%s%s%s;' % (fmt(mod, cl), joinstr, fmt(*parent))
        print >> f, "}"
        f.close()

class_re = re.compile("""
   (?P<all>class\s*
    (?P<classname>[a-zA-Z]\w*)
    (\(
    (?P<parentlist>
    (.*?)  # The first parent
    (,(.*?))* # unknown number of more parents
    )\))?:)""", re.VERBOSE)#(\(*?\))")

db = ClassDb()

def mod_split(modulename):
    """
    Split the complete modulename into (package, modulename) tuple
    """
    v = modulename.split(".")
    return ".".join(modulename.split(".")[:-1]), v[-1]

def mod_to_filename(mod):
    " solfege.abstract => solfege/abstract.py"
    return mod.replace(".", "/") + ".py"
def do_file(fn):
    modulename = fn[:-3].replace("/", ".")
    package = mod_split(modulename)[0]
    s = open(fn).read()
    for m in class_re.finditer(s):
        if m:
            parents = m.group('parentlist')
            if parents:
                parents = [p.strip() for p in parents.split(",")]
            else:
                parents = []
            db.add_classdef(modulename, m.group('classname'))
            for p in parents:
                # Continue if this is not a module in this project.
                if p in ('unicode', 'list', 'dict', 'object'):
                    continue
                if p.startswith("Gtk."):
                    continue
                mname = os.path.join(mod_split(modulename)[0], mod_split(p)[0])+".py"
                if mod_split(p)[0] and not os.path.exists(mname):
                    print "DROPPING", p
                    continue
                if "." in p:
                    mm = ".".join((package, mod_split(p)[0]))
                    nn = mod_split(p)[1]
                    db.add_class_parent(modulename, m.group('classname'),
                        (mm, nn))
                else:
                    db.add_class_parent(modulename, m.group('classname'),
                        (modulename, p))

for fn in sys.argv[1:]:
    do_file(fn)

for mod, d in db.db.items():
    for deps in d.values():
        for dep in deps:
            if dep[0] not in db.db.keys():
                do_file(mod_to_filename(dep[0]))


db.write("classhier.dot", 'dot')
os.system("dot -T png -o classhier.png classhier.dot")
print "created classhier.png"
#os.system("fdp -T png -o classhier.png classhier.dot")
