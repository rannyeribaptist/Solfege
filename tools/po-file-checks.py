#!/usr/bin/python
# coding: iso-8859-1

import re
import sys
import optparse
import unittest
import glob
import os

ok_different_mapping_key = (
  "notenameformat|%(notename)s%(oct)s",
)
class Entry(object):
    # translated status: UNTRANS, FUZZY, TRANS
    # obsolete: True / False
    def __init__(self, s):
        s = s.strip("\n")
        msgid_re = re.compile('(msgid|#~ msgid) "(?P<id>.*?)"\s*$')
        msgstr_re = re.compile('(msgstr|#\~ msgstr) "(?P<str>.*?)"\s*$')
        data = {'comment': [], 'msgid': [], 'msgstr': []}
        mode = None
        self.m_status = 'translated'
        self.m_obsolete = False
        for line in s.split("\n"):
            msgid_m = msgid_re.match(line)
            msgstr_m = msgstr_re.match(line)
            if line.startswith("#:") or line.startswith("#.") or line.startswith("#, python-format") or line.startswith("#, no-python-format") or line.startswith("# ") or line == '#':
                assert mode in ('comment', None)
                mode = 'comment'
                data[mode].append(line)
            elif line.startswith("#, fuzzy"):
                assert mode in ('comment', None)
                mode = 'comment'
                self.m_status = 'fuzzy'
                data[mode].append(line)
            elif msgid_m:
                assert mode in ('comment', None)
                mode = 'msgid'
                if line.startswith("#~"):
                    self.m_obsolete = True
                if msgid_m.group('id'):
                    data[mode].append(msgid_m.group('id'))
            elif msgstr_m:
                assert mode == 'msgid'
                mode = 'msgstr'
                if msgstr_m.group('str'):
                    data[mode].append(msgstr_m.group('str'))
            else:
                # We are in a mlineline msgid or msgstr
                assert mode in ('msgid', 'msgstr'), mode
                data[mode].append(line.strip('"'))
        self.m_msgid = data['msgid']
        self.m_msgstr = data['msgstr']
        self.m_comment = data['comment']
        if not "".join(self.m_msgstr):#self.m_msgstr == ['']:
            self.m_status = 'untranslated'
        if not self.m_msgid:
            self.m_status = 'heading'
        for idx in range(len(self.m_msgid)):
            if self.m_msgid[idx] == '':
                self.m_msgid[idx] = '\n'
        self.m_msgid_string = "".join(self.m_msgid)
        for idx in range(len(self.m_msgstr)):
            if self.m_msgstr[idx] == '':
                self.m_msgstr[idx] = '\n'
        self.m_msgstr_string = "".join(self.m_msgstr)
        #    translated = 'heading'
        #if not "\n".join(retval['msgstr']):
        #    translated = 'untranslated'
        #return translated, obsolete, retval
    def is_header(self):
        return not self.m_msgid
    def get_status(self):
        """
        'translated'
        'untranslated'
        'fuzzy'
        'obsolete'
        """
        if self.m_obsolete:
            return 'obsolete'
        return self.m_status
    def get_msgid(self):
        return self.m_msgid_string
        return " ".join(self.m_msgid)
    def get_msgstr(self):
        return self.m_msgstr_string
        return " ".join(self.m_msgstr)

class TestEntry(unittest.TestCase):
    def test_escaped_qoute(self):
        s = """
#: solfege/dictation.py:197
#, python-format
msgid "The '%s'."
msgstr "Il file \"%s\"."

"""
        e = Entry(s)
        self.assertEqual(e.get_msgstr(), "Il file \"%s\".")

def string_to_entry_list(s):
    """
    This function assumes that the file is well formed. There should
    be one empty line between each message."
    """
    v = []
    for x in s.split("\n\n"):
        if not x:
            print "NOTHIN"
            continue
        e = Entry(x)
        v.append(e)
    return v

def parse_string(s):
    """
    This function will return a dict with some statistics about the entries.
    """
    v = string_to_entry_list(s)
    dicts = {'translated': 0, 'fuzzy': 0, 'obsolete': 0, 'untranslated': 0, 'heading': 0}
    for e in v:
        dicts[e.get_status()] += 1
    del dicts['heading']
    return dicts

def parse_file(filename):
    return parse_string(file(filename, 'r').read())


def find_string_formatting(s):
    """
    Make a list with all string formatting operators in the string except
    named operators, like %(name)s
    """
    s = re.sub("%\s*%", "", s)
    #r = re.compile("\%(\(\w+\))?(\.?\d+)?\w")
    r = re.compile("\%(\.?\d+)?[^\s\(]")
    start = 0
    m = r.search(s[start:])
    ret = []
    while m:
        ret.append(m.group())
        start = start + m.end()
        m = r.search(s[start:])
    return ret

