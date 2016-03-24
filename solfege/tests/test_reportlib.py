# Solfege - free ear training software
# Copyright (C) 2007, 2008, 2011 Tom Cato Amundsen
# License is GPL, see file COPYING

from __future__ import absolute_import
import unittest
import os

from solfege.testlib import outdir
from solfege.reportlib import *

class TestReport(unittest.TestCase):
    def create_report(self):
        r = Report()
        r.append(Heading(1, "Heading1"))
        r.append(Paragraph("Text"))
        t = Table()
        r.append(t)
        row = TableRow()
        row.append("Cell1 text")
        row.append("Cell2 text")
        t.append(row)
        t.append_row("cell1", "cell2")
        return r
    def test_html(self):
        r = self.create_report()
        HtmlReport(r, os.path.join(outdir, "t1.html"))
        os.remove(os.path.join(outdir, "t1.html"))
    def test_latex(self):
        r = self.create_report()
        LatexReport(r, os.path.join(outdir, "t1.tex"))
        os.remove(os.path.join(outdir, "t1.tex"))

suite = unittest.makeSuite(TestReport)

