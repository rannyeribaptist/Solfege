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

from __future__ import absolute_import
import operator

from gi.repository import Gtk
from gi.repository import Pango
from gi.repository import GdkPixbuf
import cairo

from solfege.mpd import const
from solfege.mpd import elems
from solfege.mpd import mpdutils
from solfege.mpd.musicalpitch import MusicalPitch

ACCIDENTAL__2 = -2
ACCIDENTAL__1 = -1
ACCIDENTAL_0 = 0
ACCIDENTAL_1 = 1
ACCIDENTAL_2 = 2

NOTEHEAD_WHOLE = 0
NOTEHEAD_HALF = 1
NOTEHEAD_QUARTER = 2

FLAG_8UP = 'u3'
FLAG_8DOWN = 'd3'
FLAG_16UP = 'u4'
FLAG_16DOWN = 'd4'
FLAG_32UP = 'u5'
FLAG_32DOWN = 'd5'
FLAG_64UP = 'u6'
FLAG_64DOWN = 'd6'

fetadir = "feta"

class dim20:
    linespacing = 8
    stemlen = linespacing * 3.5
    xshift = 10
    col_width = 20
    first_staff_ypos = 80
    staff_spacing = 100
    ledger_left = -4
    ledger_right = 14
    accidental_widths = { -2: 12, -1: 7, 0: 5, 1: 8, 2: 8}
    clef_yoffset = {
        'G': -38 + 3 * linespacing,
        'F':  -8 + 3 * linespacing,
        'C': -15 + 3 * linespacing,
    }

dimentions = {20: dim20}

accidental_y_offset = {ACCIDENTAL__2: -7,
                       ACCIDENTAL__1: -7,
                       ACCIDENTAL_0: -5,
                       ACCIDENTAL_1: -6,
                       ACCIDENTAL_2: -2}

class Engraver:
    def __init__(self):
        self.m_fontsize = 20
    def get_width(self):
        """
        Get the width of all engravers that does not implement their
        own get_width function.
        """
        return 20
    def __str__(self):
        return '(%s)' % self.__class__


class ClefEngraver(Engraver):
    def __init__(self, clef):
        Engraver.__init__(self)
        self.m_clef = clef

    def get_width(self):
        return 25

    def engrave(self, ct, staff_yoffset):
        ims = cairo.ImageSurface.create_from_png(
            fetadir + '/feta%i-clefs-%s.png'
            % (self.m_fontsize, self.m_clef.get_symbol()))
        ct.set_source_surface(
            ims, self.m_xpos,
            dimentions[self.m_fontsize].clef_yoffset[self.m_clef.get_symbol()]
            - self.m_clef.get_stafflinepos() * dimentions[self.m_fontsize].linespacing
            + staff_yoffset)
        ct.paint()


class TimeSignatureEngraver(Engraver):
    def __init__(self, timesig):
        Engraver.__init__(self)
        self.m_timesig = timesig

    def engrave(self, ct, staff_yoffset):
        x = 0
        for idx in range(len(str(self.m_timesig.m_num))):
            n = str(self.m_timesig.m_num)[idx]
            ims = cairo.ImageSurface.create_from_png(
                fetadir + '/feta%i-number-%s.png' % (self.m_fontsize, n))
            ct.set_source_surface(ims, self.m_xpos + x, staff_yoffset - 12)
            x += 10
        x = 0
        for idx in range(len(str(self.m_timesig.m_den))):
            n = str(self.m_timesig.m_den)[idx]
            ims = cairo.ImageSurface.create_from_png(
                fetadir + '/feta%i-number-%s.png' % (self.m_fontsize, n))
            ct.set_source_surface(ims, self.m_xpos + x, staff_yoffset + 3)
            x += 10
    def __str__(self):
        return '(TimeSignatureEngraver:%i/%i)' % (self.m_timesig.m_den,
            self.m_timesig.m_num)


class TieEngraver(Engraver):
    def __init__(self,  note1, note2):
        Engraver.__init__(self)
        self.m_note1 = note1
        self.m_note2 = note2

    def engrave(self, ct, staff_yoffset):
        dim = dimentions[self.m_fontsize]
        p1 = self.m_note1.m_xpos + dim.xshift
        p2 = self.m_note2.m_xpos
        w = p2 - p1 - dim.xshift
        w = max(w, dim.xshift)
        ct.arc((p1 + (p2 - p1) / 2),
               int(staff_yoffset + dim.linespacing * (self.m_note2.m_ypos-1) / 2 + 3),
               int(w), 30 * 3.14 / 180, 150 * 3.14 / 180)
        ct.stroke()


