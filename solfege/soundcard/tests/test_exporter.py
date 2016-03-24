# Solfege - free ear training software
# Copyright (C) 2007, 2008, 2011 Tom Cato Amundsen
# License is GPL, see file COPYING

import os
import unittest
from solfege.soundcard.exporter import MidiExporter
from solfege.mpd.track import Track
from solfege.testlib import outdir

class TestMidiExporter(unittest.TestCase):
    def test_empty(self):
        m = MidiExporter()
        m.start_export(os.path.join(outdir, "a.mid"))
        m.end_export()
        # We don't generate a file if no music has been played
        # since start_export()
        self.assertFalse(os.path.exists(os.path.join(outdir, "a.mid")))
    def test_export_track(self):
        t = Track()
        t.start_note(50, 120)
        m = MidiExporter()
        m.start_export(os.path.join(outdir, "a.mid"))
        m.play_track(t)
        m.end_export()
        os.remove(os.path.join(outdir, "a.mid"))

suite = unittest.makeSuite(TestMidiExporter)

