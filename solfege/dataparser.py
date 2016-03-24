# -*- coding: iso-8859-1 -*-
# GNU Solfege - free ear training software
# Copyright (C) 2001, 2002, 2003, 2004, 2007, 2008, 2011  Tom Cato Amundsen
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

# 4.69
from __future__ import absolute_import
"""
prog             The test done before calling
 +statementlist
  +statement
   +assignment   peek: 'NAME', '='
    +expressionlist  scan('NAME') scan('=')
     +expression
      +atom()  kalles direkt på første linje. Så evt på nytt etter +-/%
       +functioncall    peek: 'NAME' '('
        +expressionlist     peek() != ')'
   +block        peek: 'NAME', '{'
    +assignments
    +expression     peek_type()!= '}'
   +include      peek: 'NAME'("include"), '(
    +prog

+assignment

"""
# på singchord-1 sparer jeg ca 0.03 på å ha _peek_type
# På singchord-1 sparer jeg ikke noe på å ha en peek2_type(t1, t2)
# som tester de to neste token.

import codecs
import os
import re
import sys
import weakref

from solfege import i18n
import solfege.parsetree as pt

NAME = 'NAME'
STRING = 'STRING'
OPERATOR = 'OPERATOR'
INTEGER = 'INTEGER'
FLOAT = 'FLOAT'
CHAR = 'CHAR'
EOF = 'EOF'

NEW_re = re.compile("""(?:
                        (\s+)|  #space
                        (\#.*?$)| #comment
                        (-?\d+\.\d+) | #float
                        (-?\d+)| #integer
                        (\"\"\"(.*?)\"\"\")| #multiline string
                        ("(.*?)")| #string
                        (\w[\[\]\w-]*) #name
                )""",
                      re.VERBOSE|re.MULTILINE|re.DOTALL|re.UNICODE)

LI_INTEGER = NEW_re.match("-3").lastindex
LI_FLOAT = NEW_re.match("3.3").lastindex
LI_MSTRING = NEW_re.match('"""string"""').lastindex
LI_STRING = NEW_re.match('"string"').lastindex
LI_NAME = NEW_re.match("name").lastindex
LI_COMMENT = NEW_re.match("# comment").lastindex

lastindex_to_ID = {LI_INTEGER: INTEGER,
                     LI_FLOAT: FLOAT,
                    LI_STRING: STRING,
                     LI_MSTRING: STRING,
                     LI_NAME: NAME,
                    }

lastindex_to_group = {LI_INTEGER: 4,
                     LI_STRING: 8,
                     LI_MSTRING: 6,
                     LI_NAME: 9,
                     LI_FLOAT: 3,
                    }

# Used to find elements in the token tuple
TOKEN_TYPE = 0
TOKEN_STRING = 1
TOKEN_IDX = 2
TOKEN_LINENO = 3

class istr(unicode):
    def __init__(self, s):
        self.cval = s
        self.m_added_language = None
    def __mod__(self, other):
        """
        Handle format strings in translated strings:
        _("%i. inversion") % 2
        """
        i=istr(unicode(self) % other)
        i.cval = self.cval % other
        return i
    def add_translation(self, lang, s):
        """
        Use this method to add translations that are included directly in
        the lesson file like this:

          name = "major"
          name[no] = "dur"
        """
        if lang in i18n.langs():
            # i18n.langs() has a list of the langauges we can use.
            # The first language in the list is preferred.
            new_pos = i18n.langs().index(lang)
            if not self.m_added_language:
                old_pos = sys.maxint
            else:
                old_pos = i18n.langs().index(self.m_added_language)
            if new_pos < old_pos:
                retval = istr(s)
                retval.m_added_language = lang
                retval.cval = self.cval
                return retval
        return self
    def new_translated(cval, translated):
        retval = istr(translated)
        retval.cval = cval
        return retval
    new_translated = staticmethod(new_translated)

def dataparser_i18n_func(s):
    if s == "":
        s = 'error in your lesson file: empty string cannot be translated'
    retval = istr(_(s))
    retval.cval = s
    return retval

def dataparser_i18n__i_func(s):
    if s == "":
        s = 'error in your lesson file: empty string cannot be translated'
    retval = istr(_i(s))
    retval.cval = s
    return retval


class Question(dict):
    def __getattr__(self, n):
        if n in self:
            return self[n]
        raise AttributeError()
    def __setattr__(self, name, value):
        self[name] = value