class AccidentalsEngraver(Engraver):
    def __init__(self, accs):
        Engraver.__init__(self)
        self.m_accs = accs
        def f(v, w=dimentions[self.m_fontsize].accidental_widths):
            x = 0
            for a in v:
                x += w[a]
            return x
        self.m_usize = reduce(operator.__add__, map(f, accs.values())) + len(accs)
    def get_width(self):
        return self.m_usize
    def engrave(self, ct, staff_yoffset):
        x = 0
        for y in self.m_accs:
            for acc in self.m_accs[y]:
                ims = cairo.ImageSurface.create_from_png(
                        fetadir+'/feta%i-accidentals-%i.png' % \
                            (self.m_fontsize, acc))
                ct.set_source_surface(ims, self.m_xpos + x,
                        int(accidental_y_offset[acc] + staff_yoffset
                         + dimentions[self.m_fontsize].linespacing*y/2
                         + accidental_y_offset[acc]))
                x += dimentions[self.m_fontsize].accidental_widths[acc] + 1
        ct.paint()


class KeySignatureEngraver(Engraver):
    def __init__(self, old_key, key, clef):
        Engraver.__init__(self)
        self.m_clef = clef
        self.m_old_accidentals = mpdutils.key_to_accidentals(old_key)
        self.m_accidentals = mpdutils.key_to_accidentals(key)
    def get_width(self):
        #FIXME this value depends on the fontsize, and on what kind of
        #accidental we are drawing. A sharp is wider that a flat.
        return len(self.m_accidentals) * 10 + len(self.m_old_accidentals) * 6 + 8
    def engrave(self, ct, staff_yoffset):
        x = 0
        dolist = []
        # natural signs
        for acc in self.m_old_accidentals:
            if acc in self.m_accidentals:
                continue
            ypos = self.m_clef.an_to_ylinepos(acc)
            dolist.append((0, x, ypos))
            #FIXME see FIXME msg in .get_width
            x += 6
        # accidentals
        for acc in self.m_accidentals:
            if acc.endswith('eses'):
                ktype = -2
            elif acc.endswith('es'):
                ktype = -1
            elif acc.endswith('isis'):
                ktype = 2
            else:
                ktype = 1
            ypos = self.m_clef.an_to_ylinepos(acc)
            dolist.append((ktype, x, ypos))
            #FIXME see FIXME msg in .get_width
            x += 10
        for ktype, x, ypos in dolist:
            ims = cairo.ImageSurface.create_from_png(
                fetadir + '/feta%i-accidentals-%i.png' % (self.m_fontsize, ktype))
            ct.set_source_surface(ims, self.m_xpos + x,
                int(accidental_y_offset[ktype] + staff_yoffset
                     + dimentions[self.m_fontsize].linespacing * ypos / 2
                     + accidental_y_offset[ktype]))
            ct.paint()


class NoteheadEngraver(Engraver):
    def __init__(self, shift, ypos, musicalpitch, duration):
        """
        m_ypos == 0 is the middle line on the staff.
        Negative value is up, positive is down.
        The value counts notesteps, not pixels!
        FIXME, right now it also draws dots, but they should be an own class
        because the dots has to be handled special with noteheads are xshifted.
        """
        Engraver.__init__(self)
        if duration.m_nh < 2:
            self.m_head = NOTEHEAD_WHOLE
        elif duration.m_nh > 2:
            self.m_head = NOTEHEAD_QUARTER
        else:
            self.m_head = NOTEHEAD_HALF
        self.m_shift = shift
        self.m_numdots = duration.m_dots
        self.m_ypos = ypos
        self.m_midi_int = int(musicalpitch)
    def engrave(self, ct, staff_yoffset):
        dim = dimentions[self.m_fontsize]
        # Have to adjust wholenotes a little to the left to be on the middle
        # of the ledger line.
        if self.m_head == 0:
            xx = -2
        else:
            xx = 0
        ims = cairo.ImageSurface.create_from_png(
            fetadir + '/feta%i-noteheads-%i.png' % (self.m_fontsize, self.m_head))
        ct.set_source_surface(ims, self.m_xpos + self.m_shift * dim.xshift + xx,
            int(staff_yoffset + dim.linespacing * self.m_ypos / 2 - 4))
        ct.paint()
        for n in range(self.m_numdots):
            ims = cairo.ImageSurface.create_from_png(
                fetadir + '/feta20-dots-dot.png')
            ct.set_source_surface(ims, int(self.m_xpos + dim.xshift * (self.m_shift + 1.5 + n/2.0)),
                -3 + staff_yoffset + dim.linespacing * self.m_ypos / 2)
        ct.paint()
    def __str__(self):
        try:
            xpos = self.m_xpos
        except AttributeError:
            xpos = None
        return "(NoteheadEngraver: xpos:%s, ypos:%i, head:%i, shift=%i)" % (
                xpos, self.m_ypos, self.m_head, self.m_shift)
    def __repr__(self):
        try:
            xpos = self.m_xpos
        except AttributeError:
            xpos = None
        return "<NoteheadEngraver xpos:%s, ypos:%i, head:%i, shift=%i>" % (
                xpos, self.m_ypos, self.m_head, self.m_shift)


