#!/usr/bin/python2.3

import sys, os
if os.getcwdu()[-4:] == "test":
    sys.path.insert(0, "..")
else:
    sys.path.insert(0, ".")
import soundcard
soundcard.initialise_devicefile("/dev/sequencer2", 2)

s = soundcard.solfege_c_midi

devnum = soundcard.synth.m_devnum
chan = 0
s.seq_start_timer()
#s.seq_set_patch(devnum, chan, 48)

# these two lines are necessary to make the first tone stop.
#s.seq_start_note(devnum, chan, 60, 90)
#s.seq_stop_note(devnum, chan, 60, 90)

#for i in range(500):
#        s.seq_start_note(devnum, chan, 60 + i % 10, 90)
#        s.seq_delta_time(25)
#        s.seq_stop_note(devnum, chan, 60 + i % 10, 90)
s.seq_set_patch(0, 0, 63)
s.seq_set_patch(0, 1, 63)
for i in range(500):
        s.seq_start_note(devnum, 0, 60 + (i*2) % 10, 90)
        s.seq_delta_time(25)
        s.seq_stop_note(devnum, 0, 60 + (i*2) % 10, 90)
        s.seq_start_note(devnum, 1, 60 + (i*2) % 10 + 1, 90)
        s.seq_delta_time(25)
        s.seq_stop_note(devnum, 1, 60 + (i*2) % 10 + 1, 90)



s.seqbuf_dump()

import sys
print "press ENTER to continue"
sys.stdin.readline()
soundcard.synth.close()