class DataparserException(Exception):
    def __init__(self, message):
        Exception.__init__(self, message)


class DataparserSyntaxError(DataparserException):
    def __init__(self, parser, bad_pos, expect):
        DataparserException.__init__(self, _('Syntax error in file "%(filename)s". %(expected)s') % {'filename': parser.m_filename, 'expected': expect})
        # This variable is only used by the module test code.
        self.m_token = parser._lexer.m_tokens[bad_pos]
        self.m_nonwrapped_text = parser._lexer.get_err_context(bad_pos)

class AssignmentToReservedWordException(DataparserException):
    def __init__(self, parser, bad_pos, word):
        DataparserException.__init__(self, _("Assignment to the reserved word \"%(word)s\"") % {'word': word})
        # This variable is only used by the module test code.
        self.m_token = parser._lexer.m_tokens[bad_pos]
        self.m_nonwrapped_text = parser._lexer.get_err_context(bad_pos)

class CanOnlyTranslateStringsException(DataparserException):
    def __init__(self, parser, bad_pos, variable):
        DataparserException.__init__(self, _("We can only translate strings using in-file translations (ex var[no]=...). See the variable \"%(variable)s\" in the file \"%(filename)s\"") % {'filename': parser.m_filename, 'variable': variable})
        # This variable is only used by the module test code.
        self.m_token = parser._lexer.m_tokens[bad_pos]
        self.m_nonwrapped_text = parser._lexer.get_err_context(bad_pos)


class UnableToTokenizeException(DataparserException):
    def __init__(self, lexer, lineno, token, pos):
        """
        lineno is the zero indexed line number where the exception happened.
        token is the char that we cannot tokenize
        pos is the position in the string we are tokenizing.
        """
        # This line will add a fake token tuple, so that get_err_context
        # can produce useful output.
        lexer.m_tokens.append(('FIXME', token, pos, lineno))
        # This variable is only used by the module test code.
        self.m_token = lexer.m_tokens[-1]
        DataparserException.__init__(self,
            _('Unable to tokenize line %(lineno)i of the file "%(filename)s"') % {
                'lineno': lineno + 1,
                'filename': lexer.m_parser().m_filename})
        self.m_nonwrapped_text = lexer.get_tokenize_err_context()