def find_string_formatting_mapping_keys(s):
    s = re.sub("%\s*%", "", s)
    r = re.compile("\%(\((?P<name>\w*)\))?(?P<notname>(\.?\d+)?[^\s\(])")
    start = 0
    m = r.search(s[start:])
    ret = []
    while m:
        ret.append((m.group('name'), m.group('notname')))
        start = start + m.end()
        m = r.search(s[start:])
    return ret

class TestFindStringFormatting(unittest.TestCase):
    def test_simplest(self):
        for n in ("%s", "%f", "%.2d", "%03d"):
            self.assertEqual(find_string_formatting(n), [n])
    def test_complex(self):
        self.assertEqual(find_string_formatting("abc %.1f%%\n def %.1f%%"), ['%.1f', '%.1f'])
    def test_common_po_bugs(self):
        self.assertNotEqual(find_string_formatting("%.1f%.\n"), ['%.1f'])
    def test_double_percent(self):
        self.assertEqual(find_string_formatting("%s %% %f"), ['%s', '%f'])
        self.assertEqual(find_string_formatting("%s % % %f"), ['%s', '%f'])
        self.assertEqual(find_string_formatting("%s %\t\t% %f"), ['%s', '%f'])
    def test_ignore(self):
        self.assertEqual(find_string_formatting("%(name)s"), [])
    def test_xxx(self):
        msgid = """
Test completed!
Your score was %.1f%%.
The test requirement was %.1f%%.
"""
        msgstr = """
Úspěšný test!
Vaše skóre bylo %.1f%%.
Požadované skóre bylo%.1f% %.
"""
        self.assertEqual(find_string_formatting(msgid),
                         find_string_formatting(msgstr))
    def test_mapping(self):
        v1 = find_string_formatting_mapping_keys("%(name)s %(bla).1f X")
        v2 = find_string_formatting_mapping_keys("%(bla).1f X X %(name)s ")
        v1.sort()
        v2.sort()
        self.assertEqual(v1, v2)


def check_file(filename):
    v = string_to_entry_list(file(filename, 'r').read())
    file_ok = True
    for entry in v:
        if entry.is_header():
            continue
        a = find_string_formatting(entry.get_msgid())
        b = find_string_formatting(entry.get_msgstr())
        if (a != b) and entry.get_msgstr() and \
                (entry.get_status() not in ('obsolete', 'fuzzy')):
            file_ok = False
            print "%s:" % filename
            print 'msgid: "%s"' % entry.get_msgid()
            print 'msgstr: "%s"' % entry.get_msgstr()
            print "%s != %s" % (a, b)
            print "Entry status:", entry.get_status()
            print
        # Check mapping key
        v1 = find_string_formatting_mapping_keys(entry.get_msgid())
        v2 = find_string_formatting_mapping_keys(entry.get_msgstr())
        all_1 = v1 and bool([x for x in v1 if x[0] is not None])
        all_2 = v2 and bool([x for x in v2 if x[0] is not None])
        v1x = list(v1)
        v2x = list(v2)
        v1x.sort()
        v2x.sort()
        format_ok = (v1x == v2x and all_1 and all_2)
        if (v1 != v2) and entry.get_msgstr() \
                and (entry.get_status() not in ('obsolete', 'fuzzy')) \
                and not [s for s in entry.m_comment if 'no-python-format' in s] \
                and (entry.get_msgid() not in ok_different_mapping_key) \
                and (not format_ok):
            file_ok = False
            print "Mapping key not equal in the file", filename
            print "\tmsgid: \"" + entry.get_msgid() + "\""
            print "\tmsgstr: \"" + entry.get_msgstr() + "\""
        # Check for notename| strings
        if entry.get_msgid().startswith("notename|"):
            if "|" in entry.get_msgstr():
                file_ok = False
                print "%s:" % filename
                print "'|' in translated notename entry:"
                print 'msgid: "%s"' % entry.get_msgid()
    return file_ok


if len(sys.argv) > 1 and sys.argv[1] == '-t':
    del sys.argv[1]
    unittest.main()
    sys.exit()
if len(sys.argv) > 1 and sys.argv[1] == '-c':
    s = file('po/tr.po', 'r').read()
    for x in s.split("\n\n"):
        print "\n", x
    sys.exit()


retval = 0
for filename in glob.glob(os.path.join("po", "*.po")):
    if not check_file(filename):
        retval = -1
sys.exit(retval)