class BarlineEngraver(Engraver):
    def __init__(self, barline_type):
        Engraver.__init__(self)
        self.m_type = barline_type
    def get_width(self):
        return 8

    def engrave(self, ct, staff_yoffset):
        dim = dimentions[self.m_fontsize]
        ct.move_to(self.m_xpos + 0.5, staff_yoffset - dim.linespacing * 2)
        ct.line_to(self.m_xpos + 0.5, staff_yoffset + dim.linespacing * 2)

class TupletEngraver(Engraver):
    def __init__(self, ratio, direction):
        Engraver.__init__(self)
        self.m_stems = []
        self.m_ratio = ratio
        self.m_direction = direction
    def add_stem(self, stem):
        self.m_stems.append(stem)
    def do_layout(self):
        dim = dimentions[self.m_fontsize]
        top = []
        bottom = []
        for s in self.m_stems:
            if s.m_stemdir == const.UP:
                top.append(min(s.m_yposes)-7)
                bottom.append(max(s.m_yposes)+1)
            else:
                top.append(min(s.m_yposes))
                bottom.append(max(s.m_yposes)+5)
        self.m_t = min(top) - 2
        self.m_b = max(bottom) + 2
        self.m_xpos1 = self.m_stems[0].m_xpos - 2
        self.m_xpos2 = self.m_stems[-1].m_xpos + 2
        if self.m_stems[-1].m_stemdir == const.DOWN:
            self.m_xpos2 += dim.xshift
    def engrave(self, ct, staff_yoffset):
        self.do_layout()
        dim = dimentions[self.m_fontsize]
        m = (self.m_xpos1 + self.m_xpos2) / 2
        if self.m_direction == const.UP or self.m_direction == const.BOTH:
            y = min(staff_yoffset - dim.linespacing * 3,
                   staff_yoffset + self.m_t * dim.linespacing / 2)
            d = 1
        else: # == const.DOWN
            y = max(staff_yoffset + dim.linespacing * 5,
                    staff_yoffset + self.m_b * dim.linespacing /2)
            d = -1
        self.m_xpos1 += 0.5
        self.m_xpos2 += 0.5
        if len(self.m_stems) > 1:
            # left horiz
            ct.move_to(self.m_xpos1, y)
            ct.line_to(m - 6, y)
            # right horiz
            ct.move_to(m + 6, y)
            ct.line_to(self.m_xpos2, y)
            # left vertic
            ct.move_to(self.m_xpos1, y)
            ct.line_to(self.m_xpos1, y + 5 * d)
            # right vertic
            ct.move_to(self.m_xpos2, y)
            ct.line_to(self.m_xpos2, y + 5 * d)
            ct.stroke()
        ct.select_font_face("Sans 10")
        tt = ct.text_extents(str(self.m_ratio.m_den))
        ct.move_to(m - tt[2] / 2, y + tt[3] / 2)
        ct.show_text(str(self.m_ratio.m_den))
        ct.stroke()


