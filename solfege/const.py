# GNU Solfege - free ear training software
# Copyright (C) 2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2011  Tom Cato Amundsen
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

# Moved RHYTHMS here because is should be available from a module that does
# not pull in the gtk module.

from __future__ import absolute_import

RHYTHMS = ("c4", "c8 c8", "c16 c16 c16 c16", "c8 c16 c16",
           "c16 c16 c8", "c16 c8 c16", "c8. c16", "c16 c8.",
           "r4", "r8 c8", "r8 c16 c16", "r16 c16 c8", "r16 c8 c16",
           "r16 c16 c16 c16", "r8 r16 c16", "r16 c8.",
           "c12 c12 c12", "r12 c12 c12",
           "c12 r12 c12", "c12 c12 r12", "r12 r12 c12", "r12 c12 r12",
           "c4.", "c4 c8", # 22, 23
           "c8 c4", "c8 c8 c8", # 24, 25
           "c4 c16 c16", # 26
           "c16 c16 c4", # 27
           "c8 c8 c16 c16", #28
           "c8 c16 c16 c8", #29
           "c16 c16 c8 c8", #30
           "c8 c16 c16 c16 c16", #31
           "c16 c16 c8 c16 c16", #32
           "c16 c16 c16 c16 c8", #33
           "c16 c16 c16 c16 c16 c16", #34
)

solmisation_syllables = ["SO,","SI,","LU,","LA,","LI,","TU,","TI,","DO","DI","RU","RE","RI","MU","MI","FA","FI","SU","SO","SI","LU","LA","LI","TU","TI","DO'","DI'","RU'","RE'","RI'","MU'","MI'","FA'","FI'","SU'","SO'"]

solmisation_notenames = ["g","gis","aes","a","ais","bes","b","c'","cis'","des'","d'","dis'","ees'","e'", "f'","fis'","ges'","g'","gis'","aes'","a'","ais'","bes'","b'","c''","cis''","des''","d''","dis''","ees''","e''", "f''","fis''","ges''","g''"]
