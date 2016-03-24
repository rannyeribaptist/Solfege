#!/bin/sh

FILES_TO_CONVERT="$(find . -name '*.py')"

for f in $FILES_TO_CONVERT; do
    perl -i -0 \
	    -pe "s/Gtk.HSeparator\(, True, True, 0\)/Gtk.HSeparator\(\)/g;"\
	    -pe "s/Gtk.VSeparator\(, True, True, 0\)/Gtk.VSeparator\(\)/g;"\
    $f
done

perl -i -0 -pe "s/Gtk.Combo,/Gtk.ComboBox,/g;" solfege/gu.py
perl -i -0 -pe "s/pack_start\(([^,]+), False\)/pack_start\(\1, False, False, 0\)/g;" solfege/tracebackwindow.py solfege/mainwin.py solfege/esel.py
perl -i -0 -pe "s/pack_start\(([^,]+), True\)/pack_start\(\1, True, False, 0\)/g;" solfege/tracebackwindow.py solfege/mainwin.py solfege/esel.py
perl -i -0 -pe "s/pack_start\(([^,\)]+), False, padding=([^\)])/pack_start\(\1, False, False, padding=\2/g" solfege/esel.py

perl -i -0 -pe "s/pack_start\(([^,\)]+), ([^,\)]+), ([^,\)]+)\)/pack_start\(\1, \2, \3, padding=0\)/g" solfege/gu.py