class Lexer:
    def __init__(self, src, parser):
        assert isinstance(src, str)
        if parser:
            self.m_parser = weakref.ref(parser)
        else:
            self.m_parser = parser
        r = re.compile("#.*?coding\s*[:=]\s*([\w_.-]+)")
        # according to http://www.python.org/dev/peps/pep-0263/
        # the encoding marker must be in the first two lines
        m = r.match("\n".join(src.split("\n")[0:2]))
        if m:
            src = unicode(src, m.groups()[0], errors="replace")
        else:
            src = unicode(src, "UTF-8", errors="replace")
        assert isinstance(src, unicode)
        src = src.replace("\r", "\n")
        # Some editors (notepad on win32?) insert the BOM, so we have
        # to check for it and remove it since the lexer don't handle it.
        src = src.lstrip(unicode(codecs.BOM_UTF8, "utf8"))
        self.m_src = src
        self.pos = 0
        pos = 0
        lineno = 0
        self.m_tokens = []
        while 1:
            try:
                if src[pos] in u"\u202f\xa0 \n\t{}=%+,/().":
                    if src[pos] in u'\u202f\xa0 \t':
                        pos += 1
                        continue
                    if src[pos] == '\n':
                        pos += 1
                        lineno += 1
                        continue
                    self.m_tokens.append(('%s' % src[pos], src[pos], pos, lineno))
                    pos += 1
                    continue
            except IndexError:
                break
            m = NEW_re.match(src, pos)
            if not m:
                raise UnableToTokenizeException(self, lineno, src[pos], pos)
            if m.lastindex == LI_COMMENT:
                pass
            else:
                self.m_tokens.append((lastindex_to_ID[m.lastindex],
                         m.group(lastindex_to_group[m.lastindex]), pos, lineno))
            pos = m.end()
        self.m_tokens.append(("EOF", None, pos, lineno))
        self.m_tokens.append(("EOF", None, pos, lineno))
        self.m_tokens.append(("EOF", None, pos, lineno))
        self.m_tokens.append(("EOF", None, pos, lineno))
    def _err_context_worker(self, lexer_pos):
        ret = ""
        lineno = self.m_tokens[lexer_pos][TOKEN_LINENO]
        x = self.m_tokens[lexer_pos][TOKEN_IDX]
        while x > 0 and self.m_src[x-1] != "\n":
            x -= 1
        linestart_idx = x
        erridx_in_line = self.m_tokens[lexer_pos][TOKEN_IDX] - linestart_idx
        if lineno > 1:
            ret += "\n(line %i): %s" % (lineno-1, self.get_line(lineno-2))
        if lineno > 0:
            ret += "\n(line %i): %s" % (lineno, self.get_line(lineno-1))
        ret += "\n(line %i): %s" % (lineno + 1, self.get_line(lineno))
        ret += "\n" + " " * (erridx_in_line + len("(line %i): " % (lineno+1))) + "^"
        return ret.strip()
    def get_tokenize_err_context(self):
        """
        return a string with the last part of the file that we were able
        to tokenize. Used by UnableToTokenizeException
        """
        return self._err_context_worker(len(self.m_tokens)-1)
    def get_err_context(self, pos):
        return self._err_context_worker(pos)
    def new_get_err_context(self, pos1, pos2):
        # Line number of the last part of the error. We will display
        # two lines, the last line containing (part of) the error, and
        # the line before it.
        l2 = self.m_src[:pos2].count("\n")
        # i1 and i2 is the start and end of the text that should be
        # marked as erroneous. If the error is stretched over several
        # lines, then we will only mark the last line.
        i = pos2
        while i > 0 and self.m_src[i] != "\n":
            i -= 1
        i2 = pos2 - i - 1
        if pos1 > i:
            i1 = pos1 - i - 1
        else:
            i1 = 0
        linestr = "(line %i):" % (l2 + 1)
        return ("(line %i): %s\n" % (l2 , self.get_line(l2-1))
              + "%s %s\n" % (linestr, self.get_line(l2))
              + " " * (i1 + len(linestr) + 1) + "^" * (i2 - i1))
    def peek(self, forward=0):
        return self.m_tokens[self.pos+forward]
    def peek_type(self, forward=0):
        return self.m_tokens[self.pos+forward][TOKEN_TYPE]
    def peek_string(self, forward=0):
        return self.m_tokens[self.pos+forward][TOKEN_STRING]
    def scan_any(self):
        """scan the next token"""
        self.pos += 1
        return self.m_tokens[self.pos-1][TOKEN_STRING]
    def scan(self, t=None):
        """t is the type of token we expect"""
        if self.m_tokens[self.pos][TOKEN_TYPE] == t:
            self.pos += 1
            return self.m_tokens[self.pos-1][TOKEN_STRING]
        else:
            # Tested in TestLexer.test_scan
            raise DataparserSyntaxError(self.m_parser(), self.pos,
                _("Token \"%(nottoken)s\" not found, found \"%(foundtoken)s\" of type %(type)s.") % {
                    'nottoken': t,
                    'foundtoken': self.m_tokens[self.pos][TOKEN_STRING],
                    'type': self.m_tokens[self.pos][TOKEN_TYPE]})
    def get_line(self, lineno):
        """line 0 is the first line
        Return an empty string if lineno is out of range.
        """
        idx = 0
        c = 0
        while c < lineno and idx < len(self.m_src):
            if self.m_src[idx] == '\n':
                c += 1
            idx += 1
        x = idx
        while x < len(self.m_src) and self.m_src[x] != '\n':
            x += 1
        return self.m_src[idx:x]

