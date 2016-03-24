#!/bin/bash

DIST=build
PYGI=/C/mygi
PYVER=27

setup() {
  rm $DIST -rf
  mkdir $DIST
  cp -a /C/mypython27/* $DIST/
}
trim() {
	cd $DIST
	rm -rf Doc
	rm -rf tcl
	rm -rf Tools
	rm -rf include
	rm -rf Lib/bsddb
	rm -rf Lib/compiler
	rm -rf Lib/distutils
	rm -rf Lib/email
	rm -rf Lib/importlib
	rm -rf Lib/lib2to3
	rm -rf Lib/lib-tk
	rm -rf Lib/hotshot
	rm -rf Lib/idlelib
	rm -rf Lib/json
	rm -rf Lib/msilib
	rm -rf Lib/pydoc_data
	rm -rf Lib/test
	rm -rf Lib/wsgiref
	rm -rf Lib/curses
	rm -rf Lib/unittest
	mkdir Python.txt
	mv LICENSE.txt README.txt NEWS.txt Python.txt
	rm python-2.7.2.msi
	rm -rf Lib/site-packages/gtk/share/dbus-1
	rm -rf Lib/site-packages/gtk/share/devhelp
	rm -rf Lib/site-packages/gtk/share/enchant
	rm -rf Lib/site-packages/gtk/share/gedit
	rm -rf Lib/site-packages/gtk/share/glade
	rm -rf Lib/site-packages/gtk/share/gtksourceview-3.0
	rm -rf Lib/site-packages/gtk/share/gtranslator
	rm -rf Lib/site-packages/gtk/share/telepathy
	cd ..
}
copy_mygi() {
	cp -a $PYGI/py$PYVER/* $DIST/Lib/site-packages/
	cp -a $PYGI/gtk $DIST/Lib/site-packages/
}
setup
copy_mygi
trim
make winbuild
mv AUTHORS.txt COPYING.txt FAQ.txt INSTALL.txt INSTALL.win32.txt README.txt $DIST
make DESTDIR=$DIST prefix="" install
cp solfege/soundcard/winmidi.pyd $DIST/share/solfege/solfege/soundcard
cp win32-start-solfege.pyw $DIST/bin/
cp debugsolfege.bat $DIST/bin
echo "done!"
