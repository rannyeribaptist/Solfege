/* GNU Solfege - ear training for GNOME
 * Copyright (C) 2000, 2001, 2002, 2003, 2004  Tom Cato Amundsen
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin ST, Fifth Floor, Boston, MA  02110-1301  USA
 *
 */

#include <stdlib.h>
#include <stdio.h>  
#include <unistd.h>  
#include <fcntl.h>  
#include <string.h>
#include <sys/ioctl.h> /* for writing to the device */
#include <sys/soundcard.h> /* the soundcard macro definitions */
#include <assert.h>

int seqfd = -1;		/* file descriptor for /dev/sequencer */
SEQ_DEFINEBUF(2048);

void seqbuf_dump()	/* the MIDI messages get dumped here */
{
  assert(seqfd != -1);
  if (_seqbufptr)
    if (write (seqfd, _seqbuf, _seqbufptr) == -1) 
      perror("solfege_c_midi.seqbuf_dump.Can't write to MIDI device");   
  _seqbufptr = 0;
}

int sndctl_seq_nrsynths()
{
  int n;
  if (ioctl(seqfd, SNDCTL_SEQ_NRSYNTHS, &n) == -1) {
    perror("solfege_c_midi.sndctl_seq_nrsynth");
    return -1;
  }
  return n;
}

/* return 1 if successful, 0 if fail */
int sndctl_seq_reset()
{
/*  printf("sndctl_seq_reset\n");*/
  if (ioctl(seqfd, SNDCTL_SEQ_RESET) != 0) {
    perror("solfege_c_midi.sndctl_seq_reset");
    return 0; 
  }
  return 1;
}

/*
 * This function should only be used with
 * /dev/music (aka /dev/sequencer2), it will
 * fail if used with /dev/sequencer
 */
void sndctl_tmr_timebase(int timebase)
 {
  if (ioctl(seqfd, SNDCTL_TMR_TIMEBASE, &timebase)==-1)
   { 
    perror("solfege_c_midi.sndctl_tmr_timebase");
   }
 }

/*
 * This function should only be used with
 * /dev/music (aka /dev/sequencer2), it will
 * fail if used with /dev/sequencer
 */
void sndctl_tmr_tempo(int tempo)
 {
  if (ioctl(seqfd, SNDCTL_TMR_TEMPO, &tempo)==-1)
   {
    perror("solfege_c_midi.sndctl_tmr_tempo");
   }
 }

int sndctl_seq_gettime()
 {
  int i;
  if (ioctl(seqfd, SNDCTL_SEQ_GETTIME, &i)==-1)
    {
      perror("solfege_c_midi.sndctl_seq_gettime");
      exit(-1);
    }
  return i;
 }

/* ugh: Find out if swig takes care of freeing the return value */
static char _tmpbuf[100];

char * get_synth_name(int i)
{
  struct synth_info si;
  si.device = i;
  if (ioctl(seqfd, SNDCTL_SYNTH_INFO, &si) == -1) {
    perror("solfege_c_midi.get_synth_name");
    exit(-1);
  }
  strncpy(_tmpbuf, si.name, 99);
  return _tmpbuf;
}

int get_synth_nr_voices(int i)
{
  struct synth_info si;
  si.device = i;
  if (ioctl(seqfd, SNDCTL_SYNTH_INFO, &si) == -1) {
    perror("solfege_c_midi.get_synth_nr_voices");
    return -1;
  }
  return si.nr_voices;
}

