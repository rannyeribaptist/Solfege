#!/usr/bin/python
# vim: set fileencoding=utf-8:

import optparse
import os
import shutil
import re
import subprocess
import sys

op = optparse.OptionParser(usage="%prog [options] VERSION")
op.add_option("--not-translated",
    action='store_false', dest='translated_branch', default=True,
    help="Don't check for translation updates. This is a devel branch "
         "that is not translated.")
op.add_option("--docbooktest", action='store_true', dest='docbooktest',
    default=False)
op.add_option("--no-test", action='store_false', dest='run_make_test',
    help="Don't run \"make test\"",
    default=True)

options, args = op.parse_args()

def parse_build_log():
    f = open("build.log", "r")
    curlang = None
    docbook_langstart = re.compile("\(cd help\/(\w+)\/")
    stack = []
    for line in f.readlines():
        line = line.strip()
        m = docbook_langstart.match(line)
        if m:
            curlang = m.groups()[0]
        if line.startswith("Error") or line.startswith("ERROR"):
            if not stack or stack[0] != 'docbook':
                print "Errors, probably from docbook:"
                print "=============================="
                stack = ['docbook']
            if len(stack) < 2 or (len(stack) == 2 and stack[1]!= curlang):
                if len(stack) == 2 and stack[1] != curlang:
                    stack[1] = curlang
                else:
                    stack.append(curlang)
                print "Language:", curlang
            print "\t", line
    f.close()

version_number = args[0]
distdir = "solfege-%s" % version_number
bindistdir = "solfege-bin-%s" % version_number

def get_last_revision_id():
    p = subprocess.Popen(["git", "rev-parse", "HEAD"],
        cwd=distdir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT)
    while 1:
        p.poll()
        if p.returncode != None:
            break
        return p.stdout.readline().strip()
    p.wait()
    return retval

class Logger(object):
    def __init__(self, filename):
        self.logfile = open(filename, 'w')
        self.close = self.logfile.close
    def call(self, *args, **kwargs):
        kwargs['stdout'] = subprocess.PIPE
        kwargs['stderr'] = subprocess.STDOUT
        p = subprocess.Popen(*args, **kwargs)
        while 1:
            p.poll()
            if p.returncode != None:
                break
            while True:
                s = p.stdout.readline()
                print s.strip()
                self.logfile.write(s)
                if not s:
                    break
        p.wait()
        if p.returncode != 0:
            print "p.returncode =", p.returncode
            sys.exit()
        return p.returncode

def update_configure_ac(new_revid, version):
    f = open(os.path.join(distdir, "configure.ac"), "r")
    s = f.read()
    f.close()
    m = re.search("REVISION_ID=\"(.*?)\"", s)
    s = s[:m.start()+len("REVISION_ID=\"")] + new_revid + s[m.end()-1:]
    m = re.search("MAJOR_VERSION=.*?$", s, re.MULTILINE)
    s = s[:m.start()+len("MAJOR_VERSION=")] + version.split(".")[0] + s[m.end():]
    m = re.search("MINOR_VERSION=.*?$", s, re.MULTILINE)
    s = s[:m.start()+len("MINOR_VERSION=")] + version.split(".")[1] + s[m.end():]
    m = re.search("PATCH_LEVEL=.*?$", s, re.MULTILINE)
    s = s[:m.start()+len("PATCH_LEVEL=")] + ".".join(version.split(".")[2:]) + s[m.end():]

    m = re.search("AC_INIT\(\[GNU Solfege\],\[.*?\]", s, re.MULTILINE)
    s = s[:m.start()+len("AC_INIT([GNU Solfege],[")] + version + s[m.end()-1:]

    f = open(os.path.join(distdir, "configure.ac"), "w")
    f.write(s)
    f.close()


if options.docbooktest:
    parse_build_log()
    sys.exit()

bl = Logger("build.log")
for b in distdir, bindistdir:
    if os.path.exists(b):
        s = raw_input("«%s» exists. Delete (Y/N)? " % b)
        if s in ('y', 'Y'):
            shutil.rmtree(b)
        else:
            sys.exit(1)
print "git clone . ", distdir
bl.call(["git", "clone", ".", distdir])

if options.translated_branch:
    bl.call(["make", "check-for-new-po-files"])
    bl.call(["make", "check-for-new-manual-po-files"])

update_configure_ac(get_last_revision_id(), version_number)
bl.call(["./autogen.sh"], cwd=distdir, env=os.environ)

shutil.rmtree(os.path.join(distdir, ".git"))

bl.call(["tar", "--gzip", "--create",
         "--file=%s.tar.gz" % distdir,
         distdir],
        env=os.environ)

os.rename(distdir, bindistdir)
bl.call(["./configure"], cwd=bindistdir, env=os.environ)

bl.call(["make", "update-manual"], cwd=bindistdir, env=os.environ)
bl.call(["make"], cwd=bindistdir, env=os.environ)


bl.call(["tar", "--gzip", "--create",
            "--file=%s.tar.gz" % bindistdir,
             bindistdir])

if options.run_make_test:
    bl.call(["make", "test"], cwd=bindistdir)
bl.call(["make", "dist"], cwd=bindistdir)
bl.close()
print "Remember to check that the translation of the user manual does"
print "not mess with the docbook format of the file."
