#!/bin/sh
set -e

echo "Make sure that there are no whitespace in any directory"
echo "containing the build directory of GNU Solfege. Whitespace"
echo "WILL make things fail"

PYTHON=win32/python/python.exe


buildenv() {
	echo "Running buildenv..."
	if [ ! -f "solfege/solfege.py" ]; then
		echo "Run from the directory below script location."
		exit 10
	fi

	DEPS="deps-dl"
	PYVER="2.7.5"
	PYTHONMSI="python-$PYVER.msi"
	PYGI="pygi-aio-3.4.2rev11.7z"
	PYGIn7="pygi-aio-3.4.2rev11"

	ENVDIR="mypython"

	if [ ! -d "$DEPS" ]; then
	  # Control will enter here if $DIRECTORY doesn't exist.
	  mkdir $DEPS
	fi

	if [ -f "$DEPS/$PYTHONMSI" ]; then
	  echo "Python found."
	else
	  wget http://www.python.org/ftp/python/$PYVER/python-$PYVER.msi -O "$DEPS/$PYTHONMSI"
	fi

	if [ -f "$DEPS/$PYGI" ]; then
	  echo "Pygi-aio found."
	else
	  wget https://osspack32.googlecode.com/files/$PYGI -O "$DEPS/$PYGI" --no-check-certificate 
	fi

	if [ ! -d "$DEPS/$PYGIn7" ]; then
	  echo "Please unpack $PYGI to $DEPS/$PYGIn7/"
	  exit 10
	else
	  echo "$DEPS/$PYGIn7/ is unpacked"
	fi

	echo "Recreating $ENVDIR"
	rm -rf $ENVDIR
	mkdir $ENVDIR

	PDIR="C:\\MinGW\\msys\\1.0\\home\\"$(basename `pwd`)"\\mypython"
	msiexec -a deps-dl\\python-2.7.5.msi TARGETDIR="$PDIR"
	cp -a deps-dl/pygi-aio-3.4.2rev11/py27/* mypython/lib/site-packages/
	cp -a deps-dl/pygi-aio-3.4.2rev11/gtk mypython/lib/site-packages/
}

setup() {
  # Step 1: Prepare the win32 directory. This is required both for
  # running from the source dir, and for the installer.
  rm win32 -rf
  mkdir win32
  cp -a ../mypython win32/python
  #echo '"lib/gtk-2.0/2.10.0/loaders/svg_loader.dll"' > win32/etc/gtk-2.0/gdk-pixbuf.loaders
  #echo '"svg" 2 "gdk-pixbuf" "Scalable Vector Graphics" "LGPL"' >> win32/etc/gtk-2.0/gdk-pixbuf.loaders 
  #echo '"image/svg+xml" "image/svg" "image/svg-xml" "image/vnd.adobe.svg+xml" "text/xml-svg" "image/svg+xml-compressed" ""' >> win32/etc/gtk-2.0/gdk-pixbuf.loaders 
  #echo '"svg" "svgz" "svg.gz" ""' >> win32/etc/gtk-2.0/gdk-pixbuf.loaders 
  #echo '" <svg" "*    " 100' >> win32/etc/gtk-2.0/gdk-pixbuf.loaders 
  #echo '" <!DOCTYPE svg" "*             " 100' >> win32/etc/gtk-2.0/gdk-pixbuf.loaders 
  #echo ' ' >> win32/etc/gtk-2.0/gdk-pixbuf.loaders
  ## We did the above instead of using gdk-pixbuf-query-loaderse.exe because
  ## we need to make a relocatable file.
  ##win32/bin/gdk-pixbuf-query-loaders.exe win32/lib/gtk-2.0/2.10.0/loaders/svg_loader.dll > win32/etc/gtk-2.0/gdk-pixbuf.loaders 

  ##mv win32/zlib-1.2.4/zlib1.dll win32/bin
  ## Move these so CSound can find python25.dll
  #cp -a ../pygtk-stuff/* win32/bin/lib/site-packages

  #cp testgtkenv.bat testgtkenv.py win32/bin/
  #echo "gtk-theme-name = \"MS-Windows\""  > win32/etc/gtk-2.0/gtkrc
  #find win32 -name "*.def" | xargs rm
  #find win32 -name "*.a" | xargs rm
  #find win32 -name "*.lib" | xargs rm
  #(cd win32 && find -name *.pyc | xargs rm)
}

build() {
  # Step 2: After this, we can run from the source dir
  # MS Windows have other defaults than linux. The 'sed' I have installed on
  # my windows machine don't support the -i option.
  mv default.config tmp.cfg
  sed -e "s/type=external-midiplayer/type=sequencer-device/" -e "s/csound=csound/csound=AUTODETECT/" -e "s/mma=mma/mma=AUTODETECT/" tmp.cfg > default.config
  rm tmp.cfg
  ./configure PYTHON=win32/python/python.exe --enable-winmidi
  make
  make winbuild
}
install() {
  # Step 3: Install solfege into win32/ so that we can run from inside
  # it, or create the installer.
  cp README.txt INSTALL.win32.txt INSTALL.txt AUTHORS.txt COPYING.txt win32
  make DESTDIR=win32 prefix="" install skipmanual=yes

  cp solfege/soundcard/winmidi.pyd win32/share/solfege/solfege/soundcard
  cp win32-start-solfege.pyw win32/bin
  cp solfegedebug.bat win32/bin/
}
cleanup_win32() {
  # 185MB
  cd win32/python
  rm -rf include
  rm -rf Tools
  rm -rf tcl
  rm -rf Doc
  cd DLLs
  rm -rf _tkinter.pyd tcl85.dll tclpip85.dll tk85.dll
  cd ..
  cd Lib # python/lib
  rm -rf bsddb compiler curses hotshot idlelib importlib # ctypes distutils
  rm -rf json lib2to3 lib-tk msilib pydoc_data test unittest wsgiref
  #154 MB
  cd site-packages/gtk
  rm -rf glade-previewer.exe glade.exe
  rm -rf lib/glade
  rm -rf libgladeui-2-4.dll
  rm -rf share/glade
  rm -rf share/icons
  find | grep gda | xargs rm -rf

  rm -rf share/glib-2.0
  rm -rf share/gtranslator lib/gtranslator libgtranslator-3.0-0.dll gtranslator.exe
  find | grep dbus | xargs rm -rf
  find | grep telepath | xargs rm -rf
  find | grep aspell | xargs rm -rf
  find | grep enchant | xargs rm -rf
  find | grep gedit | xargs rm -rf
  find | grep goffice | xargs rm -rf
  find | grep gstreamer | xargs rm -rf
  rm -f libwebkitgtk-3.0-0.dll
  rm -f libgucharmap*
  rm -f libgexiv*
  rm -f libpoppler*
  find | grep devhelp | xargs rm -rf
  find | grep geoclue | xargs rm -rf
  rm -f ghex.exe
  rm -f zenity.exe
  find | grep charmap | xargs rm -rf

}
if test "x$1" = "xbuildenv"; then
  buildenv
fi
if test "x$1" = "xsetup"; then
  setup
fi
if test "x$1" = "xbuild"; then
  build
fi
if test "x$1" = "xinstall"; then
  install
fi
if test "x$1" = "xclean"; then
  cleanup_win32
fi
if test "x$1" = "xgo"; then
  setup
  build
  install
fi
if test "x$1" = "x-h"; then
  echo "sub commands:"
  echo "   buildenv      create ../mypython/  This has to be done once with"
  echo "   setup         Create the win32/ directory that includes all deps."
  echo "   build         Build the package. After this we can run from"
  echo "                 the source directory."
  echo "   install       Install into win32/ directory."
  echo "   clean         remove unnecessary stuff from win32/"
  echo "   go            run setup-build-install."
fi

