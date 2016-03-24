#!/usr/bin/python
# Copyright (C) 2007, 2008, 2011 Tom Cato Amundsen
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

# Undocumented
# chordvoicing (test written)
# harmonicprogressiondictation (test written)
# identifybpm
# singinterval
# tuner
# twelvetone

# Documented. Not test
# harmonicinterval
# melodicinterval
# singinterval
# compareintervals
# rhythm
# rhythmtapping2
# idtone
# nameinterval

# idbyname
# singanswer
# rhythmtapping
# chord (obsolete)
# idproperty
# dictation
# singchord
# elembuilder

module_to_mtype = {
  'idbyname': ('voice', 'rvoice', 'chord', 'music'),
  'singanswer': ('voice', 'rvoice', 'chord', 'music'),
  'rhythmtapping': ('voice', 'rvoice'),
  'chord': ('chord',),
  'idproperty': ('chord', 'rvoice',),
  'dictation': ('music', 'voice', 'rvoice',),
  'singchord': ('satb',),
  'elembuilder': ('voice', 'rvoice', 'music'),
  'harmonicprogressiondictation': ('music', 'rvoice'),
  'chordvoicing': ('chord', 'satb'),
}

ok = {
    'voice': "c d e",
    'chord': "c e g",
    'music': "\\staff{ c' d' e'}",
    'satb': "c'' | e' | g | c",
}

errors = {
    'voice': [
        "< c",
        "3c EX d",
        "*",
        r"\time 3\4 c d",
        r"\time 3/x c d",
        r"c \time 3\4 c d",
        r"c4 \times 3/2{ c \times 4/6 { c e } }",
        "c4. c.",
        "c4 { jo ",
        "c4 >d < e }",
        "c4 <d < e }",
        "\clef xxx c4 d e }",
    ],
    'chord': [
        "c > e g",
        "<",
        "c ERR g",
        r"\c e g",
        r"\clef noclefsaadlj c e ",
        "{",
    ],
    'music': [
        "\\staff{}\n\\staff()\n\\staff",
        "\\addvoice{ c \ne g}\n\\staff{ x\n y x}",
        r"clkfja slkdfj",
        r"\staff{ \clef ERROR c",
        "\\staff{ \clef ERROR \n c",
        "\\staff{ \clef \n ERROR \n c",
        r"\staff{ c < }",
        r"}",
    ],
    'satb': [
        "|||",
        " c | > | |",
        "c'' | g' | error | c",
        "c'' | g' | \n ER | c",
        " |dfd",
        " | | |}",
    ],
}
errors['rvoice'] = errors['voice']

def set1():
    for module in module_to_mtype:
        of = open("exercises/standard/regression-lesson-files/xx-%s-exceptions" % module, "w")
        if module == 'elembuilder':
            print >> of, 'include("../lesson-files/include/progression-elements")'
        print >> of, "header {"
        print >> of, "  module = %s" % module
        print >> of, '  title = "%s mpd errors"' % module
        print >> of, "  lesson_id = \"%s-module-exceptions\"" % module
        print >> of, "  have_repeat_slowly_button = yes"
        if module == 'idbyname':
            print >> of, "  filldir = horiz"
            print >> of, "  fillnum = 4"
        elif module == 'elembuilder':
            print >> of, "  elements = auto"
        elif module == 'idproperty':
            print >> of, '  flavour = "chord"'
        print >> of, "}"
        for mtype in module_to_mtype[module]:
            if mtype == module_to_mtype[module][0]:
                vv = [ok[mtype]]
            else:
                vv = []
            if mtype in errors:
                for music in vv + errors[mtype]:
                    print >> of, "question {"
                    print >> of, '  name = "%s: %s"' % (mtype, music)
                    print >> of, '  music = %s("%s")' % (mtype, music)
                    if module == 'singanswer':
                        print >> of, 'question_text = "question..."'
                        print >> of, 'answer = music %s("%s")' % (mtype, music)
                    elif module == 'elembuilder':
                        print >> of, 'elements = progI, progIV'
                    print >> of, "}"
        of.close()

set1()
