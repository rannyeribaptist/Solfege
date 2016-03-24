/*
 * oss.h
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

#ifndef _DSP_H
#define _DSP_H

#include <fcntl.h>
#include <sys/soundcard.h>

#define PLAYBACK_MODE		O_WRONLY
#define RECORD_MODE		O_RDONLY
#define DUPLEX_MODE		O_RDWR

#define MU_LAW			AFMT_MU_LAW
#define A_LAW			AFMT_A_LAW
#define IMA_ADPCM		AFMT_IMA_ADPCM
#define U8			AFMT_U8
#define S8			AFMT_S8
#define S16_LE			AFMT_S16_LE
#define S16_BE			AFMT_S16_BE
#define S16			AFMT_S16_NE
#define S32_LE			AFMT_S32_LE
#define S32_BE			AFMT_S32_BE
#define U16_LE			AFMT_U16_LE
#define U16_BE			AFMT_U16_BE
#define MPEG			AFMT_MPEG

#define DRIVER_FRAGS		0x7fff

struct _dsp_control {
		char 		*dev_name;
		unsigned char 	*ptr;

		int 		fd;
		int 		buf_size;
		int 		o_mode;

		short		set_buf_parms;
		int		frags;
		int		fragsize;

		int		fmt;
		int		chn;
		int		srate;

		int		ofrags;
		int		obytes;
		int		ifrags;
		int		ibytes;
};

typedef struct 	_dsp_control 	_dsp_control;

		int		dsp_open		( _dsp_control *udev );
		void		dsp_close		( void );

		int		dsp_playback		( unsigned char *data, unsigned long size );
		int		dsp_record		( unsigned char *data, unsigned long size );

		int		dsp_sync		( void );
		int		dsp_reset		( void );

		int		dsp_avail		( void );

int dsp_open_record();
float idle_loop ( void );
                
extern _dsp_control _ctrl;

#endif
