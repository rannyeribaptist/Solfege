#!/usr/bin/python
"""
This script demonstrates a bug or something I don't understand about
the old OSS (not 4.1). 
"""

import sys, os
if os.getcwdu()[-4:] == "test":
    sys.path.insert(0, "..")
else:
    sys.path.insert(0, ".")
import src.i18n
src.i18n.setup(".", "C")
import soundcard
soundcard.initialise_devicefile("/dev/sequencer2", 2)
s = soundcard.solfege_c_midi

devnum = soundcard.synth.m_devnum
s.seq_start_timer()
for x in range(16):
    s.seq_set_patch(devnum, x, 48)

# these two lines are necessary to make the first tone stop.
# another solution is to use channel 0 for the first note and
# channel 1 for the second. Not that this i big deal, but it
# is not mentioned in any documentation I have read.

#s.seq_start_note(devnum, 0, 60, 90)
#s.seq_stop_note(devnum, 0, 60, 90)

s.seq_start_note(devnum, 1, 60, 90)
s.seq_delta_time(100)
s.seq_stop_note(devnum, 1, 60, 90)

s.seq_start_note(devnum, 0, 61, 90)
s.seq_delta_time(100)
s.seq_stop_note(devnum, 0, 61, 90)

s.seq_start_note(devnum, 0, 62, 90)
s.seq_delta_time(100)
s.seq_stop_note(devnum, 0, 62, 90)


s.seqbuf_dump()

import sys
print "press ENTER to continue"
sys.stdin.readline()
soundcard.synth.close()
