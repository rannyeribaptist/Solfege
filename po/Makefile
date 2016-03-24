# vim: set noexpandtab:
#
# GNU Solfege - free ear training software
# Copyright (C) 2000, 2001, 2002, 2003, 2004, 2007, 2008, 2011  Tom Cato Amundsen
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

POFILES:=$(wildcard po/*.po)
MOFILES:=$(patsubst %.po,%.mo, $(POFILES))
POLANGUAGES:=$(patsubst po/%.po,%,$(POFILES))
TARGETS += $(MOFILES)
dist_files += $(POFILES) po/Makefile po/solfege.pot

%.mo: %.po
	$(MSGFMT) $< -o $@

local-message-catalogs:=$(patsubst %,share/locale/%/LC_MESSAGES/$(PACKAGE).mo,$(POLANGUAGES))
all: $(local-message-catalogs)

share/locale/%/LC_MESSAGES/$(PACKAGE).mo: po/%.mo
	mkdir -p share/locale/$(patsubst po/%.mo,%,$<)/LC_MESSAGES
	cp $< $@

run-from-srcdir: $(MOFILES)
	# we to this just to make life simpler when running from source dir
	for lang in $(POLANGUAGES); do \
	  mkdir -p share/locale/$$lang/LC_MESSAGES ; \
	  cp po/$$lang.mo share/locale/$$lang/LC_MESSAGES/$(PACKAGE).mo; \
	done

install-po:
	for lang in $(POLANGUAGES); do \
	  mkdir -p $(DESTDIR)/$(datadir)/locale/$$lang/LC_MESSAGES; \
	  $(INSTALL_DATA) po/$$lang.mo $(DESTDIR)/$(datadir)/locale/$$lang/LC_MESSAGES/$(PACKAGE).mo; \
	done

uninstall-po:
	for lang in $(POLANGUAGES); do \
	  rm -f $(DESTDIR)/$(datadir)/locale/$$lang/LC_MESSAGES/$(PACKAGE).mo; \
	  rmdir $(DESTDIR)/$(datadir)/locale/$$lang/LC_MESSAGES || true ; \
	  rmdir $(DESTDIR)/$(datadir)/locale/$$lang|| true ; \
	done
	rmdir $(DESTDIR)/$(datadir)/locale || true

trfiles:=$(wildcard solfege/*.py) \
	   $(wildcard solfege/mpd/*.py) \
	   $(wildcard solfege/soundcard/*.py) \
	   $(wildcard solfege/exercises/*.py) \
           $(filter-out exercises/standard/lesson-files/bin \
                        exercises/standard/lesson-files/include \
						exercises/standard/lesson-files/share, \
					$(wildcard exercises/standard/lesson-files/*)) \
		   $(wildcard exercises/standard/lesson-files/include/*) \
		   $(filter-out exercises/standard/debugtree.txt, $(wildcard exercises/standard/*.txt))

po-update: po/solfege.pot
	for pofile in $(POFILES); do \
         cp $$pofile tmpfile; \
         $(MSGMERGE) tmpfile po/$(PACKAGE).pot > $$pofile; \
       done
	rm tmpfile
	@echo
	@echo "Just a friendly reminder:"
	@echo "The translation of GNU Solfege is handled by the Translation Project."
	@echo "You should visit http://translationproject.org and follow their"
	@echo "guidelines if you want to translate GNU Solfege."

po/solfege.pot: $(trfiles)
	$(XGETTEXT) --from-code=utf-8 --add-comments=translators -L python -o solfege.pot -p po \
	--copyright-holder="Tom Cato Amundsen" \
	--keyword=_i $(trfiles)

check-for-new-po-files:
ifneq "$(skip_new_po_test)" "yes"
	@echo "Run with 'skip_new_po_test=yes' to drop the following check."
	rsync -Lrtvz  translationproject.org::tp/latest/solfege/  po
	$(GIT) status --porcelain po > po-diff.tmp
	@echo
	@if test -s "po-diff.tmp" ; then \
		$(GIT) status po ; \
		echo "There are new translations in po/ that need to be committed."; \
		echo "Exiting..."; \
		exit 10; \
	fi
	rm -f po-diff.tmp
endif

