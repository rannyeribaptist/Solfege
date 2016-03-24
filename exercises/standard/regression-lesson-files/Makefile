# vim: set noexpandtab:
#
# GNU Solfege - free ear training software
# Copyright (C) 2004, 2007, 2008, 2011 Tom Cato Amundsen
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

installfiles += $(filter-out \
	exercises/standard/regression-lesson-files/Makefile \
	exercises/standard/regression-lesson-files/share, \
	$(wildcard exercises/standard/regression-lesson-files/* \
			   exercises/standard/regressions-lesson-files/share/*))

lf_dist_files += $(filter-out exercises/standard/regression-lesson-files/share, \
        $(wildcard exercises/standard/regression-lesson-files/* \
                   exercises/standard/regression-lesson-files/share/*))

.PHONY: gen-regression-lessonfiles
gen-regression-lessonfiles:
	$(PYTHON) tools/gen_regression_lessonfiles.py

all: gen-regression-lessonfiles
