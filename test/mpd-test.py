#!/usr/bin/python

from gi.repository import Gtk
import sys, os
sys.path.append(".")
import solfege.i18n
solfege.i18n.setup(".")
import solfege.cfg
from solfege import filesystem
solfege.cfg.initialise("default.config", None, filesystem.rcfile())



from gi.repository import Gtk

from solfege import gu
from solfege import mpd
from solfege.mpd.musicdisplayer import MusicDisplayer
from solfege import soundcard
from solfege import utils

musicfile = "mpd-test.txt"

class DisplaytestWindow(Gtk.Window):
    def on_quit(self, w):
        t = self.m_buf.get_text(self.m_buf.get_start_iter(),
                                self.m_buf.get_end_iter(), True)
        self.save(t)
    def __init__(self):
        Gtk.Window.__init__(self)
        self.connect('destroy', self.on_quit)
        self.vbox = vbox = Gtk.VBox()
        vbox.show()
        self.add(vbox)
        self.g_text = Gtk.TextView()
        self.g_text.set_size_request(-1, 100)
        self.g_text.show()
        self.g_text.set_editable(True)
        try:
            s = open(musicfile, "r").read()
        except IOError, e:
            s = r"\staff{c' d' e'}"
        self.m_buf = self.g_text.get_buffer()
        self.m_buf.insert(self.m_buf.get_end_iter(), s)
        vbox.pack_start(self.g_text, True, True, 0)
        self.g_displayer = MusicDisplayer()
        self.g_displayer.set_size_request(200, 200)
        self.g_displayer.show()
        self.vbox.pack_start(self.g_displayer, True, True, 0)
        gu.bButton(vbox, "Parse", self.on_parse)
        gu.bButton(vbox, "Display", self.on_display)
        gu.bButton(vbox, "Display first notes", self.on_display_first_notes)
        gu.bButton(vbox, "Play", self.on_play)
        gu.bButton(vbox, "Play first", self.on_play_first)
    def save(self, text):
        f = open(musicfile, 'w')
        f.write(text)
        f.close()
    def on_parse(self, _o):
        t = self.m_buf.get_text(self.m_buf.get_start_iter(),
                                self.m_buf.get_end_iter(), True)
        score = mpd.parser.parse_to_score_object(t)
    def on_display(self, _o):
        t = self.m_buf.get_text(self.m_buf.get_start_iter(),
                                self.m_buf.get_end_iter(), True)
        self.save(t)
        self.g_displayer.display(t, 20)
    def on_display_first_notes(self, _o):
        t = self.m_buf.get_text(self.m_buf.get_start_iter(),
                                self.m_buf.get_end_iter(), True)
        self.save(t)
        self.g_displayer.display(t, 20, mpd.Rat(0, 1))
    def on_play(self, _o):
        t = self.m_buf.get_text(self.m_buf.get_start_iter(),
                                self.m_buf.get_end_iter(), True)
        self.save(t)
        utils.play_music(t, (120, 4), 0, 100)
    def on_play_first(self, _o):
        t = self.m_buf.get_text(self.m_buf.get_start_iter(),
                                self.m_buf.get_end_iter(), True)
        tr = mpd.music_to_tracklist(t, mpd.Rat(0, 1), mpd.Rat(1, 8))
        soundcard.synth.play_track(*tr)


#soundcard.initialise_devicefile("/dev/sequencer", 0)
#soundcard.initialise_devicefile("/dev/music", 0)
#soundcard.initialise_using_fake_synth()
soundcard.initialise_external_midiplayer()

w = DisplaytestWindow()
w.connect('destroy', Gtk.main_quit)
w.show()
Gtk.main()
