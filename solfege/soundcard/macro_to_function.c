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

/*#define be_verbose 1*/
#include "../../config.h"
#include <sys/soundcard.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/ioctl.h>

extern int _seqbufptr;
extern int _seqbuflen;
extern unsigned char _seqbuf[];
extern int seqfd;

void seq_bender(int devnum, int chan, int value)
{
  SEQ_BENDER(devnum, chan, value);
}

void seq_start_note(int devnum, int chan, int note, int vel)
{
#ifdef be_verbose
  printf("start_note devnum:%i, chan:%i, note:%i, vel:%i\n", 
            devnum, chan, note, vel);
#endif
  SEQ_START_NOTE(devnum, chan, note, vel);
}

void seq_stop_note(int devnum, int chan, int note, int vel)
{
#ifdef be_verbose
  printf("stop_note devnum:%i, chan:%i, note:%i, vel:%i\n", 
            devnum, chan, note, vel);
#endif
  SEQ_STOP_NOTE(devnum, chan, note, vel);
}

void seq_set_patch(int devnum, int chan, int patch)
{
#ifdef be_verbose
  printf("set_patch devnum:%i, chan:%i, patch:%i\n", devnum, chan, patch);
#endif
  SEQ_SET_PATCH(devnum, chan, patch)
}

void seq_set_volume(int devnum, int chan, int vol)
{
   SEQ_CONTROL(devnum, chan, CTL_MAIN_VOLUME, vol);
}


void seq_delta_time(int ticks)
{
#ifdef be_verbose
  printf("delta_time ticks:%i\n", ticks);
#endif
  SEQ_DELTA_TIME(ticks);
}

void seq_start_timer()
{
#ifdef be_verbose
  /*printf("start_timer\n");
   */
#endif
  SEQ_START_TIMER();
}

