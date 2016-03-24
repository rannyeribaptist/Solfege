# GNU Solfege - free ear training software
# Copyright (C) 2010, 2011 Tom Cato Amundsen
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
from pyalsa import alsaseq

from solfege.soundcard.synth_common import SynthCommon
from solfege.mpd.track import MidiEventStream
from solfege import soundcard


class AlsaSequencer(SynthCommon):
    name = "solfege-alsa.py"
    def __init__(self, clientport, verbose_init):
        SynthCommon.__init__(self)
        self.m_type_major = "ALSA"
        self.m_sequencer = alsaseq.Sequencer(name = 'default',
                              clientname = self.name,
                              streams = alsaseq.SEQ_OPEN_OUTPUT,
                              mode = alsaseq.SEQ_NONBLOCK)
        if verbose_init:
            print "clientport:", clientport
            print "Sequencer", self.m_sequencer
            print "\tname:", self.m_sequencer.name
            print "\tclientname", self.m_sequencer.clientname
            print "\tstreams:    %d (%s)" % (self.m_sequencer.streams, str(self.m_sequencer.streams))
            print "\tmode:       %d (%s)" % (self.m_sequencer.mode, str(self.m_sequencer.mode))
            print "\tclient_id:  %s" % self.m_sequencer.client_id
        self.m_port = self.m_sequencer.create_simple_port(name = self.name,
                             type = alsaseq.SEQ_PORT_TYPE_MIDI_GENERIC \
                                  | alsaseq.SEQ_PORT_TYPE_APPLICATION,
                             caps = alsaseq.SEQ_PORT_CAP_NONE)
        self.m_queue = self.m_sequencer.create_queue(name = self.name)
        self.m_clientport = clientport
        self.m_sequencer.connect_ports((self.m_sequencer.client_id, self.m_port), clientport)
    def play_track(self, *tracks):
        self.play_midieventstream(MidiEventStream(*tracks))
    def play_midieventstream(self, midieventstream):
        # We don't start at the very beginning. This to give the sequencer
        # a little time to get ready.
        t = 30
        a, b = self.m_sequencer.queue_tempo(self.m_queue)
        self.m_sequencer.queue_tempo(self.m_queue, a, b)
        self.m_sequencer.start_queue(self.m_queue)
        for e in midieventstream:
            if e[0] == 'program-change':
                event = alsaseq.SeqEvent(type=alsaseq.SEQ_EVENT_PGMCHANGE)
                event.dest = self.m_clientport
                event.time = t
                event.set_data({'control.channel' : e[1],
                               'control.value' : e[2],
                               })
            elif e[0] == 'volume':
                continue
            elif e[0] == 'bender':
                continue
            elif e[0] == 'note-on':
                event = alsaseq.SeqEvent(type=alsaseq.SEQ_EVENT_NOTEON)
                event.dest = self.m_clientport
                event.time = t
                event.set_data({'note.channel' : e[1],
                               'note.note' : e[2],
                               'note.velocity' : e[3],
                               })
            elif e[0] == 'notelen-time':
                t += int(96*2*4*e[1])
                continue
            elif e[0] == 'note-off':
                event = alsaseq.SeqEvent(type=alsaseq.SEQ_EVENT_NOTEOFF)
                event.dest = self.m_clientport
                event.time = t
                event.set_data({'note.channel' : e[1],
                               'note.note' : e[2],
                               'note.velocity' : e[3],
                               })
            elif e[0] == 'tempo':
                event = alsaseq.SeqEvent(type=alsaseq.SEQ_EVENT_TEMPO)
                event.dest = (0, 0)
                event.time = t
                event.set_data({'queue.param.value' : 500000 * 60 / e[1],
                                'queue.queue': self.m_queue})
            else:
                print e
                raise Exception("Not implemented")
            event.source = (0, 0)
            event.queue = self.m_queue
            self.m_sequencer.output_event(event)
        event = alsaseq.SeqEvent(alsaseq.SEQ_EVENT_STOP)
        event.source = (0, 0)
        event.queue = self.m_queue
        event.time = t
        event.dest = (alsaseq.SEQ_CLIENT_SYSTEM, alsaseq.SEQ_PORT_SYSTEM_TIMER)
        event.set_data({'queue.queue' : self.m_queue})
        self.m_sequencer.output_event(event)

        # make sure that the sequencer sees all our events
        self.m_sequencer.drain_output()
    def close(self):
        print "close: FIXME"
    def stop(self):
        self.m_sequencer.stop_queue(self.m_queue)
        self.m_sequencer.drain_output()

def get_connection_list():
    sequencer = alsaseq.Sequencer(name = 'default',
                              clientname = "solfege-alsa.py",
                              streams = alsaseq.SEQ_OPEN_OUTPUT,
                              mode = alsaseq.SEQ_NONBLOCK)
    retval = []
    clientports = sequencer.connection_list()
    for connections in clientports:
        clientname, clientid, connectedports = connections
        for port in connectedports:
            portname, portid, connections = port
            portinfo = sequencer.get_port_info(portid, clientid)
            type = portinfo['type']
            caps = portinfo['capability']
            if (type & alsaseq.SEQ_PORT_TYPE_MIDI_GENERIC 
                or type & alsaseq.SEQ_PORT_TYPE_APPLICATION) and \
                    caps & (alsaseq.SEQ_PORT_CAP_WRITE | alsaseq.SEQ_PORT_CAP_SUBS_WRITE):
                retval.append((clientid, portid, clientname, portname,
                    u"%i:%i %s %s" % (clientid, portid, clientname, portname)))
    return retval