class BeamEngraver(Engraver):
    def __init__(self):
        Engraver.__init__(self)
        self.m_stems = []
    def add_stem(self, stem_engraver):
        self.m_stems.append(stem_engraver)
    def do_layout(self):
        # We don't beam single notes. Notes can be single when the dictation
        # exercise tries to display the first note
        if len(self.m_stems) == 1:
            self.m_stems[0].m_is_beamed = False
        self.decide_beam_stemdir()
        self.set_stemlens(self.find_lowhigh_ypos())
    def set_stemlens(self, lh):
        l, h = lh
        for e in self.m_stems:
            if self.m_stemdir == const.UP:
                e.m_beamed_stem_top = l - 6
            else:
                assert self.m_stemdir == const.DOWN
                e.m_beamed_stem_top = h + 6
    def find_lowhigh_ypos(self):
        """
        Find the lowest and highest notehead in the beam.
        """
        mn = 1000
        mx = -1000
        for se in self.m_stems:
            for ylinepos in se.m_yposes:
                if mn > ylinepos:
                    mn = ylinepos
                if mx < ylinepos:
                    mx = ylinepos
        return mn, mx
    def decide_beam_stemdir(self):
        """
        Decide the direction for the stems in this beam, and set
        the stemdir for all stems.
        """
        v = {const.UP: 0, const.DOWN: 0}
        for e in self.m_stems:
            v[e.m_stemdir] = v[e.m_stemdir] + 1
            e.m_stemlen = 50
        if v[const.UP] > v[const.DOWN]:
            stemdir = const.UP
        else:
            stemdir = const.DOWN
        for e in self.m_stems:
            e.m_stemdir = stemdir
        self.m_stemdir = stemdir
    def engrave(self, ct, staff_yoffset):
        # Do nothing if there are only one stem in the beam. Usually this
        # does not happen, but it is possible that a lesson file want to
        # display only the first note in some music, and that note is beamed.
        if len(self.m_stems) == 1:
            return
        dim = dimentions[self.m_fontsize]
        d = 0
        if self.m_stemdir == const.UP:
            d = 1
        else:
            d = -1
        x1 = self.m_stems[0].m_xpos
        x2 = self.m_stems[-1].m_xpos
        if self.m_stems[0].m_beamed_stem_top % 2 == 1:
            for x in range(len(self.m_stems)):
                self.m_stems[x].m_beamed_stem_top = \
                    self.m_stems[x].m_beamed_stem_top - d
        y1 = self.m_stems[0].m_beamed_stem_top * dim.linespacing/2 + staff_yoffset
        beamw = 3
        beaml = 10
        for y in range(beamw):
            ct.move_to(x1, y1 + y*d)
            ct.line_to(x2, y1 + y*d)
        for stem in self.m_stems:
            stem._beam_done = 8
        def short_beam(stem, xdir, beamnum, d=d, beamw=beamw, beaml=beaml, y1=y1):
            for y in range(beamw):
                ct.move_to(stem.m_xpos, y1 + y + beamnum * d * beamw * 2)
                ct.line_to(stem.m_xpos + xdir * beaml, y1 + y + beamnum * d * beamw * 2)
        for nl, yc in ((16, 0), (32, 1), (64, 2)):
            for i in range(len(self.m_stems)-1):
                if self.m_stems[i].m_duration.m_nh >= nl \
                        and self.m_stems[i+1].m_duration.m_nh >= nl:
                    for y in range(beamw):
                        ct.move_to(self.m_stems[i].m_xpos, d*beamw*yc*2 + y1 + y + d*beamw*2)
                        ct.line_to(self.m_stems[i+1].m_xpos, d*beamw*yc*2 + y1 + y + d*beamw*2)
                    self.m_stems[i]._beam_done = nl
                    self.m_stems[i+1]._beam_done = nl
                if self.m_stems[i].m_duration.m_nh >= nl \
                      and self.m_stems[i+1].m_duration.m_nh <= nl/2 \
                      and self.m_stems[i]._beam_done < nl:
                    if i == 0:
                        stemdir = 1
                    else:
                        if self.m_stems[i-1].m_duration.m_nh < \
                           self.m_stems[i+1].m_duration.m_nh:
                            stemdir = 1
                        else:
                            stemdir = -1
                    short_beam(self.m_stems[i], stemdir, yc+1, d)
                    self.m_stems[i]._beam_done = nl
            if self.m_stems[-1].m_duration.m_nh >= nl \
                    and self.m_stems[-1]._beam_done <= nl/2:
                short_beam(self.m_stems[-1], -1, yc+1, d)
        ct.stroke()


