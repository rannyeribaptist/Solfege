#!/bin/bash
set -e

if [ "$OSTYPE" = "msys" ]; then
	export GIT=C:/Programfiler/Git/bin/git.exe
	export GIT="C:/Program Files (x86)/Git/bin/git.exe"
	export PYTHON=/c/python27/python.exe
	export PYTHON=../mypython/python.exe
	aclocal-1.11
	autoconf
	configure --enable-winmidi
	$PYTHON -c "import tools.buildutil; tools.buildutil.create_versions_file('$GIT')"
else
	aclocal $ACINCLUDE
	autoconf
        python -c "import tools.buildutil; tools.buildutil.create_versions_file('git')"
fi
