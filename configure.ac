# GNU Solfege - ear training for GNOME
# Copyright (C) 2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011  Tom Cato Amundsen
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin ST, Fifth Floor, Boston, MA  02110-1301  USA

# Process this file with autoconf to produce a configure script.

AC_INIT([GNU Solfege],[3.23.0],[bug-solfege@gnu.org])
AC_CONFIG_HEADER(config.h)

PACKAGE=solfege
AC_SUBST(PACKAGE)

# We set MAJOR_VERSION AND MINOR_VERSION the the correct version number as
# soon we create a new branch. This because the version numbers are used
# when uploading the user manual to docs.solfege.org
MAJOR_VERSION=3
MINOR_VERSION=23
# ALWAYS set PATCH_LEVEL to bzr-checkout for non-releases.
# Never commit an actual patch level to the bzr repo.
PATCH_LEVEL=git-checkout
# Revision id of the last official release of this branch.
REVISION_ID="rev-id-not-set-no-release"
AC_SUBST(MAJOR_VERSION)
AC_SUBST(MINOR_VERSION)
AC_SUBST(PATCH_LEVEL)
AC_SUBST(REVISION_ID)

VERSION=$MAJOR_VERSION.$MINOR_VERSION.$PATCH_LEVEL
AC_SUBST(VERSION)

AC_PROG_CC

# Remember to update solfege/runtime.py and topdocs/README.texi
# when we change the requried python version.
AM_PATH_PYTHON(2.7)
AM_CHECK_PYTHON_HEADERS(HAVE_PYTHON_H=yes, HAVE_PYTHON_H=no)

AC_PROG_INSTALL
AC_PROG_MAKE_SET

dnl Check for programs

AC_PATH_PROG(SWIG, swig)
AC_SUBST(SWIG)

AC_PATH_PROG(LILYPOND, lilypond)
AC_SUBST(LILYPOND)

AC_PATH_PROG(GIT, git, "notfound")
AC_SUBST(GIT)

AC_PATH_PROG(GS, gs)
AC_SUBST(GS)

AC_PATH_PROG(TXT2MAN, txt2man, "notfound")
AC_SUBST(TXT2MAN)

MY_SWIG_TEST(SWIG_VERSION)
AC_SUBST(SWIG_VERSION)

# This does not get the exact version, just check if we have version 2.10
# or another version.
MY_LILYPOND_TEST(LILYPOND_VERSION)
AC_SUBST(LILYPOND_VERSION)

MY_PATH_PROG(XGETTEXT, xgettext, [You need to install the gettext package.])
MY_PATH_PROG(MSGFMT, msgfmt, [You need to install the gettext package.])
MY_PATH_PROG(MSGMERGE, msgmerge, [You need to install the gettext package.])
MY_PATH_PROG(MSGGREP, msggrep, [You need the gettext package package.])
MY_PATH_PROG(MAKEINFO, makeinfo [You need to install the texinfo package.])
MY_PATH_PROG(SED, sed)
MY_PATH_PROG(CAT, cat)

# FIXME we had to comment out this to run on win32
# PKG_PROG_PKG_CONFIG(0.17.0)

# Remember to update solfege/runtime.py and topdocs/README.texi when
# we change the minimum version of pygtk.

# FIXME we had to comment out this to run on win32
# PKG_CHECK_MODULES(XML2PO, xml2po >= 0.4)
AC_PATH_PROG(XML2PO, xml2po)
AC_SUBST(XML2PO)

AC_PATH_PROG(XSLTPROC, xsltproc)
AC_SUBST(XSLTPROC)

AC_ARG_ENABLE(docbook-stylesheet,
   AC_HELP_STRING([--enable-docbook-stylesheet=PATH],
   [PATH is filename including full path to the html/chunk.xsl
    stylesheet.]),
  [STYLESHEET=$enableval],
  [STYLESHEET=/usr/share/sgml/docbook/stylesheet/xsl/nwalsh/html/chunk.xsl])

AC_CHECK_FILE($STYLESHEET, HAVE_STYLESHEET=yes, HAVE_STYLESHEET=no)
AC_SUBST(STYLESHEET)
AC_SUBST(HAVE_STYLESHEET)

AC_CHECK_HEADER(sys/soundcard.h, HAVE_SOUNDCARD_H=yes, HAVE_SOUNDCARD_H=no)
AC_SUBST(HAVE_SOUNDCARD_H)

AC_ARG_ENABLE(oss-sound, AC_HELP_STRING([--disable-oss-sound],
    [Do not build module for OSS sound. Use this if you OS don't support OSS]),
    [ENABLE_OSS_SOUND=$enableval],
    [ENABLE_OSS_SOUND=$HAVE_SOUNDCARD_H])
AC_SUBST(ENABLE_OSS_SOUND)

if test $HAVE_SOUNDCARD_H = "no"; then
  if test $ENABLE_OSS_SOUND = "yes"; then
      AC_MSG_ERROR([Cannot find sys/soundcard.h
                  --enable-oss-sound require sys/soundcard.h])
  fi
fi

AC_ARG_ENABLE(winmidi, AC_HELP_STRING([--enable-winmidi],
    [Build the winmidi.pyd module. This is required to get sound on MS Windows.]),
    [ENABLE_WINMIDI=$enableval],
    [ENABLE_WINMIDI=no])
AC_SUBST(ENABLE_WINMIDI)

AC_ARG_ENABLE(tuner, AC_HELP_STRING([--enable-tuner],
    [the microphone experiment (default: disable). This code is dead, it
     does not work.]),
    [ENABLE_TUNER=$enableval],
    [ENABLE_TUNER=no])
AC_SUBST(ENABLE_TUNER)

dnl Checks for libraries.
if test "x$ENABLE_TUNER" = xyes; then
    AC_DEFINE(ENABLE_TUNER)
    AC_CHECK_LIB(rfftw, rfftw, [
        AC_DEFINE(HAVE_FFTW)
        LIBS="$LIBS -lfftw -lrfftw"], ,-lfftw)
fi

dnl Checks for header files.
AC_HEADER_STDC
AC_CHECK_HEADERS(fcntl.h sys/ioctl.h unistd.h)

if test "x$ENABLE_OSS_SOUND" = xyes; then
  if test "x$HAVE_PYTHON_H" = xno; then
        AC_MSG_ERROR([
*** We need the python header files to build the OSS sound module.
*** The debian package is called python-dev, other distributions
*** probably have a similar name.])
  fi
fi

dnl Checks for typedefs, structures, and compiler characteristics.
AC_C_CONST

dnl Checks for library functions.
AC_PROG_GCC_TRADITIONAL
#AC_CONFIG_FILES

AC_CONFIG_FILES([
	 run-solfege.py solfege/buildinfo.py
         topdocs/defs.texi
         windowsinstaller.iss
         Makefile
         autopackage/default.apspec
         help/C/solfege.xml
         ])
AC_OUTPUT

AC_MSG_NOTICE
AC_MSG_NOTICE([Please remember to rerun configure if you change swig versions!])
if test -z "$XML2PO"; then
AC_MSG_NOTICE
AC_MSG_NOTICE([xml2po was not found. This is no big deal, but it mean that the])
AC_MSG_NOTICE([translated user manuals will not be updated if you make changes])
AC_MSG_NOTICE([to the english manual.])
fi
