# vim: set noexpandtab:
# NB: There are some places further down this file where we have
# to add a line for each language we add. It is not enought just
# to add to this variable:
USER_MANUAL_LANGUAGES=de eo es et fr gl nb nl pl pt_BR ru tr
include help/C/Makefile

I18NDEFS:=--stringparam chunker.output.encoding "UTF-8"
XSLTPARAMS:= \
--param chunk.quietly 1 \
--param use.id.as.filename 1 \
--param callout.unicode 1 \
--param callout.graphics 0 \
--param xref.with.number.and.title 0 \
--xinclude \
--stringparam html.stylesheet "../style.css"

dist_files += help/Makefile help/README \
	help/style.css \
	$(foreach dir,C $(USER_MANUAL_LANGUAGES), \
	$(wildcard help/$(dir)/*.html) \
	$(wildcard help/$(dir)/*.xml) \
	$(wildcard help/$(dir)/$(dir).po) \
	$(wildcard help/$(dir)/figures/*.png) \
	$(wildcard help/$(dir)/ly/*.png) \
	)

# Add all .ly files in help/C/ly that are not generated files.
dist_files += $(filter-out $(shell python tools/generate_theory_ly.py --ly-C-targets),$(wildcard help/C/ly/*.ly))

installfiles+=$(foreach dir,$(USER_MANUAL_LANGUAGES), \
	$(wildcard help/$(dir)/*.html) \
	$(wildcard help/$(dir)/figures/*.png) \
	$(wildcard help/$(dir)/ly/*.png) \
	)
installfiles+=help/style.css

ifneq "$(skipmanual)" "yes"
ifdef LILYPOND
all: $(shell python tools/generate_theory_ly.py --png-targets)
endif
endif


# I have removed any code that will merge help/C/solfege.pot and
# help/lang/lang.po since the Translation Project should do all merging.
# generation of C/solfege.pot is in help/C/Makefile
# User manual dependencies:
# (1) help/C/solfege.pot: SOURCES
# (2) help/lang/solfege.xml: help/C/solfege.pot help/lang/lang.po $(NOT_TRANSLATED_SOURCES)
#     NB: lang.po is only changed if we have new translations. So we must
#     depend on solfege.pot too, since we will use the english text if
#     no translation exist.
# (3) help/lang/index.html: help/lang/solfege.xml

help/de/solfege.xml: help/C/solfege.pot help/de/de.po $(USER_MANUAL_SOURCES)
help/eo/solfege.xml: help/C/solfege.pot help/eo/eo.po $(USER_MANUAL_SOURCES)
help/es/solfege.xml: help/C/solfege.pot help/es/es.po $(USER_MANUAL_SOURCES)
help/et/solfege.xml: help/C/solfege.pot help/et/et.po $(USER_MANUAL_SOURCES)
help/fr/solfege.xml: help/C/solfege.pot help/fr/fr.po $(USER_MANUAL_SOURCES)
help/gl/solfege.xml: help/C/solfege.pot help/gl/gl.po $(USER_MANUAL_SOURCES)
help/nb/solfege.xml: help/C/solfege.pot help/nb/nb.po $(USER_MANUAL_SOURCES)
help/nl/solfege.xml: help/C/solfege.pot help/nl/nl.po $(USER_MANUAL_SOURCES)
help/pl/solfege.xml: help/C/solfege.pot help/pl/pl.po $(USER_MANUAL_SOURCES)
help/pt_BR/solfege.xml: help/C/solfege.pot help/pt_BR/pt_BR.po $(USER_MANUAL_SOURCES)
help/ru/solfege.xml: help/C/solfege.pot help/ru/ru.po $(USER_MANUAL_SOURCES)
help/tr/solfege.xml: help/C/solfege.pot help/tr/tr.po $(USER_MANUAL_SOURCES)

help/%/solfege.xml:
ifdef XML2PO
ifneq "$(skipmanual)" "yes"
	for filename in $(notdir $(USER_MANUAL_SOURCES)); do \
	$(XML2PO) --keep-entities -p $(patsubst help/%/solfege.xml, help/%, $@)/$(patsubst help/%/solfege.xml,%,$@).po -o $(dir $@)/$$filename help/C/$$filename; \
	done
	rm -f .xml2po.mo
endif
endif

manual-po-update: help/C/solfege.pot
	for pofile in $(wildcard help/*/*.po); do \
         cp $$pofile tmpfile; \
         $(MSGMERGE) tmpfile help/C/$(PACKAGE).pot > $$pofile; \
       done
	rm tmpfile
	@echo
	@echo "Just a friendly reminder:"
	@echo "The translation of GNU Solfege is handled by the Translation Project."
	@echo "You should visit http://translationproject.org and follow their"
	@echo "guidelines if you want to translate GNU Solfege."

xmllint:
	for lang in $(USER_MANUAL_LANGUAGES); do \
		xmllint --postvalid --dtdvalid http://www.oasis-open.org/docbook/xml/4.4/docbookx.dtd --xinclude --noout  help/$$lang/solfege.xml ;\
		if [ $$? -eq 0 ] ; then true; else exit $$?; fi \
	done


maintainer-clean: rm-generated-user-manual

genlyfiles: $(MOFILES)
	$(PYTHON) tools/generate_theory_ly.py --all

rm-generated-user-manual:
	for dir in $(USER_MANUAL_LANGUAGES); do \
		rm -f help/$$dir/*.html; \
		rm -f help/$$dir/*.xml; \
		rm -rf help/$$dir/ly; \
	done
	rm -f help/C/*.html

TARGETS += help/C/rhythmtable.xml
help/C/rhythmtable.xml: tools/gen_rhythms_table.py
	$(PYTHON) tools/gen_rhythms_table.py

%/one-big-page.html: %/solfege.xml
	(cd $(dir $<); $(XSLTPROC) $(I18NDEFS) --xinclude --stringparam html.stylesheet "../style.css" --stringparam root.filename "one-big-page" --param onechunk 1 $(subst chunk,onechunk,$(STYLESHEET)) $(notdir $<) )

%/index.html: %/solfege.xml
ifneq "$(skipmanual)" "yes"
ifeq "$(HAVE_STYLESHEET)" "yes"
 ifneq "$(XSLTPROC)" ""
	(cd $(dir $<); $(XSLTPROC) $(I18NDEFS) $(XSLTPARAMS) $(STYLESHEET) $(notdir $<))
 else
  ifneq "$(skipmanual)" "yes"
	@echo "*** Cannot rebuild the user manual because you don't have xsltproc installed."
	@echo "*** Run make as 'make skipmanual=yes' to ignore the problem and don't build the docs"
	exit 64
  endif
 endif
else
 ifneq "$(skipmanual)" "yes"
	@echo "*** Cannot rebuild html docs because we are missing the docbook stylesheet."
	@echo "*** Try to install the missing software and reconfigure."
	@echo "*** Run make as 'make skipmanual=yes' to ignore the problem and don't build the docs"
	exit 64
 endif
endif
endif
ifeq "$(skipmanual)" "yes"
	@echo "*** Not building manual because nomanual=yes"
endif

.PHONY: update-manual
ifdef XML2PO
update-manual: $(addsuffix /index.html,$(addprefix help/,C $(USER_MANUAL_LANGUAGES)))
else
update-manual:
	@echo "You have to install xml2po to run 'make update-manual'"
endif

%.png:%.ly
ifeq "$(LILYPOND_VERSION)" "2.10"
	$(LILYPOND) -I ../../C/ly --png -b eps -dno-gs-load-fonts -dinclude-eps-fonts -o $(basename $@) $<
else
	$(LILYPOND) -I ../../C/ly --png -d backend=eps -o $(basename $@) $<
endif

stupid-step1:
	rm -rf manual-po-tmp
	rm -rf my-manual-po-tmp
	mkdir my-manual-po-tmp
	rsync -Lrtvz  translationproject.org::tp/latest/solfege-manual/  manual-po-tmp

stupid-step2:
	cp help/*/*.po my-manual-po-tmp
	for lang in $(basename $(notdir $(wildcard manual-po-tmp/*.po))); do \
		    mkdir -p help/$$lang; \
			cp manual-po-tmp/$$lang.po help/$$lang/$$lang.po; \
	done
	diff my-manual-po-tmp manual-po-tmp > manual-po-diff.tmp || true
	@if test -s "manual-po-diff.tmp" ; then \
		echo "There are new translations of the manual that need to be committed."; \
		echo "Exiting..."; \
		exit 10; \
	fi
	rm -f manual-po-diff.tmp
	rm -rf my-manual-po-tmp manual-po-tmp

# I had to split check-for-new-manual-po-files into two subtargets and
# run make on them because often the wilcard in stupid-step2 would not
# find any files in manual-po-tmp even though I verified that they where
# there.
check-for-new-manual-po-files:
ifneq "$(skip_new_po_test)" "yes"
	@echo "Run with 'skip_new_po_test=yes' to drop the following check."
	$(MAKE) stupid-step1 
	$(MAKE) stupid-step2
endif
