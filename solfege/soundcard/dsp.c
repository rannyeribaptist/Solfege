/*
 * dsp.c: oss interface
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

#include <string.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <sys/soundcard.h>
#include "dsp.h"
#include "calc.h"
#include "xmalloc.h"
#include "gate.h"

_dsp_control   _ctrl = { "/dev/dsp", NULL, -1, 0, RECORD_MODE, 1, DRIVER_FRAGS,
	512, U8, 1, 32768, 0, 0, 0, 0 };

struct t_config {
	unsigned int	srate;
	unsigned long	fft_points;
	short		mode;
	unsigned int	noise_gate;
	unsigned long	freq_gate;
};

typedef struct t_config t_config;

t_config _config = { 44100, 32768, HARM_COUNT, 5, 41 };

int		_first_loop = -1;
unsigned char 	*audiobuf = NULL;
unsigned char	 *fftbuf = NULL;



int	_dsp_setfmt		( int *ufmt );
int	_dsp_setchn		( int *uchn );
int	_dsp_setsrate		( int *urate );
int	_dsp_setbuffering	( int size, int num );
int	_dsp_init		( void );
int	_dsp_getobuffer		( audio_buf_info *info );
int	_dsp_getibuffer		( audio_buf_info *info );

_dsp_control	defaults = { "/dev/dsp", NULL, -1, 4096, DUPLEX_MODE, 
	0, 0, 0, U8, 1, 8000, 0, 0, 0, 0 };
_dsp_control	*dev = NULL;


int
dsp_open( _dsp_control *udev )
{
	audio_buf_info info;
	int flags;

	if( udev == NULL ) {
		dev = &defaults;
	} else {
		dev = udev;
		dev->fd = -1;
	}
	if( ( dev->fd = open( dev->dev_name, dev->o_mode | O_NONBLOCK ) ) == -1 ) {
		return -1;
	}
	if( ( flags = fcntl( dev->fd, F_GETFL ) ) == -1 )
		return -1;
	if( ( fcntl( dev->fd, F_SETFL, flags & ~O_NONBLOCK ) ) == -1 )
		return -1;

	if( _dsp_init() == -1 ) {
		dsp_close();
		return -1;
	}

	switch( dev->o_mode ) {
		case RECORD_MODE: if( _dsp_getibuffer( &info ) == -1 ) {
					dsp_close();
					return -1;
				}
				break;

		default: if( _dsp_getobuffer( &info ) == -1 ) {
					dsp_close();
					return -1;
				}
				break;
	}

	dev->frags = info.fragstotal;
	dev->fragsize = info.fragsize;
	if( dev->buf_size == 0 || dev->set_buf_parms == 1 )
		dev->buf_size = info.fragsize;

	return 0;
}

void
dsp_close( void )
{
	close( dev->fd );
	dev->fd = -1;
}

int
_dsp_setfmt( int *ufmt )
{
	if( ioctl( dev->fd, SNDCTL_DSP_SETFMT, ufmt ) == -1 )
		return -1;

	dev->fmt = *ufmt;

	return 0;
}

int
_dsp_setchn( int *uchn )
{
	if( ioctl( dev->fd, SNDCTL_DSP_CHANNELS, uchn ) == -1 )
		return -1;

	dev->chn = *uchn;

	return 0;
}

int
_dsp_setsrate( int *urate )
{
	if ( ioctl( dev->fd, SNDCTL_DSP_SPEED, urate ) == -1 )
		return -1;

	dev->srate = *urate;

	return 0;
}

int
_dsp_setbuffering( int size, int num )
{
	int arg = (num&0xffff) << 16, exp = 0;

	while( size > 1 ) {
		size >>= 1;
		exp++;
	}

	arg |= (exp&0xffff);
	if ( ioctl( dev->fd, SNDCTL_DSP_SETFRAGMENT, &arg ) == -1 )
		return -1;

	return 0;
}

int
_dsp_init( void )
{	
	if( _dsp_setfmt( &dev->fmt ) == -1 )
		return -1;
	if( _dsp_setchn( &dev->chn ) == -1 )
		return -1;
	if( _dsp_setsrate( &dev->srate ) == -1 )
		return -1;
	if( dev->set_buf_parms == 1 )
		if( _dsp_setbuffering( dev->fragsize, dev->frags ) == -1 )
			return -1;

	return 0;
}

int
dsp_playback( unsigned char *data, unsigned long size )
{
	int blk, nblocks = size / dev->buf_size,
		carrier = size % dev->buf_size;

	dev->ptr = data;
	for( blk = 0; blk <= nblocks; blk++ ) {
		if( blk != nblocks ) {
			if( write( dev->fd, dev->ptr, dev->buf_size ) == -1 )
				return -1;
		} else
			write( dev->fd, dev->ptr, carrier );
		dev->ptr = dev->ptr + dev->buf_size;
	}

	return 0;
}

int
dsp_record( unsigned char *data, unsigned long size )
{
	int blk, nblocks = size / dev->buf_size,
		carrier = size % dev->buf_size;

	dev->ptr = data;
	for( blk = 0; blk <= nblocks; blk++ ) {
		if( blk != nblocks ) {
			if( read( dev->fd, dev->ptr, dev->buf_size ) == -1 )
				return -1;
		} else
			read( dev->fd, dev->ptr, carrier );
		dev->ptr = dev->ptr + dev->buf_size;
	}

	return 0;
}

int
dsp_sync( void )
{
	if( ioctl( dev->fd, SNDCTL_DSP_SYNC, 0 ) == -1 )
		return -1;

	return 0;	
}

int
dsp_reset( void )
{
	if( ioctl( dev->fd, SNDCTL_DSP_RESET, 0 ) == -1 )
		return -1;

	return 0;	
}

int
_dsp_getobuffer( audio_buf_info *info )
{
	if( ioctl( dev->fd, SNDCTL_DSP_GETOSPACE, info ) == -1 )
		return -1;

	return 0;
}

int
_dsp_getibuffer( audio_buf_info *info )
{
	if( ioctl( dev->fd, SNDCTL_DSP_GETISPACE, info ) == -1 )
		return -1;

	return 0;
}

int
dsp_avail( void )
{
	audio_buf_info info;

	if( dev->o_mode==PLAYBACK_MODE || dev->o_mode==DUPLEX_MODE ) {
		if( _dsp_getobuffer( &info ) == -1 )
			return -1;

		dev->ofrags = info.fragments;
		dev->obytes = info.bytes;
	}

	if( dev->o_mode==RECORD_MODE || dev->o_mode==DUPLEX_MODE ) {
		if( _dsp_getibuffer( &info ) == -1 )
			return -1;

		dev->ifrags = info.fragments;
		dev->ibytes = info.bytes;
	}

	return 0;
}
    
int
dsp_open_record()
{
  _ctrl.srate = _config.srate;
  _ctrl.o_mode = RECORD_MODE;
  if (dsp_open(&_ctrl) == -1) {
    printf("Error opening dsp\n");
    return -1;
  }
  audiobuf = (char*) xmalloc( sizeof( char ) * _ctrl.buf_size * _ctrl.frags );
  fftbuf = (char*) xmalloc( sizeof( char ) * _config.fft_points );
  _first_loop = 1;
  return 0;
}
float
idle_loop()
{
	double f;
	long bread;

	if( !_first_loop ) {
		if( dsp_avail() == -1 ) {
			printf("dsp_avail failed.\n");
			return -1;
		}
		if( _ctrl.ibytes == 0 || _ctrl.ifrags == _ctrl.frags ) {
			printf("Timed Out\n");
			_first_loop = 1;
			return -1;
		}
		bread = 512*_ctrl.ifrags;
		if( dsp_record( audiobuf, bread ) == -1 ) {
			printf("Error reading from audio device\n");
			return -1;
		}
		noise_gate_U8( audiobuf, bread, _ctrl.srate, _config.noise_gate, 5, 5, 5 );
		if( bread < _config.fft_points ) {
			memmove( fftbuf, fftbuf + bread, _config.fft_points - bread );
			memcpy( fftbuf + _config.fft_points - bread, audiobuf, bread );
		} else {
			memcpy( fftbuf, audiobuf + bread - _config.fft_points, _config.fft_points ); 
		}
	} else {
		if( dsp_record( fftbuf, _config.fft_points ) == -1 ) {
			printf("Error reading from audio device\n");
			return -1;
		}
		noise_gate_U8( fftbuf, _config.fft_points, _ctrl.srate,_config.noise_gate,5,5,5 );
		_first_loop = 0;
	}
	f = calc_freq( fftbuf, _config.fft_points, _ctrl.srate, _config.mode, BYTE );
	if( f < _config.freq_gate )
		f = 1;
        return f;
}