class StemEngraver(Engraver):
    """
    Every notehead belong to a stem, even if the stem is invisible.
    """
    def __init__(self, noteheads, duration, stemdir, is_beamed):
        """
        If stemdir == BOTH: Look at the location of the noteheads, and descide
        which way the stem will go. Set m_stemdir to UP or DOWN.
        """
        Engraver.__init__(self)
        self.m_noteheads = noteheads
        # FIXME maybe remove, if m_noteheads will be available anyway
        self.m_yposes = sorted([h.m_ypos for h in noteheads])
        self.m_duration = duration
        self.m_stemdir = stemdir
        self.m_is_beamed = is_beamed
        # descide the stem direction
        if len(self.m_yposes) == 1:
            x = self.m_yposes[0]
        else:
            x = self.m_yposes[0] + self.m_yposes[-1]
        if self.m_stemdir == const.BOTH:
            if x >= 0:
                self.m_stemdir = const.UP
            else:
                self.m_stemdir = const.DOWN
        self.shift_noteheads()
        self.m_stemlen = dimentions[self.m_fontsize].stemlen
    def get_width(self):
        c = 2
        if [n for n in self.m_noteheads if n.m_shift == -1]:
            c += 1
        if [n for n in self.m_noteheads if n.m_shift == 1]:
            c += 1
        return c * dimentions[self.m_fontsize].xshift
    def calc_xpos(self):
        """
        TODO: if we readd m_stempos, it has to be taken into consideration here.
        """
        if self.m_stemdir == const.UP:
            self.m_xpos += dimentions[self.m_fontsize].xshift
        if [n for n in self.m_noteheads if n.m_shift == -1]:
            self.m_xpos += dimentions[self.m_fontsize].xshift
            for n in self.m_noteheads:
                n.m_xpos += dimentions[self.m_fontsize].xshift
    def engrave(self, ct, staff_yoffset):
        dim = dimentions[self.m_fontsize]
        if self.m_duration.m_nh < 2:
            return
        # draw flags
        if not self.m_is_beamed and self.m_duration.m_nh > 4:
            if self.m_stemdir == const.UP:
                ims = cairo.ImageSurface.create_from_png(
                    fetadir + '/feta%i-flags-%s.png' %
                    (self.m_fontsize, self.get_flag(const.UP)))
                ct.set_source_surface(ims, self.m_xpos,
                    int(staff_yoffset - self.m_stemlen + self.m_yposes[0] * dim.linespacing/2))
            else:
                ims = cairo.ImageSurface.create_from_png(
                    fetadir + '/feta%i-flags-%s.png'
                    % (self.m_fontsize, self.get_flag(const.DOWN)))
                ct.set_source_surface(ims, self.m_xpos,
                    int(staff_yoffset + 4 + self.m_yposes[-1] * dim.linespacing/2))
        # draw stem
        if self.m_stemdir == const.DOWN:
            if self.m_is_beamed:
                yroot = self.m_beamed_stem_top
            else:
                yroot = self.m_yposes[-1] + 6
            ytop = self.m_yposes[0]
        else:
            if self.m_is_beamed:
                yroot = self.m_beamed_stem_top
            else:
                yroot = self.m_yposes[0] - 6
            ytop = self.m_yposes[-1]
        ct.move_to(self.m_xpos, ytop * dim.linespacing / 2 + staff_yoffset)
        ct.line_to(self.m_xpos, yroot * dim.linespacing / 2 + staff_yoffset)
    def get_flag(self, stemdir):
        assert self.m_duration.m_nh > 4
        return {8:{const.UP: FLAG_8UP,
                   const.DOWN: FLAG_8DOWN},
                16: {const.UP: FLAG_16UP,
                     const.DOWN: FLAG_16DOWN},
                32: {const.UP: FLAG_32UP,
                     const.DOWN: FLAG_32DOWN},
                64: {const.UP: FLAG_64UP,
                     const.DOWN: FLAG_64DOWN}} \
                              [self.m_duration.m_nh][stemdir]
    def shift_noteheads(self):
        """
        We need to look at all stems at the same timepos in the staff when
        shifting note heads. An integer value say if and in which direction
        a note head is shifted. The value 0 means that the note head is in
        its default position. In default position, the noteheads
        on stems pointing UP are to the left of the stem and noteheads on
        stems pointing DOWN on the right of the stem. And they are all
        aligned below each other.

        A positive shift value means that the head is moved to the right,
        and a negative is to the left. The unit is notehead-widths, so
        the common (and for now only used) value is -1 for noteheads on
        down-stems and +1 for noteheads on up-stems.
        """
        self.m_noteheads.sort(lambda a, b: cmp(a.m_ypos, b.m_ypos))
        # TODO: handle crashing noteheads in two different voices.

        # When laying out noteheads, we start with the notehead at the
        # end of the stem. That will always be unshifted.
        if self.m_stemdir == const.UP:
            heads = list(reversed(self.m_noteheads))
        else:
            heads = self.m_noteheads
        last_ypos = None
        for idx, head in enumerate(heads):
            if last_ypos is not None:
                if abs(last_ypos - head.m_ypos) == 1 and heads[idx - 1].m_shift == 0:
                    head.m_shift = 1 if self.m_stemdir == const.UP else -1
                elif last_ypos == head.m_ypos:
                    head.m_shift = 1 if self.m_stemdir == const.UP else -1
            last_ypos = head.m_ypos
    def __str__(self):
        return "(StemEngraver)"
    def __repr__(self):
        return "<StemEngraver xpos:%s>" % (
                self.m_xpos, )


class LedgerLineEngraver(Engraver):
    def __init__(self, up, down):
        """
        up: number of ledger lines above staff
        down: number of ledger lines below staff
        """
        Engraver.__init__(self)
        self.m_xpos = 0
        self.m_up = up
        self.m_down = down
    def engrave(self, ct, staff_yoffset):
        dim = dimentions[self.m_fontsize]
        if self.m_up:
            for y in range(self.m_up):#FIXME use rel_line_to
                ct.move_to(self.m_xpos+dim.ledger_left, (-y-3) * dim.linespacing + staff_yoffset)
                ct.line_to(self.m_xpos+dim.ledger_right, (-y-3) * dim.linespacing + staff_yoffset)
        if self.m_down:
            for y in range(self.m_down):
                ct.move_to(self.m_xpos+dim.ledger_left, (y+3) * dim.linespacing + staff_yoffset)
                ct.line_to(self.m_xpos+dim.ledger_right, (y+3) * dim.linespacing + staff_yoffset)
        ct.stroke()
    def __str__(self):
        return "(LedgerLineEngraver xpos:%i, updown%i%i" % (
            self.m_xpos, self.m_up, self.m_down)
    def __repr__(self):
        return "<LedgerLineEngraver xpos:%i, updown%i:%i>" % (
            self.m_xpos, self.m_up, self.m_down)


