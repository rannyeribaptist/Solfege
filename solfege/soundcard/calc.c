/*
 * calc.c
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

#include <math.h>
#include <stdlib.h>
#include "calc.h"
#include "xmalloc.h"

#define FACT_3RD	1.259921050
#define FACT_5TH	1.498307077

#define IFACT		1000

#define MAX_PEAKS	20

struct	_calc_peak {
	int index;
	double amp;
	int	is_ma;
	int harms;
};

typedef struct _calc_peak _calc_peak;

_calc_peak *list = NULL;
double *outbuf = NULL;
unsigned long outbuf_size = 0;

int 	_calc_compare_peaks_A	( const void *p1, const void *p2 );
int 	_calc_compare_peaks_I	( const void *p1, const void *p2 );
int	_calc_is_peak 		( int i, double *data );
int	_calc_peak_in_range	( int a, int b, double *data );
void	_calc_init_peak_list	( _calc_peak *list );
void	_calc_peak_add		( int i, double *data, _calc_peak *list );

int
_calc_compare_peaks_A( const void *p1, const void *p2 )
{
	if( ((_calc_peak *) p1)->amp > ((_calc_peak *) p2)->amp )
		return 1;
	else if( ((_calc_peak *) p1)->amp == ((_calc_peak *) p2)->amp )
		return 0;
	return -1;
}

int
_calc_compare_peaks_I( const void *p1, const void *p2 )
{
	if( ((_calc_peak *) p1)->index > ((_calc_peak *) p2)->index )
		return 1;
	else if( ((_calc_peak *) p1)->index == ((_calc_peak *) p2)->index )
		return 0;
	return -1;
}

int
_calc_is_peak( int i, double *data )
{
	if( data[i] > data[i-1] && data[i] > data[i+1] )
		return 1;
	else
		return 0;
}

int
_calc_peak_in_range( int a, int b, double *data )
{
	int i;
	for( i = a; i <= b; i++ )
		if( _calc_is_peak( i, data ) )
			return i;

	return 0;
}

void
_calc_init_peak_list( _calc_peak *list )
{
	int i;

	for( i = 0; i < MAX_PEAKS; i++ ) {
		list[i].index = 0;
		list[i].amp = 0;
		list[i].is_ma = 0;
		list[i].harms = 0;
	}
}

void
_calc_peak_add( int i, double *data, _calc_peak *list )
{
	if ( data[i] > list[0].amp ) {
		list[0].index = i;
		list[0].amp = data[i];
		qsort( list, MAX_PEAKS, sizeof( _calc_peak ),
			_calc_compare_peaks_A );
	}
}

void
calc_init( unsigned long size )
{
	if( !list ) {
		list = (_calc_peak *) xmalloc( sizeof( _calc_peak ) * MAX_PEAKS );
	}
	outbuf_size = NEED_BUF( size );
	if( outbuf )
		free( outbuf );
	outbuf = (double *) xmalloc( sizeof( double ) * outbuf_size );
}

double
calc_freq( void *snd_sample, unsigned long size, int rate, int mode, int typ )
{
	double kf;
	unsigned long index = 0, i, k, t;
	_calc_peak max = { 0, 0 };

	if( outbuf_size != NEED_BUF( size ) ) {
		calc_init( size );
	}

	if( fft( snd_sample, size, outbuf, typ ) == -1 )
		return 0;

	_calc_init_peak_list( list );
	for( i = 1; i < size / 2; i++ ) {
		if( mode == HARM_COUNT && _calc_is_peak( i, outbuf ) ) {
			_calc_peak_add( i, outbuf, list );
		}
		if( outbuf[i] > max.amp ) {
			max.index = i;
			max.amp = outbuf[i];
		}
	}
	
	if( mode == ABSOLUTE_MAX ) {
		index = max.index;
	}
	
	if( mode == HARM_COUNT ) {
		qsort( list, MAX_PEAKS, sizeof( _calc_peak ),
			_calc_compare_peaks_I );

		for( i = 0; i < MAX_PEAKS; i++ ) {
			if( list[i].index == 0 || list[i].amp < (max.amp / IFACT) )
				continue;

			if( list[i].index == max.index )
				list[i].is_ma = 1;

			for( k = 2 * list[i].index; k < size / 2; k *= 2 ) {
				for( t = i + 1; t < MAX_PEAKS; t++ ) {
					index = list[t].index;
					if( index == max.index )
						list[i].is_ma = 1;
					if( index >= k - 4 && index <= k + 4 ) {
						list[i].harms++;
					}
				}
			}

			kf = FACT_3RD * list[i].index;
			k = (int) kf;
			while( k < size / 2 ) {
				for( t = i + 1; t < MAX_PEAKS; t++ ) {
					index = list[t].index;
					if( index == max.index )
						list[i].is_ma = 1;
					if( index >= k - 4 && index <= k + 4 ) {
						list[i].harms++;
					}
				}
				kf *= 2.0;
				k = (int) kf;
			}

			kf = FACT_5TH * list[i].index;
			k = (int) kf;
			while( k < size / 2 ) {
				for( t = i + 1; t < MAX_PEAKS; t++ ) {
					index = list[t].index;
					if( index == max.index )
						list[i].is_ma = 1;
					if( index >= k - 4 && index <= k + 4 ) {
						list[i].harms++;
					}
				}
				kf *= 2.0;
				k = (int) kf;
			}
		}
		k = 0;
		for( i = 0; i < MAX_PEAKS; i++ ) {
			if( list[i].harms >= k && list[i].is_ma ) {
				index = list[i].index;
				k = list[i].harms;
			}
		}
		if( index == 0 )
			index = max.index;
	}
	
	if( mode == USE_MAX ) {
		k = max.index;
		kf = max.amp / IFACT;

		i = _calc_peak_in_range( k/2 - 2, k/2 + 2, outbuf );
		if( i != 0 && outbuf[i] > kf ) {
			t = _calc_peak_in_range( k*FACT_5TH - 4, k*FACT_5TH + 4, outbuf );
			if( t != 0 && outbuf[t] > kf ) {
				index = i;
				goto done;
			}
		}

		i = _calc_peak_in_range( k/FACT_5TH - 4, k/FACT_5TH + 4, outbuf );
		if( i != 0 && outbuf[i] > kf ) {
			t = _calc_peak_in_range( k/(2*FACT_5TH) - 4, k/(2*FACT_5TH) + 4, outbuf );
			if( t != 0 && outbuf[t] > kf ) {
				index = t;
				goto done;
			}
		}
		index = k;
	}

	done:
	return (double)((double) index * (double) rate / (double) size);
}

void
calc_end( void )
{
	free( outbuf );
	free( list );
	outbuf_size = 0;
	outbuf = NULL;
	list = NULL;
}
