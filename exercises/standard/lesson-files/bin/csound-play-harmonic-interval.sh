#!/bin/bash

# This file is free software; as a special exception the author gives
# unlimited permission to copy and/or distribute it, with or without
# modifications, as long as this notice is preserved.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY, to the extent permitted by law; without even the
# implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

set -e

TMPDIR=/tmp/solfegetmpdir.$$

umask 027       # or 077
rm -rf $TMPDIR
mkdir $TMPDIR || exit 1

sed -e "s/440/$1/" -e "s/660/$2/" share/fil1.sco >$TMPDIR/solfege-csound.sco
csound share/fil1.orc $TMPDIR/solfege-csound.sco -W -g -o devaudio
rm -rf $TMPDIR