class RestEngraver(Engraver):
    def __init__(self, ypos, dur):
        Engraver.__init__(self)
        self.m_ypos = ypos
        self.m_dots = dur.m_dots
        self.m_type = {1: 0, 2: 1, 4: 2, 8: 3, 16: 4, 32: 5, 64: 6}[dur.m_nh]

    def get_width(self):
        #FIXME write me!
        return 20

    def engrave(self, ct, staff_yoffset):
        dim = dimentions[self.m_fontsize]
        if self.m_type == 0:
            my = dim.linespacing / 2
        else:
            my = 0
        ims = cairo.ImageSurface.create_from_png(
            fetadir+'/feta%i-rests-%i.png' % (self.m_fontsize, self.m_type))
        ct.set_source_surface(
            ims, self.m_xpos,
            int(staff_yoffset - my + dim.linespacing*self.m_ypos / 2 - 4))
        ct.paint()
        for n in range(self.m_dots):
            ims = cairo.ImageSurface.create_from_png(fetadir+'/feta20-dots-dot.xpm')
            ct.set_source_surface(
                int(self.m_xpos+dim.xshift*(1.5+n/2.0)),
                -3 + staff_yoffset + dim.linespacing*self.m_ypos/2)
            ct.paint()
    def __str__(self):
        return "(RestEngraver)"


class SkipEngraver(Engraver):
    def __init__(self, duration):
        Engraver.__init__(self)
        self.m_duration = duration
    def engrave(self, ct, staff_yoffset):
        pass


