#!/bin/bash

set -e
echo "Processing version:" $1

if [ "$1" = "-h" ]; then
  echo "Usage:"
  echo "    tools/make-0install.sh stable|unstable PLATFORM version-nr"
  echo "Example:"
  echo "    tools/make-0install.sh stable Linux-x86_64 3.18.0"
  exit 0;
fi

if [ "$1" != "stable" ]; then
  if [ "$1" != "unstable" ]; then
    echo "Param 1 must be 'stable' or 'unstable'";
    exit 1;
  fi
fi
if [ "$2" != "Linux-i386" ]; then
  if [ "$2" != "Linux-x86_64" ]; then
    echo "Param 2 must be 'Linux-i386' or 'Linux-x86_64'";
    exit 1;
  fi
fi


VERSION=$3
PLATFORM=$2
DIST=$1

TARBALL=solfege-$VERSION.tar.gz
TF=solfege-$VERSION.tar

if test ! -e $TARBALL ; then
   echo "File solfege-$VERSION.tar.gz does not exist"
   exit -1
fi

if test -e solfege-$VERSION ; then
    echo "Directory solfege-$VERSION exists"
    exit -1
fi

tar zxf solfege-$VERSION.tar.gz
cd solfege-$VERSION
pwd
./configure --prefix=`pwd`/solfege-$VERSION-$PLATFORM
make
make install
cd solfege-$VERSION-$PLATFORM
find -name *.pyc | xargs rm -f
find -name *.pyo | xargs rm -f
pwd
cd ..
tar --gzip --create --file=../solfege-$VERSION-$PLATFORM.tar.gz solfege-$VERSION-$PLATFORM


