/*
 * gate.c: simple noise gate
 * Copyright (C) 2000 Fabio Checconi <fchecconi@libero.it>
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
 * Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
 */

#include "gate.h"

void
noise_gate_U8(  unsigned char *data, int len, int rate, int gate_on, int hold_time, int release_time, int attack_time )
{
	int i, is_on = 0, hold = 0, hold_ticks, rel_ticks, att_ticks, dec = 0;
	float fact = 1.0, c_rel, c_att;

	if( gate_on == 0 )
		return;

	hold_ticks = hold_time * rate / 1000;
	rel_ticks = release_time * rate / 1000;
	att_ticks = attack_time * rate / 1000;

	c_rel = 1.0 / rel_ticks;
	c_att = 1.0 / att_ticks;

	for( i = 0; i < len; i++ ) {
		if( data[i] > (128 - gate_on) && data[i] < (128 + gate_on) ) {
			if( !is_on ) {
				hold++;
				if( hold > hold_ticks )
					is_on = dec = 1;
			} else {
				if( dec == 1 ) {
					fact -= c_rel;
					if( fact < 0.0 ) {
						fact = 0;
						dec = 0;
						data[i] = 128;
					} else
						data[i] = 128 + (data[i] - 128) * fact;
				} else
					data[i] = 128;
			}
		} else {
			if( is_on ) {
				fact += c_att;
				if( fact > 1.0 ) {
					fact = 1.0;
					is_on = 0;
				} else
					data[i] = 128 + (data[i] - 128) * fact;
			}
			hold = 0;
		}
	}
}