class _StaffCommon(list):
    def __init__(self, staff, last_timepos):
        """
        Create engraver objects for the staff, one timepos at the time.
        Append them to self, and add refs to them in the m_engravers dict
        to access them by timepos and type.
        """
        list.__init__(self)
        self.m_label = getattr(staff, 'm_label', None)
        self.m_engravers = {}
        # When joining two empty Scores with Score.concat2, we need to return
        # to avoid IndexErrors further down this method.
        if not staff.w_parent().m_bars:
            return
        # make a set of all timeposes in the staffs voices
        t = set()
        # We need to add the timepos of the beginning of all bars, since
        # all staffs has to display the time signature if it changes. Normally
        # it is not necessary to do this here, since staff.m_tdict will have
        # the timepos. But it is necessary for Scores created by Score.concat2
        [t.add(b.m_timepos) for b in staff.w_parent().m_bars]
        # Then we add the timepos of all notes and rests
        [t.add(tp) for tp in staff.m_tdict]
        for voice in staff.m_voices:
            [t.add(tp) for tp in voice.m_tdict]
        if last_timepos is None:
            # display all notes
            timeposes = sorted(t)
        else:
            timeposes = [x for x in sorted(t) if x < last_timepos]
        #
        clef = None
        keysig = ("c", "major")
        self.refill_accidentals_info(keysig)
        for voice in staff.m_voices:
            # tmp variable needed to keep track of the beams. Deleted at method exit.
            voice.m_beam = None
            voice.m_ties = {}
            # tuplet
            voice.m_tuplet = None
        bar_idx = 0
        props = {
            'hide-timesignature': False,
        }
        beams = []
        for timepos in timeposes:
            if (bar_idx < len(staff.w_parent().m_bars) -1
                  and timepos == staff.w_parent().m_bars[bar_idx + 1].m_timepos):
                bar_idx += 1
            if timepos not in self.m_engravers:
                self.m_engravers[timepos] = {}
            eng = self.m_engravers[timepos]
            ##############
            # Properties #
            ##############
            if (timepos in staff.m_tdict
                    and 'properties' in staff.m_tdict[timepos]):
                props.update(staff.m_tdict[timepos]['properties'])
            # Forget accidentals at bar lines
            if timepos == staff.w_parent().m_bars[bar_idx].m_timepos:
                self.refill_accidentals_info(keysig)
            ########
            # Clef #
            ########
            if timepos in staff.m_tdict and 'clef' in staff.m_tdict[timepos]:
                clef = staff.m_tdict[timepos]['clef']
                eng['clef'] = ClefEngraver(staff.m_tdict[timepos]['clef'])
                self.append(eng['clef'])
            #################
            # Key signature #
            #################
            if timepos in staff.m_tdict and 'keysig' in staff.m_tdict[timepos]:
                eng['keysig'] = KeySignatureEngraver(keysig,
                    staff.m_tdict[timepos]['keysig'], clef)
                self.append(eng['keysig'])
                keysig = staff.m_tdict[timepos]['keysig']
                self.refill_accidentals_info(keysig)
            ##################
            # Time signature #
            ##################
            if not staff.w_parent().m_bars:
                return
            if (props['hide-timesignature'] == False
                and ((timepos == staff.w_parent().m_bars[bar_idx].m_timepos
                and bar_idx > 0
                and staff.w_parent().m_bars[bar_idx].m_timesig
                 != staff.w_parent().m_bars[bar_idx - 1].m_timesig) or timepos == elems.TimeSignature(0, 1))):
                eng['timesig'] = TimeSignatureEngraver(staff.w_parent().m_bars[bar_idx].m_timesig)
                self.append(eng['timesig'])
            ###############
            # Accidentals #
            ###############
            if isinstance(self, StaffContext):
                v = {}
                for voice in staff.m_voices:
                    if timepos not in voice.m_tdict:
                        continue
                    # If the 'elem' is a rest or skip,
                    # then there are no accidentals.
                    if isinstance(voice.m_tdict[timepos]['elem'][0],
                            (elems.Rest, elems.Skip)):
                        continue
                    for elem in voice.m_tdict[timepos]['elem']:
                        e = self.needed_accidental(elem.m_musicalpitch)
                        if e is not None:
                            v[clef.steps_to_ylinepos(elem.m_musicalpitch.steps())] = e
                if v:
                    self.append(AccidentalsEngraver(v))
                    eng['accidentals'] = self[-1]
            ############################################
            # Create stems, noteheads and ledger lines #
            ############################################
            # These two count show many ledger lines we need.
            yline_up = 0
            yline_down = 0
            for voice in staff.m_voices:
                if timepos not in voice.m_tdict:
                    continue
                if 'elem' in voice.m_tdict[timepos]:
                    elem = voice.m_tdict[timepos]['elem']
                    if isinstance(elem, elems.Stem):
                        if elem.m_beaminfo == 'start':
                            voice.m_beam = BeamEngraver()
                            beams.append(voice.m_beam)
                            self.append(voice.m_beam)
                        # If the tuplet contain only one tone, then elem.m_tupletinfo == 'end' and
                        # voice.m_tuplet will be None
                        if elem.m_tupletinfo == 'start' or (elem.m_tupletinfo == 'end' and voice.m_tuplet == None):
                            voice.m_tuplet = TupletEngraver(elem.m_tuplet_ratio, elem.m_tuplet_dir)
                    if 'elem' not in eng:
                        eng['elem'] = []
                    if isinstance(voice.m_tdict[timepos]['elem'][0], elems.Rest):
                        e = RestEngraver(0, voice.m_tdict[timepos]['elem'][0].m_duration)
                        self.append(e)
                        eng['elem'].append(e)
                    elif isinstance(elem[0], elems.Skip):
                        e = SkipEngraver(elem[0].m_duration)
                        self.append(e)
                        eng['elem'].append(e)
                    elif not isinstance(voice.m_tdict[timepos]['elem'][0], elems.Skip):
                        elist, stemengraver = self.create_notehead_engraver(clef, voice.m_tdict[timepos]['elem'])
                        for note, engraver in zip(voice.m_tdict[timepos]['elem'], elist):
                            if note.m_tieinfo == 'start':
                                voice.m_ties[note.m_musicalpitch.get_octave_notename()] = engraver
                            elif note.m_tieinfo == 'go':
                                self.append(TieEngraver(voice.m_ties[note.m_musicalpitch.get_octave_notename()], engraver))
                                del voice.m_ties[note.m_musicalpitch.get_octave_notename()]
                                voice.m_ties[note.m_musicalpitch.get_octave_notename()] = engraver
                            elif note.m_tieinfo == 'end':
                                self.append(TieEngraver(voice.m_ties[note.m_musicalpitch.get_octave_notename()], engraver))
                                del voice.m_ties[note.m_musicalpitch.get_octave_notename()]
                        if voice.m_beam:
                            stemengraver.m_is_beamed = True
                            voice.m_beam.add_stem(stemengraver)
                        if voice.m_tuplet:
                            voice.m_tuplet.add_stem(stemengraver)
                        eng['elem'].extend(elist)
                        eng['elem'].append(stemengraver)
                        self.extend(elist)
                        self.append(stemengraver)
                    if isinstance(elem, elems.Stem):
                        if elem.m_beaminfo == 'end':
                            voice.m_beam = None
                        if elem.m_tupletinfo == 'end':
                            self.append(voice.m_tuplet)
                            voice.m_tuplet = None
                # Ledger lines
                for elem in voice.m_tdict[timepos]['elem']:
                    if isinstance(elem, elems.Note):
                        if not clef:
                            # clef is None on a rhythm staff. Then we need no
                            # ledger lines
                            continue
                        ypos = clef.steps_to_ylinepos(elem.m_musicalpitch.steps())
                        if yline_up > ypos < -5:
                            yline_up = ypos
                        if yline_down < ypos > 5:
                            yline_down = ypos
            if yline_up:
                yline_up = - yline_up / 2 - 2
            if yline_down:
                yline_down = yline_down / 2 - 2
            if yline_up or yline_down:
                e = LedgerLineEngraver(yline_up, yline_down)
                eng['elem'].append(e)
                self.append(e)
        # We do this here instead of further up where we check for'
        # if m_beaminfo == 'end' because we need to do do_layout for beams
        # even when we only want to engrave the first note in a beam.
        for b in beams:
            b.do_layout()


