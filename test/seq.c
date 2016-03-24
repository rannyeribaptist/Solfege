
#define SEQUENCER_DEV "/dev/sequencer2"
#include <linux/soundcard.h>
#include <linux/awe_voice.h>
#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <assert.h>

int devnum = 0;
int seqfd = -1;
SEQ_DEFINEBUF(2048);

void seqbuf_dump()
{
  assert(seqfd != -1);
  if (_seqbufptr)
    if (write (seqfd, _seqbuf, _seqbufptr) == -1) 
      perror("solfege_c_midi.seqbuf_dump.Can't write to MIDI device");   
  _seqbufptr = 0;
}


void seq_reset() {
        ioctl(seqfd, SNDCTL_SEQ_RESET);
        seqbuf_dump();
}
void initialize_sound() {
        if ((seqfd = open(SEQUENCER_DEV, O_WRONLY, 0)) < 0) {
                perror("open" SEQUENCER_DEV);
                exit(-1);
        }
}
void close_sound() {
        close(seqfd);
}

/*
 * This sounds like this om my linux 2.4.0 with sb pnp32 soundcard
 * 1. The first tone starts. 
 * 2. The second tone starts.
 * 3. The second tone stops.
 * 4. The first tone last forever (that is until we close the device)
 *
 * If I use chn 0 on the first and chn 1 on the second note, it works
 * ok. The OSS Programming guide (4front) don't say anywhere that I must
 * use chn 0 before chn 1. What am I missing??
 */
void test1() {
        seq_reset();
        SEQ_START_TIMER();
        SEQ_SET_PATCH(devnum, 0, 58);
        SEQ_SET_PATCH(devnum, 1, 60);

        SEQ_START_NOTE(devnum, 1, 50, 100);
        SEQ_DELTA_TIME(60);
        SEQ_STOP_NOTE(devnum, 1, 50, 100);
        
        SEQ_START_NOTE(devnum, 0, 51, 100);
        SEQ_DELTA_TIME(60);
        SEQ_STOP_NOTE(devnum, 0, 51, 100);
        SEQ_STOP_TIMER();
        SEQ_DUMPBUF();
}

/*
 * The 31 first notes are stopped as they should, but after that, the
 * notes are not stopped by the SEQ_STOP_NOTE macro
 **/
void test2() {
        int i;
        seq_reset();
        SEQ_START_TIMER();
        SEQ_SET_PATCH(devnum, 0, 58);
        SEQ_SET_PATCH(devnum, 1, 66);
        for (i = 30; i < 63 ; i = i + 2) {
                SEQ_START_NOTE(devnum, 0, i, 100);
                SEQ_DELTA_TIME(20);
                SEQ_STOP_NOTE(devnum, 0, i, 100);
                SEQ_START_NOTE(devnum, 1, i + 1, 100);
                SEQ_DELTA_TIME(20);
                SEQ_STOP_NOTE(devnum, 1, i + 1, 100);
        }
        SEQ_DUMPBUF();
}
void test3() {
        seq_reset();
        SEQ_START_TIMER();
        SEQ_SET_PATCH(devnum, 0, 58);
        SEQ_SET_PATCH(devnum, 1, 60);

        SEQ_START_NOTE(devnum, 0, 50, 100);
        SEQ_DELTA_TIME(60);
        SEQ_STOP_NOTE(devnum, 0, 50, 100);
        
        SEQ_START_NOTE(devnum, 0, 51, 100);
        SEQ_START_NOTE(devnum, 1, 51, 100);
        SEQ_DELTA_TIME(60);
        SEQ_STOP_NOTE(devnum, 0, 51, 100);
        SEQ_STOP_NOTE(devnum, 1, 51, 100);
        SEQ_STOP_TIMER();
        SEQ_DUMPBUF();
}


int main() {
        initialize_sound();
        test3();
        sleep(3);
        close_sound();
}
