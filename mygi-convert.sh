#!/bin/sh

FILES_TO_CONVERT="solfege/gu.py solfege/esel.py solfege/exercises/rhythm.py solfege/statisticsviewer.py"

perl -i -0 -pe "s/\.value\s=\s([^\n]+)/\.set_value(\1)/g;" solfege/esel.py

for f in $FILES_TO_CONVERT; do
    perl -i -0 \
    -pe "s/getattr\(gtk.keysyms, s\)/getattr\(Gdk, 'KEY_%s' % s\)/g;"\
    -pe "s/\.size_request\(\)\[0\]/.size_request\(\).width/g;"\
    -pe "s/\.size_request\(\)\[1\]/.size_request\(\).height/g;"\
    -pe "s/\.value(\W)/\.get_value\(\)\1/g;"\
    -pe "s/\.page_size/\.get_page_size\(\)/g;"\
    -pe "s/gtk.HBox\(\)/Gtk.HBox\(False, 0\)/g;" \
    -pe "s/gtk.VBox\(\)/Gtk.VBox\(False, 0\)/g;" \
    $f
done