class StaffContext(_StaffCommon):
    def refill_accidentals_info(self, key):
        """Fill the .m_accidentals_info dict with the accidentals
        that exist in the key signature `key`.
        """
        self.m_accidentals_info = {}
        for step in range(MusicalPitch.LOWEST_STEPS, MusicalPitch.HIGHEST_STEPS+1):
            self.m_accidentals_info[step] = 0
        for a in mpdutils.key_to_accidentals(key):
            n = MusicalPitch.new_from_notename(a)
            for octave in range(-4, 7):
                n.m_octave_i = octave
                if n.semitone_pitch() < 128:
                    if a[-4:] == 'eses':
                        self.m_accidentals_info[n.steps()] = -2
                    elif a[-2:] == 'es':
                        self.m_accidentals_info[n.steps()] = -1
                    elif a[-4:] == 'isis':
                        self.m_accidentals_info[n.steps()] = 2
                    else:
                        self.m_accidentals_info[n.steps()] = 1
    def needed_accidental(self, m):
        steps = m.steps()
        if m.m_accidental_i != self.m_accidentals_info[steps]:
            if (self.m_accidentals_info[steps] == 2 and m.m_accidental_i == 1) \
                    or (self.m_accidentals_info[steps] == -2 and m.m_accidental_i == -1):
                self.m_accidentals_info[steps] = m.m_accidental_i
                return [0, m.m_accidental_i]
            self.m_accidentals_info[steps] = m.m_accidental_i
            return [m.m_accidental_i]
    def create_notehead_engraver(self, clef, elements):
        """
        Return a two item
        1: Return a list of the engravers that draw the note heads
        2: The stem engraver
        Will return the engravers in the same order as the notes in elements.
        """
        noteheads = []
        for elem in elements:
            noteheads.append(NoteheadEngraver(
            0, # shift,
            clef.steps_to_ylinepos(elem.m_musicalpitch.steps()),  # ypos,
            elem.m_musicalpitch,
            elem.m_duration))
        return (noteheads,
            StemEngraver(noteheads, elements[0].m_duration, elements.m_stemdir, False))


class RhythmStaffContext(_StaffCommon):
    """
    Typeset notes on a single line. Pitches are ignored.
    """
    def refill_accidentals_info(self, key):
        """
        nop since we don't care about pitches.
        """
        return
    def create_notehead_engraver(self, clef, elem):
        """
        Return a two item
        1: Return a list of the engravers that draw the note heads
        2: The stem engraver
        """
        notehead = NoteheadEngraver(
            0, # shift,
            0, # ypos,
            elem[0].m_musicalpitch,
            elem[0].m_duration)
        return [notehead], StemEngraver([notehead], elem[0].m_duration, elem.m_stemdir, False)

class ScoreContext(object):
    def __init__(self, score, last_timepos=None):
        t = set()
        self.m_contexts = staff_contexts = []
        # Create one staff context for each staff line.
        for staff in score.m_staffs:
            if isinstance(staff, elems.RhythmStaff):
                staff_contexts.append(RhythmStaffContext(staff, last_timepos))
            else:
                staff_contexts.append(StaffContext(staff, last_timepos))
            [t.add(timepos) for timepos in staff_contexts[-1].m_engravers]
        # BarlineEngravers have the timepos of the beginning of the next
        # bar. So the last bar line will have the timepos of where the
        # bar after the last bar would begin. We need to add that timepos
        # to the set 't' because it is not added by the above loop.
        if score.m_bars:
            t.add(score.m_bars[-1].end())
        # Initialize the property dict for each staff.
        for staff_context in staff_contexts:
            staff_context.props = {
                'hide-barline': False,
            }
        xpos = 0
        bar_idx = 0
        # This loop will set the m_xpos variable for all engraver objects
        for timepos in sorted(t):
            ########################
            # Per score properties #
            ########################
            for staff_context, staff in zip(staff_contexts, score.m_staffs):
                if (timepos in staff.m_tdict
                        and 'properties' in staff.m_tdict[timepos]):
                    staff_context.props.update(staff.m_tdict[timepos]['properties'])
            if timepos == score.m_bars[bar_idx].end():
                bar = score.m_bars[bar_idx]
                for staff_context in staff_contexts:
                    if not staff_context.props['hide-barline']:
                        e = BarlineEngraver("|")
                        staff_context.append(e)
                        staff_context.m_engravers.setdefault(
                            score.m_bars[bar_idx].end(), {})['barline'] = e
                bar_idx += 1
            def do_col(s, xpos):
                max_width = 0
                for context in staff_contexts:
                    if timepos not in context.m_engravers:
                        continue
                    if s in context.m_engravers[timepos]:
                        context.m_engravers[timepos][s].m_xpos = xpos
                        max_width = max(max_width, context.m_engravers[timepos][s].get_width())
                return max_width
            xpos += do_col('barline', xpos)
            xpos += do_col('clef', xpos)
            xpos += do_col('keysig', xpos)
            xpos += do_col('timesig', xpos)
            xpos += do_col('accidentals', xpos)
            # Elems
            max_width = 0
            for context in staff_contexts:
                if timepos not in context.m_engravers:
                    continue
                if 'elem' in context.m_engravers[timepos]:
                    for e in context.m_engravers[timepos]['elem']:
                        e.m_xpos = xpos
                        if isinstance(e, StemEngraver):
                            e.calc_xpos()
                    max_width = max(max_width, max(
                        [e.get_width() for e in context.m_engravers[timepos]['elem']]))
            xpos += max_width

