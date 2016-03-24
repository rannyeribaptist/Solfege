# GNU Solfege - free ear training software
# vim: set fileencoding=utf-8 :
# Copyright (C) 2012 Tom Cato Amundsen
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

import sys
sys.path.append(".")

import re

import solfege.parsetree as pt
from solfege.dataparser import Question

class LfMod(object):
    def __init__(self, builtins=None):
        if not builtins:
            builtins = {}
        self.m_builtins = builtins
        self.m_globals = builtins.copy()
        self.m_blocklists = {}
    def dump(self):
        import pprint
        print "Globals:"
        pprint.pprint(self.m_globals)
        print "Blocks:"
        pprint.pprint(self.m_blocklists)
        print "--------"

translation_re = re.compile("(?P<varname>\w+)\[(?P<lang>[\w_+]+)\]")
def do_assignment(mod, statement, local_namespace, global_namespace, in_header,
        included):
    """
    in_header is True if the assignment is done inside a header block. We
    need to treat assignments to the 'module' variable special, since we
    must handle module names that are equal to already defined variables
    and functions.
    """
    if isinstance(statement.right, pt.Program):
        local_namespace[unicode(statement.left)] = parse_tree_interpreter(statement.right, mod.m_builtins)
    else:
        m = translation_re.match(unicode(statement.left))
        if m:
            if m.group('varname') not in local_namespace:
                print "FIXME: correct exception aka LessonfileException"
                raise Exception("Define the C-locale variable before adding translations")
            if in_header and included:
                if m.group('varname') in local_namespace:
                    return
            local_namespace[m.group('varname')] = \
                local_namespace[m.group('varname')].add_translation(
                    m.group('lang'),
                    statement.right.evaluate(local_namespace, global_namespace))
        else:
            if in_header:
                if included:
                    if unicode(statement.left) in local_namespace:
                        return
                if in_header and statement.left == 'module':
                    local_namespace[unicode(statement.left)] = unicode(statement.right)
                    return
            local_namespace[unicode(statement.left)] = statement.right.evaluate(local_namespace, global_namespace) 


def do_module(block, mod, included=False):
    assert isinstance(mod, LfMod)
    assert isinstance(block, pt.Program)
    for statement in block:
        if isinstance(statement, pt.Assignment):
            # On the module top level, the local namespace it the
            # global namespace
            try:
                do_assignment(mod, statement, mod.m_globals, mod.m_globals, False, included)
            except pt.ParseTreeException, e:
                e.m_nonwrapped_text = block._lexer.get_err_context(e.m_tokenpos)
                raise
        elif isinstance(statement, (pt.Block, pt.NamedBlock)):
            blocks = mod.m_blocklists.setdefault(statement.m_blocktype, [])
            if statement.m_blocktype == 'question':
                blocks.append(Question())
            elif statement.m_blocktype == 'header':
                if not blocks:
                    blocks.append({})
            else:
                blocks.append({})
            if isinstance(statement, pt.NamedBlock):
                mod.m_globals[statement.m_name] = blocks[-1]
                # Named blocks need to know their name. It is not enough
                # that their name point to them from the global name space.
                # Evercises like elembuilder need to lookup their name
                # like a dict: elem['name']
                blocks[-1]['name'] = statement.m_name
            for block_statement in statement:
                try:
                    do_assignment(mod, block_statement, blocks[-1], mod.m_globals,
                              statement.m_blocktype == 'header', included)
                except pt.ParseTreeException, e:
                    e.m_nonwrapped_text = block._lexer.get_err_context(e.m_tokenpos)
                    raise
        elif isinstance(statement, pt.IncludeStatement):
            do_module(statement.m_inctree, mod, included=True)
    return mod


def parse_tree_interpreter(tree, builtins=None):
    """
    Interpret a parse tree from solfege.parsetree into LfMod objects
    """
    mod = LfMod(builtins)
    do_module(tree, mod)
    return mod

