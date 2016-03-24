# GNU Solfege - free ear training software
# Copyright (C) 2007, 2008, 2011 Tom Cato Amundsen
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
import codecs

class Heading(object):
    def __init__(self, level, text):
        """
        1 is top level heading, 2 is below that.
        """
        self.m_level = level
        self.m_text = text

class Report(list):
    pass

class Paragraph(unicode):
    pass

class Table(list):
    def append_row(self, *cells):
        self.append(cells)

class TableRow(list):
    pass

class ReportWriterCommon(object):
    def __init__(self, report, filename):
        self.m_outfile = codecs.open(filename, "w", "utf-8")
        self.write_report(report)
        self.m_outfile.close()

class HtmlReport(ReportWriterCommon):
    def write_report(self, report):
        print >> self.m_outfile, """<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
<style type="text/css">
th { text-align: left; border-bottom: 1px solid black}
</style>
</head>
<body>"""
        for elem in report:
            f = {'Heading': self.write_heading,
                 'Paragraph': self.write_paragraph,
                 'Table': self.write_table,
                }[elem.__class__.__name__](elem)
        print >> self.m_outfile, "</body>\n</html>"
    def write_heading(self, heading):
        print >> self.m_outfile, "<h%(level)i>%(str)s</h%(level)i>" % {
            'level': heading.m_level,
            'str': heading.m_text}
    def write_paragraph(self, paragraph):
        print >> self.m_outfile, "<p>%s</p>" % paragraph
    def write_table(self, table):
        print >> self.m_outfile, "<table border='0'>"
        for row in table:
            self.write_tablerow(row)
        print >> self.m_outfile, "</table>"
    def write_tablerow(self, row):
        print >> self.m_outfile, "<tr>"
        for t in row:
            print >> self.m_outfile, "<td>%s</td>" % t
        print >> self.m_outfile, "</tr>"

class LatexReport(ReportWriterCommon):
    def write_report(self, report):
        print >> self.m_outfile, r"\documentclass{article}"
        print >> self.m_outfile, r"\begin{document}"
        for elem in report:
            f = {'Heading': self.write_heading,
                 'Paragraph': self.write_paragraph,
                 'Table': self.write_table,
            }[elem.__class__.__name__](elem)
        print >> self.m_outfile, r"\end{document}"
    def write_heading(self, heading):
        print >> self.m_outfile, r"\section{%s}" % heading.m_text
    def write_paragraph(self, paragraph):
        print >> self.m_outfile, paragraph
    def write_table(self, t):
        pass
    def write_tablerow(self, t):
        pass

