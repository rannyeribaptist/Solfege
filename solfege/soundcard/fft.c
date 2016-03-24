/* 
 * fft.c: fft and frequency calculation.
 * Copyright (C) 1999 Richard Boulton <richard@tartarus.org>
 * Convolution stuff by Ralph Loader <suckfish@ihug.co.nz>
 *
 * August 2000: almost completely rewritten by Fabio Checconi <fchecconi@libero.it>
 *	( see src/fft.old.c for the original one, used by xmms-0.9.5.1 ).
 *
 *  This program is free software; you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation; either version 2 of the License, or
 *  (at your option) any later version.
 *
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with this program; if not, write to the Free Software
 *  Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
 */

#ifdef HAVE_CONFIG_H
#include <config.h>
#endif
#ifdef HAVE_FFTW
#include <rfftw.h>
#endif

#include <stdlib.h>
#include <math.h>
#include "xmalloc.h"
#include "fft.h"

#ifdef M_PI
#define PI	M_PI
#else
#define PI	3.14159265358979323846
#endif

unsigned long nn = 0;
double *window = NULL;

int 	_fft_init 		( unsigned long points );

#ifndef HAVE_FFTW

int	_fft_reverse_bits  	( unsigned int initial );
void 	_fft_calculate   	( void );

double *rout = NULL, *iout = NULL, *costable = NULL, *sintable = NULL;
unsigned long lognn;

int *bit_reverse = NULL;

#else

int have_plan = 0;
fftw_real *rin = NULL, *rout = NULL;
rfftw_plan p;

#endif

#ifndef HAVE_FFTW

int
_fft_reverse_bits( unsigned int initial )
{
	unsigned int reversed = 0, loop;

	for( loop = 0; loop < lognn; loop++) {
		reversed <<= 1;
		reversed += (initial & 1);
		initial >>= 1;
	}

	return reversed;
}

void 
_fft_calculate( void )
{
	unsigned int i, j, k;
	unsigned int exchanges;
	float fact_real, fact_imag;
	float tmp_real, tmp_imag;
	unsigned int factfact;
    
	exchanges = 1;
	factfact = nn / 2;

	for( i = lognn; i != 0; i-- ) {
		for( j = 0; j != exchanges; j++ ) {
			fact_real = costable[j * factfact];
	 		fact_imag = sintable[j * factfact];
	    
	  		for( k = j; k < nn; k += exchanges << 1) {
				int k1 = k + exchanges;
				tmp_real = fact_real * rout[k1] - fact_imag * iout[k1];
				tmp_imag = fact_real * iout[k1] + fact_imag * rout[k1];
				rout[k1] = rout[k] - tmp_real;
				iout[k1] = iout[k] - tmp_imag;
				rout[k]  += tmp_real;
				iout[k]  += tmp_imag;
			}
		}
		exchanges <<= 1;
		factfact >>= 1;
	}
}

#define __fft_calculate _fft_calculate();

#else

#define __fft_calculate rfftw_one( p, rin, rout );

#endif

int
_fft_init( unsigned long points )
{
	long c;
#ifndef HAVE_FFTW

	unsigned int i = points, k = 1;
	float j;

	while( i > 2 ) {
		if( i & 0x0001 )
			return -1;
		i >>= 1;
		k++;
	}

	nn = points;
	lognn = k;

	if( iout != NULL )
		free( iout );
	if( rout != NULL )
		free( rout );
	if( sintable != NULL )
		free( sintable );
	if( costable != NULL )
		free( costable );
	if( bit_reverse != NULL )
		free( bit_reverse );

	bit_reverse = (int*) xmalloc( sizeof( int ) * nn );
	costable = (double*) xmalloc( sizeof( double ) * nn / 2 );
	sintable = (double*) xmalloc( sizeof( double ) * nn / 2 );

	rout = (double*) xmalloc ( sizeof( double ) * nn );
	iout = (double*) xmalloc ( sizeof( double ) * nn );

	for( i = 0; i < nn; i++ ) {
		bit_reverse[i] = _fft_reverse_bits( i );
	}
	
	for( i = 0; i < nn / 2; i++ ) {
		j = 2 * PI * i / nn;
		costable[i] = cos( j );
		sintable[i] = sin( j );
   	}

#else

	nn = points;

	if( rout )
		free( rout );
	if( rin )
		free( rin );
	if( have_plan )
		rfftw_destroy_plan( p );

	rin = (fftw_real*) xmalloc( sizeof( fftw_real ) * nn );
	rout = (fftw_real*) xmalloc( sizeof( fftw_real ) * nn );

	p = rfftw_create_plan( nn, FFTW_REAL_TO_COMPLEX, FFTW_ESTIMATE );
	have_plan = 1;

#endif

	if( window )
		free( window );

	window = (double*) xmalloc( sizeof( double ) * nn );
	for ( c = 0; c < nn / 2; c++ )
		window[c] = window[nn - c - 1] = 0.54 - 0.46 * cos( 2 * PI * c / nn );

	return 0;
}

int
fft( void *snd_sample, unsigned long size, double *outbuf, int typ )
{
	unsigned long n;

	if( nn != size ) {
		if( _fft_init( size ) != 0 )
			return -1;
	}

	if( typ == BYTE ) {
		for( n = 0; n < nn; n++ ) {
#ifndef HAVE_FFTW
			rout[bit_reverse[n]] = (((unsigned char*)snd_sample)[n] - 128) * window[n];
			iout[bit_reverse[n]] = 0;
#else
			rin[n] = (((unsigned char*)snd_sample)[n] - 128) * window[n];
#endif
		}
	} else {
		for( n = 0; n < nn; n++ ) {
#ifndef HAVE_FFTW
			rout[bit_reverse[n]] = ((unsigned int*)snd_sample)[n];
			iout[bit_reverse[n]] = 0;
#else
			rin[n] = ((int*)snd_sample)[n];
#endif
		}
	}

	__fft_calculate;

	for( n = 0; n < size / 2; n ++ )
#ifndef HAVE_FFTW
		outbuf[n] = rout[n] * rout[n] + iout[n] * iout[n];
#else
		outbuf[n] = rout[n] * rout[n] + rout[size - n] * rout[size - n];
#endif

	return 0;
}
