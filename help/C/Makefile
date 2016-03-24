installfiles+=$(wildcard help/C/*.html) \
	$(wildcard help/C/ly/*.png) \
	$(wildcard help/C/figures/*.png) \
	$(wildcard help/C/scales/*.html) \
	$(wildcard help/C/scales/images/quadriads/*.png) \
	$(wildcard help/C/scales/images/triads/*.png) \
	$(wildcard help/C/scales/images/modes/chords/*.png) \
	$(wildcard help/C/scales/images/modes/scales/*.png) \

NOT_TRANSLATED_SOURCES=help/C/gpl.xml \
	help/C/lessonfiles.xml \
	help/C/rhythmtable.xml \
	help/C/midi-instrument-names.xml

USER_MANUAL_SOURCES=$(filter-out $(NOT_TRANSLATED_SOURCES), $(wildcard help/C/*.xml))

ly_gen_png_target = $(patsubst %.ly,%.png,$(filter-out $(wildcard help/C/ly/*common*.ly),$(wildcard help/C/ly/*.ly)))

pngs: $(ly_gen_png_target)

ifneq "$(skipmanual)" "yes"
ifdef LILYPOND
all: $(ly_gen_png_target)
endif
endif

maintainer-clean:
	rm -f $(ly_gen_png_target)
	rm -f help/C/*.html

dist_files += help/C/solfege.pot \
	help/C/Makefile \
	help/C/solfege.xml.in \
	$(wildcard help/C/scales/*.html) \
	$(wildcard help/C/scales/images/quadriads/*.png) \
	$(wildcard help/C/scales/images/triads/*.png) \
	$(wildcard help/C/scales/images/modes/chords/*.png) \
	$(wildcard help/C/scales/images/modes/scales/*.png) \

help/C/solfege.pot: $(USER_MANUAL_SOURCES)
ifndef XML2PO
	@echo
	@echo "You need to install xml2po to update help/C/solfege.pot"
	@echo
	@exit 64
else
	$(XML2PO) --keep-entities $(USER_MANUAL_SOURCES) | $(MSGGREP) -v -K -e "@@image:" -e "^Tom" -e "^Amundsen" -e "^tca@gnu.org" -e "^bug-solfege@gnu.org" -e "^solfege-devel@lists.sourceforge.net" -e "^solfege-announce@lists.sourceforge.net"  -o help/C/solfege.pot
endif

help/C/index.html: $(USER_MANUAL_SOURCES) $(NOT_TRANSLATED_SOURCES)