class Dataparser:
    """
    Parse a lesson file into a parsetree.Program
    """
    def __init__(self):
        self.m_filename = None
        self.m_translation_re = re.compile("(?P<varname>\w+)\[(?P<lang>[\w_+]+)\]")
    def parse_file(self, filename):
        """We always construct a new parser if we want to parse another
        file. So this method is never called twice for one parser.
        """
        self.m_filename = filename
        self.m_location = os.path.split(filename)[0]
        self._lexer = Lexer(open(filename, 'rU').read(), self)
        self.reserved_words = ('_', 'question', 'header')
        self.prog()
    def parse_string(self, s, really_filename=False):
        assert isinstance(s, str)
        if really_filename:
            self.m_filename = really_filename
        else:
            self.m_filename = "<STRING>"
        self._lexer = Lexer(s, self)
        self.reserved_words = ('_', 'question', 'header')
        self.prog()
    def prog(self):
        """prog: statementlist EOF"""
        self.tree = pt.Program()
        self.tree.m_filename = self.m_filename
        self.tree._lexer = self._lexer
        self.statementlist()
        if self._lexer.peek_type() != 'EOF':
            # This exception will be raised if we for example have
            # an extra { after a block definition.
            raise DataparserSyntaxError(self, self._lexer.pos,
                    'Expected end of file or statement.')
        self._lexer.scan('EOF')
    def statementlist(self):
        """statementlist: (statement+)"""
        while self._lexer.peek_type() == 'NAME':
            self.tree.add_statement(self.statement())
    def statement(self, allow_music_shortcut=False):
        """
        statement: assignment | block | include | import
        allow_music_shortcut can be set when we are parsing assignments
        in a question block.
        """
        if self._lexer.peek_type(1) == '=':
            return self.assignment()
        elif self._lexer.peek_type(1) == '{':
            return self.block()
        elif self._lexer.peek_type(1) == 'NAME' \
                and self._lexer.peek_type(2) == '{':
            return self.named_block()
        elif self._lexer.peek_type() == 'NAME' \
                and self._lexer.peek_string() == 'include' \
                and self._lexer.peek_type(1) == '(':
            return self.include()
        elif (self._lexer.peek_type() == 'NAME'
              and self._lexer.peek_string() == 'import'):
            return self.do_import()
        elif (self._lexer.peek_type() == 'NAME'
              and self._lexer.peek_string() == 'rimport'):
            return self.do_rimport()
        elif allow_music_shortcut:
            fakt = self.expressionlist()
            if self._lexer.peek_type() == '}':
                return pt.Assignment(pt.Identifier(u"music"), fakt[0])
            else:
                raise DataparserSyntaxError(self, self._lexer.pos, "The (obsolete) music shortcut construct must be the last statement in a question block.")
        self._lexer.scan_any()
        raise DataparserSyntaxError(self, self._lexer.pos, "Parse error")
    def include(self):
        self._lexer.scan_any() # scan include
        self._lexer.scan_any() # scan (
        try:
            filename = self._lexer.scan('STRING')
        except:
            print >> sys.stderr, "Warning: The file '%s' uses old style syntax for the include command." % self.m_filename
            print >> sys.stderr, 'This is not fatal now but will be in the future. You should change the code\nfrom include(filename) to include("filename")\n'
            filename = self._lexer.scan('NAME')
        fn = os.path.join(self.m_location, filename)
        if not os.path.exists(fn):
            fn = os.path.join(os.getcwdu(), u'exercises/standard/lesson-files', filename)
        s = open(fn, 'rU').read()
        p = Dataparser()
        p.m_location = self.m_location
        p.parse_string(s)
        self._lexer.scan(')')
        return pt.IncludeStatement(p.tree)
    def _import_worker(self, fn1, fn2):
        self._lexer.scan_any() # scan the 'import' or 'rimport' keyword
        mod_filename = self._lexer.scan_any()
        if (self._lexer.peek_type() == 'NAME'
            and self._lexer.peek_string() == 'as'):
            self._lexer.scan_any()
            mod_name = self._lexer.scan('NAME')
        else:
            mod_name = mod_filename
        p = Dataparser()
        fn1 = os.path.join(fn1, mod_filename)
        fn2 = os.path.join(fn2, mod_filename)
        if os.path.exists(fn1) or not os.path.exists(fn2):
            p.parse_file(fn1)
        else:
            p.parse_file(fn2)
        return pt.Assignment(pt.Identifier(mod_name), p.tree)
    def do_import(self):
        return self._import_worker(
            os.path.join(os.getcwdu(), "exercises", "standard", "lib"),
            os.path.join(self.m_location, "..", "lib"))
    def do_rimport(self):
        return self._import_worker(
            os.path.join(self.m_location, "..", "lib"),
            os.path.join(os.getcwdu(), "exercises", "standard", "lib"))
    def assignment(self):
        """NAME "=" expression ("," expression)* """
        npos = self._lexer.pos
        name = self._lexer.scan_any()#('NAME')
        if name in self.reserved_words:
            # do "question = 1" to raise this exception.
            raise AssignmentToReservedWordException(self, npos, name)
        self._lexer.scan_any()#('=')
        fpos = self._lexer.pos
        expressionlist = self.expressionlist()
        m = self.m_translation_re.match(name)
        if m:
            if len(expressionlist) != 1:
                raise CanOnlyTranslateStringsException(self, fpos, name)
            if not isinstance(expressionlist[0].m_value, istr):
                raise CanOnlyTranslateStringsException(self, fpos, name)
        if len(expressionlist) == 1:
            return pt.Assignment(pt.Identifier(name), expressionlist[0])
        else:
            return pt.Assignment(pt.Identifier(name), expressionlist)
    def expression(self):
        """expression: atom
              ("+" atom
              |"-" atom
              |"/" atom
              )*
              """
        # use tmp var just in case an atom in the future is more than
        # one token.
        n = self._lexer.pos
        expression = self.atom()
        expression.m_tokenpos = n
        peek = self._lexer.peek_type()
        while 1:
            if peek == '+':
                self._lexer.scan_any()
                expression = pt.Addition(expression, self.atom())
            elif peek == '-':
                self._lexer.scan_any()
                expression -= self.atom()
            elif peek == '/':
                self._lexer.scan_any()
                expression = pt.TempoType(expression, self.atom())
            elif peek == '%':
                self._lexer.scan_any()
                expression = pt.StringFormatting(expression, self.atom())
            else:
                break
            peek = self._lexer.peek_type()
        return expression
    def expressionlist(self):
        """expressionlist: expression ("," expression)* """
        # use tmp var just in case an atom in the future is more than
        # one token.
        n = self._lexer.pos
        expressionlist = pt.ExpressionList([self.expression()])
        expressionlist.m_tokenpos = n
        while self._lexer.peek_type() == ',':
            self._lexer.scan_any()
            expressionlist.append(self.expression())
        return expressionlist
    def atom(self):
        """atom: INTEGER | FLOAT | STRING | NAME | FUNCTIONCALL"""
        npos = self._lexer.pos
        peek = self._lexer.peek_type()
        if peek == 'STRING':
            return pt.Literal(istr(self._lexer.scan('STRING')))
        elif peek == 'INTEGER':
            return pt.Literal(int(self._lexer.scan('INTEGER')))
        elif peek == 'FLOAT':
            return pt.Literal(float(self._lexer.scan('FLOAT')))
        elif peek == 'NAME':
            if self._lexer.peek_type(1) == '(':
                return self.functioncall()
            name = self._lexer.scan('NAME')
            while self._lexer.peek_type() == '.':
                self._lexer.scan_any()
                if self._lexer.peek_type() != 'NAME':
                    raise DataparserSyntaxError(self, self._lexer.pos, 'Identifier expected')
                name += "." + self._lexer.scan('NAME')
            return pt.Identifier(name)
        else:
            #print "FIXME: have no idea how to raise this exception"
            raise DataparserSyntaxError(self, npos + 1,
                "Expected STRING, INTEGER or NAME+'('")
    def functioncall(self):
        """functioncall: NAME "(" expressionlist ")" """
        npos = self._lexer.pos
        name = self._lexer.scan_any()#'NAME')
        self._lexer.scan('(')
        if self._lexer.peek_type() == ')':
            # functioncall()
            ret = pt.FunctionCall(self, name, [])
            self._lexer.scan(')')
        else:
            # functioncall(arglist)
            arglist = self.expressionlist()
            self._lexer.scan(')')
            ret = pt.FunctionCall(self, name, arglist)
        ret.m_tokenpos = npos
        return ret
    def block(self):
        """block: NAME "{" assignments"}" """
        block = pt.Block(self._lexer.scan_any())
        self._lexer.scan_any() # scan '{'
        # FIXME this is not nice, but we need it since we have
        # allowed question blocks with the shortcut where they
        # omit "music ="
        while self._lexer.peek_type() != '}':
            block.add_statement(self.statement(allow_music_shortcut=True))
        self._lexer.scan("}")
        return block
    def named_block(self):
        blocktype = self._lexer.scan('NAME')
        name = self._lexer.scan('NAME')
        block = pt.NamedBlock(blocktype, name)
        self._lexer.scan('{')
        while self._lexer.peek_type() == 'NAME':
            block.add_statement(self.statement())
        self._lexer.scan("}")
        return block

