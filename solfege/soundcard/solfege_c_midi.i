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
 * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
 *
 */

%module solfege_c_midi
%include "../../config.h"
%{
#include "macro_to_function.h"
extern int seqfd;
void seqbuf_dump();
int sndctl_seq_nrsynths();
int sndctl_seq_reset();
void sndctl_tmr_timebase(int);
void sndctl_tmr_tempo(int);
int sndctl_seq_gettime();
char * get_synth_name(int i);
int get_synth_nr_voices(int i);

%}

/* defined in macro_to_function.c */
extern void seq_bender(int devnum, int chan, int value);
extern void seq_start_note(int devnum, int chan, int tone, int vel);
extern void seq_stop_note (int devnum, int chan, int note, int vel);
extern void seq_set_patch (int devnum, int chan, int p);
extern void seq_set_volume (int devnum, int chan, int volume);
extern void seq_delta_time(int ticks);
extern void seq_start_timer();

extern int errno;

/* Defined in solfege_c_midi.c */
extern int seqfd;
extern void seqbuf_dump();
extern int sndctl_seq_nrsynths();
extern int sndctl_seq_reset();
extern void sndctl_tmr_timebase(int);
extern void sndctl_tmr_tempo(int);
extern int sndctl_seq_gettime();
extern char * get_synth_name(int i);
extern int get_synth_nr_voices(int i);

/* All the dsp stuff */
#if defined(ENABLE_TUNER)
extern int dsp_open_record();
extern void dsp_close();
extern float idle_loop();
#endif /*ENABLE_TUNER*/
