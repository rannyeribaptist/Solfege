# GNU Solfege - free ear training software
# Copyright (C) 2000, 2001, 2002, 2003, 2004, 2006, 2007, 2008, 2011  Tom Cato Amundsen
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

from __future__ import absolute_import

import re

from solfege.mpd import _exceptions
from solfege.mpd import const
from solfege.mpd.duration import Duration
from solfege.mpd.requests import *
from solfege.mpd import elems

class LexerError(_exceptions.MpdException):
    def __init__(self, msg, lexer):
        _exceptions.MpdException.__init__(self, msg)
        self.m_lineno, self.m_linepos1, self.m_linepos2 = lexer.get_error_location()


class Lexer:
    STAFF = 1
    RHYTHMSTAFF = 2
    VOICE = 3
    CLEF = 4
    STEMDIR = 5
    TRANSPOSE = 6
    TIME = 7
    PARTIAL = 8
    KEY = 9
    NOTE = 10
    SKIP = 11
    REST = 12
    RELATIVE = 13
    TIMES = 14
    TUPLETDIR = 15
    re_staff = re.compile(r"\\staff", re.UNICODE)
    re_rhythmstaff = re.compile(r"\\rhythmstaff", re.UNICODE)
    re_voice = re.compile(r"\\addvoice", re.UNICODE)
    re_clef = re.compile(r"\\clef\s+(\w*)", re.UNICODE)
    re_clef_quoted = re.compile(r"\\clef\s+\"([A-Za-z1-9]+[_^1-9]*)\"", re.UNICODE)
    re_stem_updown = re.compile(r"(\\stem)(Up|Down|Both)\s+", re.UNICODE)
    re_tuplet_updown = re.compile(r"(\\tuplet)(Up|Down|Both)\s+", re.UNICODE)
    re_relative = re.compile(r"\\relative\s+(([a-zA-Z]+)([',]*))", re.UNICODE)
    re_transpose = re.compile(r"\\transpose\s+(([a-zA-Z]+)([',]*))", re.UNICODE)
    re_rest = re.compile(r"(r)([\d]*)(\.*)", re.UNICODE)
        #FIXME we are a little more strict than Lilypond, since ~ has to
        # be before ]
        #FIXME don't use named regex if we don't need it.
    re_melodic = re.compile(r"""(?x)
                             ((?P<notename>[a-zA-Z]+)
                             (?P<octave>[',]*))
                             (?P<len>[\d]*)
                             (?P<dots>\.*)""", re.UNICODE)
    re_skip = re.compile(r"""(?x)
                             (s)
                             (?P<len>[\d]*)
                             (?P<dots>\.*)""", re.UNICODE)
    re_time = re.compile(r"\\time\s+(\d+)\s*/\s*(\d+)", re.UNICODE)
    re_partial = re.compile(r"\\partial\s+(?P<len>[\d]+)(?P<dots>\.*)", re.UNICODE)
    re_key = re.compile(r"\\key\s+([a-z]+)\s*\\(major|minor)", re.UNICODE)
    re_times = re.compile(r"\\times\s+(\d+)\s*/\s*(\d+)\s*{", re.UNICODE)
    def __init__(self, s):
        if not isinstance(s, unicode):
            s = s.decode("utf-8")
        assert isinstance(s, unicode)
        self.m_string = s
        self.m_notelen = Duration(4, 0)
        self.m_idx = 0
        self.m_last_idx = None
    def __iter__(self):
        return self
    @staticmethod
    def to_string(v):
        ret = []
        for toc, toc_data in v:
            if toc == Lexer.STAFF:
                ret.append(r"\staff")
            elif toc == Lexer.RHYTHMSTAFF:
                ret.append(r"\rhythmstaff")
            elif toc == Lexer.VOICE:
                ret.append(r"\addvoice")
            elif toc == Lexer.CLEF:
                ret.append(r"\clef %s " % toc_data)
            elif toc == Lexer.STEMDIR:
                ret.append(r"\stem%s " % {const.UP: 'Up',
                                         const.DOWN: 'Down',
                                         const.BOTH: 'Both'}[toc_data])
            elif toc == Lexer.TRANSPOSE:
                ret.append(r"\transpose %s" % toc_data.get_octave_notename())
            elif toc == Lexer.TIME:
                ret.append(r"\time %i/%i " % (toc_data.m_num, toc_data.m_den))
            elif toc == Lexer.PARTIAL:
                ret.append(r"\partial %s " % toc_data.as_mpd_string())
            elif toc == Lexer.KEY:
                ret.append(r"\key %s \%s " % toc_data)
            elif toc == Lexer.NOTE:
                ret.append("%s%s " % (toc_data.m_pitch.get_octave_notename(),
                    toc_data.m_duration.as_mpd_string() if toc_data.m_duration else ""))
            elif toc == Lexer.SKIP:
                ret.append("s%s " % (toc_data.m_duration.as_mpd_string() if toc_data.m_duration else "",))
            elif toc == Lexer.REST:
                ret.append("r%s " % (toc_data.m_duration.as_mpd_string() if toc_data.m_duration else "",))
            elif toc == Lexer.RELATIVE:
                ret.append(r"\relative %s" % toc_data.get_octave_notename())
            elif toc == Lexer.TIMES:
                ret.append(r"\times %i/%i{ " % (toc_data.m_num, toc_data.m_den))
            elif toc == Lexer.TUPLETDIR:
                ret.append(r"\tuplet%s " % {const.UP: 'Up',
                                         const.DOWN: 'Down',
                                         const.BOTH: 'Both'}[toc_data])
            else:
                ret.append("%s " % toc)
        return "".join(ret).strip()

    def next(self):
        try:
            return self._next()
        except _exceptions.MpdException, e:
            if 'm_mpd_badcode' not in dir(e):
                e.m_lineno, e.m_linepos1, e.m_linepos2 = self.get_error_location()
            raise
    def _next(self):
        # Doing this while loop inside the exception clause is a little
        # faster than using a regular expression.
        try:
            while self.m_string[self.m_idx] in (' ', '\n', '\t'):
                self.m_idx += 1
        except IndexError:
            raise StopIteration
        self.m_last_idx = self.m_idx
        m = self.re_rest.match(self.m_string, self.m_idx)
        if m:
            self.m_idx = m.end()
            resttype, notelen, dots = m.groups()
            numdots = len(dots)
            if notelen:
                notelen = int(notelen)
            else:
                notelen = 0
                if numdots:
                    raise LexerError('Need a digit before dots. Write "%(goodcode)s", not "%(badcode)s".' % {
                        'badcode': m.group().strip(),
                        'goodcode':'%s%i%s' % (resttype, self.m_notelen.m_nh, dots)
                        },
                        self)
            if notelen is 0:
                return self.REST, RestRequest(None, None)
            else:
                self.m_notelen = Duration(notelen, numdots)
                return self.REST, RestRequest(notelen, numdots)
        m = self.re_skip.match(self.m_string, self.m_idx)
        if m:
            self.m_idx = m.end()
            IGN1, skiplen, dots = m.groups()
            numdots = len(dots)
            if skiplen:
                skiplen = int(skiplen)
                self.m_notelen = Duration(skiplen, numdots)
            else:
                skiplen = 0
                if numdots:
                    raise LexerError('Need a digit before dots. Write "%(goodcode)s", not "%(badcode)s".' % {
                        'badcode': m.group().strip(),
                        'goodcode':'s%i%s' % (self.m_notelen.m_nh, dots)
                        }, self)
            if skiplen is 0:
                return self.SKIP, SkipRequest(skiplen, numdots)
            else:
                self.m_notelen = Duration(skiplen, numdots)
                return self.SKIP, SkipRequest(skiplen, numdots)
        m = self.re_partial.match(self.m_string, self.m_idx)
        if m:
            self.m_idx = m.end()
            num, dot = m.groups()
            num = int(num)
            dot = len(dot)
            return self.PARTIAL, Duration(num, dot)
        m = self.re_melodic.match(self.m_string, self.m_idx)
        if m:
            self.m_idx = m.end()
            notename, IGN1, IGN2, notelen, dots = m.groups()
            numdots = len(dots)
            if notelen:
                notelen = int(notelen)
                self.m_notelen = Duration(notelen, numdots)
            else:
                notelen = 0
                if dots:
                    raise LexerError('Need a digit before dots. Write "%(goodcode)s", not "%(badcode)s".' % {
                        'badcode': m.group().strip(),
                        'goodcode':'%s%i%s' % (notename, self.m_notelen.m_nh, dots)
                        }, self)
            n = MusicRequest(notename, notelen, numdots)
            return self.NOTE, n
        m = self.re_staff.match(self.m_string, self.m_idx)
        if m:
            self.m_idx = m.end()
            return self.STAFF, None
        m = self.re_rhythmstaff.match(self.m_string, self.m_idx)
        if m:
            self.m_idx = m.end()
            return self.RHYTHMSTAFF, None
        m = self.re_voice.match(self.m_string, self.m_idx)
        if m:
            self.m_idx = m.end()
            return self.VOICE, None
        m = self.re_relative.match(self.m_string, self.m_idx)
        if m:
            self.m_idx = m.end()
            return self.RELATIVE, MusicalPitch.new_from_notename(m.group(1))
        m = self.re_clef_quoted.match(self.m_string, self.m_idx)
        if m:
            self.m_idx = m.end()
            return self.CLEF, m.group(1)
        m = self.re_clef.match(self.m_string, self.m_idx)
        if m:
            self.m_idx = m.end()
            return self.CLEF, m.group(1)
        m = self.re_stem_updown.match(self.m_string, self.m_idx)
        if m:
            self.m_idx = m.end()
            d = [const.UP, const.DOWN, const.BOTH][['Up', 'Down', 'Both'].index(m.group(2))]
            return self.STEMDIR, d
        m = self.re_tuplet_updown.match(self.m_string, self.m_idx)
        if m:
            self.m_idx = m.end()
            d = [const.UP, const.DOWN, const.BOTH][['Up', 'Down', 'Both'].index(m.group(2))]
            return self.TUPLETDIR, d
        m = self.re_transpose.match(self.m_string, self.m_idx)
        if m:
            self.m_idx = m.end()
            return self.TRANSPOSE, MusicalPitch.new_from_notename(m.group(1))
        m = self.re_time.match(self.m_string, self.m_idx)
        if m:
            self.m_idx = m.end()
            return self.TIME, elems.TimeSignature(int(m.group(1)), int(m.group(2)))
        m = self.re_key.match(self.m_string, self.m_idx)
        if m:
            self.m_idx = m.end()
            return self.KEY, (m.group(1), m.group(2))
        m = self.re_times.match(self.m_string, self.m_idx)
        if m:
            self.m_idx = m.end()
            return self.TIMES, Rat(int(m.groups()[0]), int(m.groups()[1]))
        if self.m_idx == len(self.m_string):
            raise StopIteration
        self.m_idx += 1
        return self.m_string[self.m_idx-1], None
    def get_error_location(self):
        """
        Return a tuple
        (lineno, pos1, pos2)
        lineno is the 0-index line where the error occoured.
        string[pos1:pos2] will return the exact text that caused the error.
        """
        # Let us first count lines to find which line we are on.
        # line numbers are 0-indexed
        lineno = self.m_string[:self.m_last_idx].count("\n")
        line_start = self.m_last_idx
        while line_start > 0 and self.m_string[line_start] != "\n":
            line_start -= 1
        if self.m_string[line_start] == "\n":
            line_start += 1
        line_end = line_start
        while line_end < len(self.m_string) and self.m_string[line_end] != '\n':
            line_end += 1
        return (lineno, self.m_last_idx - line_start, self.m_idx - line_start)
    def set_first_pitch(self, pitch):
        """
        Modify the first pitch of the music.
        """
        assert isinstance(pitch, MusicalPitch)
        for toc, toc_data in self:
            if toc == Lexer.NOTE:
                self.m_string = self.m_string[:self.m_last_idx] + "%s%s" % (pitch.get_octave_notename(), toc_data.m_duration.as_mpd_string() if toc_data.m_duration else "") + self.m_string[self.m_idx:]
                break


