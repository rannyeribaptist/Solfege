# vim: set noexpandtab:
#
# GNU Solfege - free ear training software
# Copyright (C) 2000, 2001, 2002, 2003, 2004, 2007, 2008, 2011  Tom Cato Amundsen
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

installfiles += $(wildcard solfege/soundcard/*.py)
dist_files += solfege/soundcard/Makefile \
	$(wildcard solfege/soundcard/*.py) \
	$(wildcard solfege/soundcard/*.c solfege/soundcard/*.i solfege/soundcard/*.h) \
	solfege/soundcard/winmidi.dsp solfege/soundcard/winmidi.dsw solfege/soundcard/winmidi.def \
	$(wildcard solfege/soundcard/tests/*.py)

CFLAGS:=$(CFLAGS) -I/usr/src/linux/include -Wall -pedantic -fPIC -I.
CC:=$(CC) $(CFLAGS) -DHAVE_CONFIG_H 

ifeq ($(ENABLE_OSS_SOUND),yes)
 ifdef SWIG
  ifeq ($(SWIG_VERSION),1.1)
   TARGETS += solfege/soundcard/solfege_c_midimodule.so
  else
   TARGETS += solfege/soundcard/_solfege_c_midi.so
  endif
 endif
endif

OBJECTS = solfege/soundcard/macro_to_function.o \
	solfege/soundcard/solfege_c_midi.o \
	solfege/soundcard/solfege_c_midi_wrap.o

ifeq ($(ENABLE_TUNER),yes)
OBJECTS += solfege/soundcard/fft.o \
           solfege/soundcard/dsp.o \
		   solfege/soundcard/gate.o \
		   solfege/soundcard/calc.o \
		   solfege/soundcard/xmalloc.o
LDFLAGS += -lm -lrfftw -lfftw
endif

solfege/soundcard/solfege_c_midimodule.so: $(OBJECTS)
	$(CC) $(LDFLAGS) -fPIC -shared $(OBJECTS) -o $@ -lc

solfege/soundcard/_solfege_c_midi.so: $(OBJECTS)
	$(CC) $(LDFLAGS) -fPIC -shared $(OBJECTS) -o $@ -lc 

solfege/soundcard/solfege_c_midi_wrap.o: solfege/soundcard/solfege_c_midi_wrap.c solfege/soundcard/solfege_c_midi.i
	(cd solfege/soundcard; $(CC) $(CFLAGS) -c solfege_c_midi_wrap.c $(PYTHON_INCLUDES))

solfege/soundcard/solfege_c_midi_wrap.c: solfege/soundcard/solfege_c_midi.c solfege/soundcard/macro_to_function.c solfege/soundcard/solfege_c_midi.i
	(cd solfege/soundcard; $(SWIG) -python solfege_c_midi.i)

# win32

ifeq ($(ENABLE_WINMIDI),yes)
TARGETS += solfege/soundcard/winmidi.pyd
endif

DLLWRAP=dllwrap

%/winmidi.pyd: %/winmidi.o
	$(DLLWRAP) --dllname=$@ --def=solfege/soundcard/winmidi.def $< -o $@ -s --entry=_DllMain@12 -L/usr/i586-mingw32msvc/lib/ -lwinmm $(PYTHONDLL)

%/winmidi.o: %/winmidi.c
	$(CC) $(CFLAGS) $(PYTHON_INCLUDES) -c $< -o $@

# end win32

install-soundcard:
ifeq ($(ENABLE_OSS_SOUND),yes)
	mkdir -p $(DESTDIR)/$(libdir)/$(PACKAGE)
ifdef SWIG
  ifeq ($(SWIG_VERSION),1.1)
	$(INSTALL_DATA) solfege/soundcard/solfege_c_midimodule.so $(DESTDIR)/$(libdir)/$(PACKAGE)/
  else
	$(INSTALL_DATA) solfege/soundcard/_solfege_c_midi.so $(DESTDIR)/$(libdir)/$(PACKAGE)/
  endif
endif
endif

uninstall-soundcard:
ifdef SWIG
  ifeq ($(SWIG_VERSION),1.1)
	rm -f $(DESTDIR)/$(libdir)/$(PACKAGE)/solfege_c_midimodule.so
  else
	rm -f $(DESTDIR)/$(libdir)/$(PACKAGE)/_solfege_c_midi.so
  endif
endif
	rmdir $(DESTDIR)/$(libdir)/$(PACKAGE) || true
	rmdir $(DESTDIR)/$(libdir)/$(PACKAGE) || true

clean-files += \
	$(wildcard solfege/soundcard/*.o \
               solfege/soundcard/*.so \
               solfege/soundcard/*.py[cdo] \
               solfege/soundcard/tests/*.py[co])

distclean-files += solfege/soundcard/solfege_c_midi_wrap.c
