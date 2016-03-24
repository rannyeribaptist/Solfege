#!/usr/bin/python

"""
literal ::=  stringliteral | integer | floatnumber
expression_list ::=  expression ( "," expression )* [","]
assignment_stmt ::=  target "=" expression_list
target          ::=  identifier
atom      ::=  identifier | literal
# We use this for imported modules lookup
attributeref ::=  primary "." identifier
"""

class ParseTreeException(Exception):
    def __init__(self, msg, token):
        Exception.__init__(self, msg)
        self.m_tokenpos = token.m_tokenpos

class LookupException(ParseTreeException):
    pass


class Identifier(unicode):
    check_ns = True
    def __repr__(self):
        return u"Identifier(%s)" % self
    def evaluate(self, local_namespace, global_namespace):
        if "." in self:
            mod, name = self.split(".")
        else:
            mod = None
            name = self
        for namespace in local_namespace, global_namespace:
            if mod:
                if mod in namespace:
                    return namespace[mod].m_globals[name]
            else:
                if name in namespace:
                    return namespace[name]
        if self.check_ns:
            raise LookupException("Unknown identifier '%s'" % name, self)
        return self

class Node(object):
    def dump(self, indent=0):
        print " " * indent, self

class Literal(Node):
    """
    Literal python object: integer or unicode string
    """
    def __init__(self, value):
        Node.__init__(self)
        assert isinstance(value, (int, unicode, float))
        self.m_value = value
    def evaluate(self, local_namespace, global_namespace):
        return self.m_value
    def __repr__(self):
        return u"Literal(%s)" % repr(self.m_value)

class TempoType(Node):
    def __init__(self, bpm, nlen):
        self.m_bpm = bpm
        self.m_nlen = nlen
    def evaluate(self, local_namespace, global_namespace):
        return (self.m_bpm.evaluate(local_namespace, global_namespace),
               self.m_nlen.evaluate(local_namespace, global_namespace))


class Assignment(Node):
    def __init__(self, name, expression):
        Node.__init__(self)
        self.left = name
        self.right = expression
    def __repr__(self):
        return u"%s = %s" % (self.left, self.right)

class FunctionCall(Node):
    class WrongArgumentCount(ParseTreeException):
        def __init__(self, functioncall):
            ParseTreeException.__init__(self, "Wrong argument count", functioncall)
    def __init__(self, dp, name, args):
        # We need to remember which dataparser called us because
        # at least one of the functions need this. FIXME I think we
        # want to remove this.
        Node.__init__(self)
        self.m_dataparser = dp
        self.m_name = name
        self.m_args = args
    def __repr__(self):
        return u"%s(%s)" % (self.m_name, self.m_args)
    def evaluate(self, local_namespace, global_namespace):
        args = [x.evaluate(local_namespace, global_namespace) for x in self.m_args]
        # Functions are only in the global namespace, as functions
        # cannot be defined in the lesson files
        if self.m_name not in global_namespace:
            raise LookupException("Function name unknown", self)
        if global_namespace[self.m_name][0]:
            args.insert(0, self.m_dataparser)
        try:
            return global_namespace[self.m_name][1](*args)
        except TypeError:
            raise self.WrongArgumentCount(self.m_args)

class Addition(Node):
    def __init__(self, left, right):
        self.left = left
        self.right = right
    def evaluate(self, local_namespace, global_namespace):
        return (self.left.evaluate(local_namespace, global_namespace)
                + self.right.evaluate(local_namespace, global_namespace))

class StringFormatting(Node):
    def __init__(self, left, right):
        self.left = left
        self.right = right
    def evaluate(self, local_namespace, global_namespace):
        return (self.left.evaluate(local_namespace, global_namespace)
                % self.right.evaluate(local_namespace, global_namespace))

class ExpressionList(Node, list):
    def evaluate(self, local_namespace, global_namespace):
        return [x.evaluate(local_namespace, global_namespace) for x in self]

class CodeBlock(Node, list):
    def add_statement(self, statement):
        self.append(statement)
    def dump(self, indent=0):
        Node.dump(self, indent)
        try:
            for statement in self:
                statement.dump(indent + 2)
        except AttributeError:
            pass

class IncludeStatement(Node):
    def __init__(self, inctree):
        Node.__init__(self)
        self.m_inctree = inctree

class Block(CodeBlock):
    def __init__(self, blocktype):
        CodeBlock.__init__(self)
        self.m_blocktype = blocktype
    def __repr__(self):
        return u"UnnamedBlock(type=%s)" % self.m_blocktype


class NamedBlock(CodeBlock):
    """
    A named block will have the name referring to it inserted
    into the namespace it is defined in.
    """
    def __init__(self, blocktype, name):
        CodeBlock.__init__(self)
        self.m_blocktype = blocktype
        self.m_name = name
    def __repr__(self):
        return u"NamedBlock(type=%s, name=%s)" % (self.m_blocktype, self.m_name)


class Program(CodeBlock):
    def __init__(self):
        CodeBlock.__init__(self)
    def dump(self, indent=0):
        print "Program:"
        for statement in self:
            statement.dump(indent + 2)

