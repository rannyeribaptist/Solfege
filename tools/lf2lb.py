#!/usr/bin/env python

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

# unfinished script that create a lilypond-book document
# over all the lessonfiles.

import gi
pyGtk.require("2.0")

import sys, re, os, os.path
sys.path.append(".")

import solfege, solfege.dataparser, solfege.lessonfile

def tex_subst(s):
    return s.replace("&", "\&").replace("#", "\#")

def so2ly(s, musicformat):
    re_staff = re.compile("\\\\staff")
    re_addvoice = re.compile("\\\\addvoice")
    v = re_staff.split(s)
    v = filter(lambda i: i!="", v)
    v = map(lambda s, r=re_addvoice: r.split(s), v)
    retval = "\\score{\n  <"
    i = ''
    for s in v:
        i = i + 'i'
        retval = retval + "\n    \\context Staff=%s<" % i
        for vo in s:
            i = i + 'i'
            if musicformat == 'chord':
                m = "< %s >" % vo
            else:
                m = vo
            retval = retval + "\n      \\context Voice=%s\\notes{%s}" % (i, m)
        retval = retval + "\n    >"
    retval = retval + "\n  >\n}"
    return retval

def write_header(of, header, filename):
    of.write("\n\\subsection{%s}" % tex_subst(header.title))
    of.write("\n\\begin{itemize}")
    of.write("\n\\item filename: %s" % filename)
    of.write("\n\\item description: %s" % header.description)
    of.write("\n\\item content: %s" % header.content)
    of.write("\n\\item musicformat: %s" % header.musicformat)
    of.write("\n\\end{itemize}")

def write_questions(of, header, questions):
    for q in questions:
        of.write("""'%s':
\\begin[11pt, eps, singleline]{lilypond}
%s
\\end{lilypond}
,
""" % (tex_subst(q.get('name', '')), so2ly(q['music'], header.musicformat)))

predef = {'dictation': 'dictation',
                      'progression': 'progression',
                      'harmony': 'harmony',
                      'chord-voicing': 'chord-voicing',
                      'sing-chord': 'sing-chord',
                      'chord': 'chord',
                      'id-by-name': 'id-by-name',
                      'satb': 'satb',
                      'horiz': 'horiz',
                      'vertic': 'vertic',
                      'yes': 1,
                      'no': 0,
                      'tempo': (60, 4)}

def write_file(of, filename):
    parser = solfege.dataparser.Dataparser(predef, ('tempo',))
    parser.parse_file(filename)

    questions = filter(lambda e: e['blocktype'] == 'question', parser.m_blocks)
    header = solfege.lessonfile._Header(
          filter(lambda e: e['blocktype'] == 'header', parser.m_blocks)[0])

    write_header(of, header, filename)
    write_questions(of, header, questions)


of = open("lessonfiles.tex", "w")
of.write(r"""\documentclass[a4paper, 12pt]{article}
\begin{document}
""")

for filename in sys.argv[1:]:
    if os.path.isfile(filename) and not filename.endswith('Makefile'):
        write_file(of, filename)

of.write("\n\\end{document}")
of.close()

