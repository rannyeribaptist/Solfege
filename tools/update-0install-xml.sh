#!/bin/bash

if [ "$1" = "-h" ]; then
 echo "Usage:"
 echo "  tools/update-0install-xml.sh stable|unstable VERSION"
 echo "Example:"
 echo "  tools/update-0install-xml.sh stable 3.20.1"
 exit 0;
fi

BRANCH=$1
VERSION=$2

echo "branch" $BRANCH
echo "version" $VERSION

if [ "$BRANCH"  != "stable" ]; then
  if [ "$BRANCH" != "unstable" ]; then
    echo "First argument must be stable or unstable"
    exit 1;
  fi
fi

if [ "$BRANCH" = "stable" ]; then
  stability="stable"
fi

if [ "$BRANCH" = "unstable" ]; then
  stability="developer"
fi

if test ! -e solfege-$VERSION-Linux-i386.tar.gz; then
  echo "solfege-$VERSION-Linux-i386.tar.gz must exist in the current directory"
  exit 1
fi

if test ! -e solfege-$VERSION-Linux-x86_64.tar.gz; then
  echo "solfege-$VERSION-Linux-x86_64.tar.gz must exist in the current directory"
  exit 1
fi


0publish -v solfege.xml \
  --add-version=$VERSION \
  --set-released=today \
  --set-arch=Linux-x86_64 \
  --set-stability=$stability \
  --set-main=solfege-$VERSION-Linux-x86_64/bin/solfege \
  --archive-file=solfege-$VERSION-Linux-x86_64.tar.gz \
  --archive-url=http://heanet.dl.sourceforge.net/project/solfege/solfege-$BRANCH/$VERSION/0install/solfege-$VERSION-Linux-x86_64.tar.gz


0publish -v solfege.xml \
  --add-version=$VERSION \
  --set-released=today \
  --set-arch=Linux-i386 \
  --set-stability=$stability \
  --set-main=solfege-$VERSION-Linux-i386/bin/solfege \
  --archive-file=solfege-$VERSION-Linux-i386.tar.gz \
  --archive-url=http://heanet.dl.sourceforge.net/project/solfege/solfege-$BRANCH/$VERSION/0install/solfege-$VERSION-Linux-i386.tar.gz

echo
echo "You are not done yet: Must check solfege.xml with 0publish-gui and"
echo "add license information."
