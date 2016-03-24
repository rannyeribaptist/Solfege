# GNU Solfege - free ear training software
# vim: set fileencoding=utf-8 :
# Copyright (C) 2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2011 Tom Cato Amundsen
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

import glob
import locale
import logging
import os
import random
import re
import stat
import subprocess
import sys
import textwrap

from gi.repository import GObject

from solfege import cfg
from solfege import dataparser
from solfege import filesystem
from solfege import lfmod
from solfege import mpd
from solfege import osutils
from solfege import parsetree as pt
from solfege import soundcard
from solfege import utils
from solfege import uuid
from solfege import xrandom
from solfege.dataparser import istr
from solfege.mpd import elems
from solfege.mpd import Duration
from solfege.mpd import Rat

_test_mode = False

# The name of the folder containing the standard learning trees.
# Relative to the installation dir.
exercises_dir = os.path.join(u"exercises", u"standard")
_abs_exercises_dir = os.path.join(os.getcwdu(), exercises_dir) + os.sep

solfege_uri = u"solfege:"

def uri_expand(url):
    """
    Convert from solfege: URI to normal file name.
    """
    assert isinstance(url, unicode)
    if url.startswith(solfege_uri):
        url = os.path.join(exercises_dir, url[len(solfege_uri):])
    return url

def mk_uri(filename):
    """
    Make an URI
    solfege:path/to/file
    that refers to files in exercises/ if the file is below that directory.
    Return unchanged if not.
    """
    if os.path.isabs(filename):
        if filename.startswith(_abs_exercises_dir):
            return (u"solfege:%s" % filename[len(_abs_exercises_dir):]).replace(os.sep, "/")
    else:
        if filename.startswith(u"%s%s" % (exercises_dir, os.sep)):
            return (u"solfege:%s" % filename[len("%s%s" % (exercises_dir, os.sep)):]).replace(os.sep, "/")
    return filename

def is_uri(filename):
    return filename.startswith(solfege_uri)

class LessonfileException(Exception):
    pass

class MusicObjectException(LessonfileException):
    pass

class LessonfileParseException(Exception):
    pass

class NoQuestionsInFileException(LessonfileParseException):
    """
    Raised by find_random_question if the lesson file contains
    no questions at all.
    """
    def __init__(self, lessonfilename):
        LessonfileParseException.__init__(self, _("The lesson file contains no questions"))

class FileNotFound(LessonfileException):
    def __init__(self, filename):
        LessonfileException.__init__(self, _("The external file '%s' was not found") % filename)

class NoQuestionsConfiguredException(LessonfileException):
    """
    This exception is raised by select_random_question if the user has
    unselected all the questions available in the lesson file.
    """
    def __init__(self):
        LessonfileException.__init__(self,
            _("No questions selected"),
            _("You can select questions on the config page of the exercise."))


# The keys in the dict say how many steps up or down in the
# circle of fifths we go if we transpose.
_keys_to_interval = {
              -10: '-M6', #c -> eses
               -9: '-a2', #c -> beses
               -8: '-a5', #c -> fes
               -7: '-a1', #c -> ces
               -6: '-a4', #c -> ges
               -5: 'm2', # c -> des
               -4: '-M3',# c -> as
               -3: 'm3', # c -> es
               -2: '-M2', # c -> bes
               -1: 'p4', # c -> f
                0: 'p1',
                1: '-p4', # c -> g,
                2: 'M2', # c -> d
                3: '-m3',# c -> a
                4: 'M3', # c -> e
                5: '-m2', # c -> b
                6: 'a4', # c -> fis
                7: 'a1', #c -> cis
                8: 'a5', # c -> gis
                9: 'a2', # c -> dis
                10: 'M6', # c -> ais
            }


def load_text(parser, filename):
    """
    The parser object is the Dataparser object that is calling this
    function.
    """
    f = open(os.path.join(parser.m_location, filename), 'r')
    s = f.read()
    f.close()
    return s

class nrandom(object):
    def __init__(self, v):
        if len(v) == 1 and type(v[0]) == list:
            v = v[0]
        self.m_list = v
        self.randomize()
    def __str__(self):
        return self.m_list[self.m_idx]
    def randomize(self):
        self.m_idx = random.randint(0, len(self.m_list) - 1)

class prandom(nrandom):
    """
    Every call to __str__ will randomize.
    """
    def __str__(self):
        self.randomize()
        return self.m_list[self.m_idx]

class LabelObject(object):
    def __init__(self, labeltype, labeldata):
        self.m_labeltype = labeltype
        self.m_labeldata = labeldata
    def __getattr__(self, name):
        if name == 'cval':
            return (self.m_labeltype, self.m_labeldata)

lessonfile_builtins = {
           #  (need_parser, function)
        '_': (False, dataparser.dataparser_i18n_func),
        '_i': (False, dataparser.dataparser_i18n__i_func),
        'load': (True, load_text),
        'nrandom': (False, lambda *v: nrandom(v)),
        'prandom': (False, lambda *v: prandom(v)),
        # play_wav should probably be removed. Replaced by wavfile
        'play_wav': (False, lambda f: Wavfile(f)),
        'music': (False, lambda m: Music(m)),
        'music3': (False, lambda m: Music3(m)),
        'chord': (False, lambda m: Chord(m)),
        'satb': (False, lambda m: Satb(m)),
        'voice': (False, lambda m: Voice(m)),
        'rvoice': (False, lambda m: Rvoice(m)),
        'rhythm': (False, lambda m: Rhythm(m)),
        'percussion': (False, lambda m: Percussion(m)),
        'cmdline': (False, lambda m: Cmdline(m)),
        'csound': (False, lambda orc, sco: CSound(orc, sco)),
        'wavfile': (False, lambda m: Wavfile(m)),
        'midifile': (False, lambda m: Midifile(m)),
        'mp3file': (False, lambda m: Mp3file(m)),
        'oggfile': (False, lambda m: Oggfile(m)),
        'mma': (False, lambda *v: Mma(*v)),
        'progressionlabel': (False, lambda s: LabelObject("progressionlabel", s)),
        'pangomarkup': (False, lambda s: LabelObject("pangomarkup", s)),
        'rnc': (False, lambda s: LabelObject("rnc", s)),
        'chordname': (False, lambda s: LabelObject("chordname", s)),
    'tempo': (60, 4),
    'yes': True,
    'no': False,
}


def rnc_markup_tokenizer(s):
    """
    [rn][mod1][num][\s-]
    """
    rn_re = re.compile(u"""(?P<p1>[b♭♯#]?[ivIV]+)
                          (?P<p2>[^\d\s-]*)
                          (?P<p3>[^\s-]*)
                          (?P<sep>(\s*-\s*|\s*))""",
                       re.VERBOSE|re.UNICODE)
    i = 0
    retval = []
    while i < len(s):
        m = rn_re.match(s[i:])
        if not m:
            retval.append((u'ERR:%s' % s[i:], '', '', ''))
            break
        retval.append((m.group('p1'), m.group('p2'), m.group('p3'), m.group('sep')))
        i += m.end()
    return retval

def chordname_markup_tokenizer(s):
    """
    s argument is a string of white-space separated chords.
    Each chord is in the following format
    [notename][whatever-text-in-normal-font-size]:[whatever-text-in-superscript-font][/notename]
    [notename] is a solfege internal format notename, c cis des fis bes etc...
    c
    caug    (allow c+ ??)
    cm:9
    c:11b9/g
    """
    r = re.compile("""(?P<nn>[cdefgab](es|is)*)
                (?P<txt1>.*?)
                (:
                 (?P<sup>.*?))?
                $
                """, re.VERBOSE)
    retval = []
    for c in s.split():
        v = c.split("/")
        if len(v) > 1:
            try:
                mpd.MusicalPitch.new_from_notename(v[-1])
                bass = v[-1]
                c = "/".join(v[:-1])
            except mpd.InvalidNotenameException, e:
                bass = ""
        else:
            bass = ""
        m = r.match(c)
        if m:
            txt1 = m.group('txt1')
            if not txt1:
                txt1 = ""
            sup = m.group('sup')
            if not sup:
                sup = ""
            retval.append((m.group('nn'), txt1, sup, bass))
        else:
            retval.append(('ERR', '', '', ''))
    return retval

class _Header(dict):
    def __init__(self, headerdict):
        dict.__init__(self, headerdict)
        for key, value in (
                           ('version', ''),
                           ('title', ''),
                           ('description', ''),
                           ('musicformat', 'normal'),
                           ('random_transpose', (True,)),
                           ('labelformat', 'normal'),
                           ('fillnum', 1),
                           ('filldir', 'horiz'),
                           ('have_repeat_slowly_button', False),
                           ('have_repeat_arpeggio_button', False),
                           ('at_question_start', []),
                           ('have_music_displayer', False),
                           ('enable_right_click', True),
                           ('disable_unused_intervals', True),
                           ('statistics_matrices', 'enabled'),
                           ):
            if key not in self:
                self[key] = value
    def __getattr__(self, name):
        """
        This function let us write

          header.variable_name

        as a shortcut or:

            header['variable_name']
        """
        if name in self:
            return self[name]
        return istr("")
    def __setattr__(self, name, value):
        self[name] = value

class MusicBaseClass(object):
    """
    MusicBaseClass.temp_dir should be set by the application before
    we create any instances. Any subclasses of MusicBaseClass that need
    to write temporary files, should write then to this directory.

    Music types that want to do some randomization for each new
    question should implement a .randomize method. One type that does
    this is Mma.
    """
    temp_dir = None
    def __init__(self, musicdata):
        self.m_musicdata = musicdata
    def get_mpd_music_string(self, lessonfile_ref):
        return "%s:%s" % (self.__class__.__name__, self.m_musicdata)


class MpdParsable(MusicBaseClass):
    """
    MpdParsable implements two generic play and play_slowly methods
    that can play the music if the subclass implements get_mpd_music_string.
    Music classes with more special needs will overwrite these play methods.
    """
    def play(self, lessonfile_ref, question):
        assert isinstance(lessonfile_ref, LessonfileCommon)
        instrument = lessonfile_ref.get_instruments(question, 1)
        # We have to call get_mpd_string outside the try: block because
        # the exceptions raised by get_mpd_string has indexes relative to
        # self.m_musicdata, and utils.play_music will raise exceptions
        # with indexes relative to the complete mpd code (including the
        # \staff codes etc.
        mpdstring = self.get_mpd_music_string(lessonfile_ref)
        try:
            if len(instrument) == 2:
                utils.play_music(mpdstring,
                    lessonfile_ref.get_tempo(),
                    instrument[0],
                    instrument[1])
            else:
                utils.play_music3(mpdstring,
                    lessonfile_ref.get_tempo(),
                    instrument)
        except mpd.MpdException, e:
            self.complete_to_musicdata_coords(lessonfile_ref, e)
            raise
        if _test_mode:
            return self.get_mpd_music_string(lessonfile_ref)
    def play_slowly(self, lessonfile_ref, question):
        assert isinstance(lessonfile_ref, LessonfileCommon)
        instrument = lessonfile_ref.get_instrument(question)
        tempo = lessonfile_ref.get_tempo()
        tempo = (tempo[0]/2, tempo[1])
        utils.play_music(self.get_mpd_music_string(lessonfile_ref),
            tempo, instrument[0], instrument[1])
        if _test_mode:
            return self.get_mpd_music_string(lessonfile_ref)
    def get_err_context(self, exception, lessonfile_ref):
        """
        This functions expect exception.m_lineno, .m_linepos1 and .m_linepos2
        to be set relative to the m_musicdata of the music object,
        and not relative to the complete mpd string with added \staff{ } etc.

        Return a twoline string showing what caused the exception.
        """
        if hasattr(exception, 'm_obj_lineno'):
            return "\n".join((self.m_musicdata.split("\n")[exception.m_obj_lineno],
            " " * exception.m_linepos1 + "^" * (exception.m_linepos2 - exception.m_linepos1)))
        return self._mpd_err_context(exception, lessonfile_ref)
    def _mpd_err_context(self, exception, lessonfile_ref):
        m = self.get_mpd_music_string(lessonfile_ref)
        v = m.split("\n")
        v = textwrap.wrap("Bad input to the music object of type %s made the parser fail to parse the following generated music code:" % self.__class__.__name__.lower(), 50) + v[:exception.m_lineno+1] + [" " * exception.m_linepos1 + "^" * (exception.m_linepos2 - exception.m_linepos1)] + v[exception.m_lineno+1:]
        return "\n".join(v)
    def complete_to_musicdata_coords(self, lessonfile_ref, exception):
        """
        The string from m_musicdata should always begin
        on line 1 (0-indexed) of column 0.

        This function modifies m_lineno, m_linepos1 and m_linepos2 so that
        get_err_context can create an ok error message.
        """
        # These two lines are just for extra checking...
        assert not hasattr(exception, '_coords_done')
        exception._coords_done = True
        if (exception.m_lineno > self.m_musicdata.count("\n") + 1
            or exception.m_lineno == 0):
            # Do not set m_obj_lineno since the error happened in the
            # added music code, not in the m_musicdata code.
            return
        exception.m_obj_lineno = exception.m_lineno - 1
    def get_score(self, lessonfile_ref, as_name=None):
        """
        Return a elems.Score object of the music object. Report the variable
        named by the as_name variable as the music object variable with the
        bug if a MpdException is raised.
        """
        try:
            return mpd.parser.parse_to_score_object(self.get_mpd_music_string(lessonfile_ref))
        except mpd.MpdException, e:
            if as_name:
                e.m_mpd_varname = as_name
            raise


class MpdDisplayable(MpdParsable):
    pass


class MpdTransposable(MpdDisplayable):
    def get_first_pitch(self):
        lexer = mpd.parser.Lexer(self.m_musicdata)
        for toc, toc_data in lexer:
            if toc == mpd.parser.Lexer.NOTE:
                return toc_data.m_pitch
        # We will display the first 3 non-empty lines
        v = [x.strip() for x in self.m_musicdata.split("\n") if x]
        v = v[:3]
        raise MusicObjectException("%s\n%s" %
            ("get_first_pitch() could not find a musical pitch in the music data:",
             "\n".join(v)))
    def get_musicdata_transposed(self, lessonfile_ref):
        """
        Return m_musicdata, but transposed relative to
        lesonfile_ref.m_transpose. All pitches identified as Lexer.NOTE
        are transposed.
        """
        assert lessonfile_ref.m_transpose
        try:
            lex = mpd.parser.Lexer(self.m_musicdata)
            tokens = list(mpd.parser.Lexer(self.m_musicdata))
        except mpd.InvalidNotenameException, e:
            self.complete_to_musicdata_coords(lessonfile_ref, e)
            raise
        for toc, toc_data in tokens:
            if isinstance(toc_data, mpd.requests.MusicRequest):
                toc_data.m_pitch.transpose_by_musicalpitch(lessonfile_ref.m_transpose)
        return mpd.parser.Lexer.to_string(tokens)
    def relative_transpose_musicdata(self, lessonfile_ref):
        """
        Also remove octave changes from the first tone.
        """
        assert lessonfile_ref.m_transpose
        tokens = list(mpd.parser.Lexer(self.m_musicdata))
        first = True
        for toc, toc_data in tokens:
            if isinstance(toc_data, mpd.requests.MusicRequest):
                orig_octave = toc_data.m_pitch.m_octave_i
                n = toc_data.m_pitch.transpose_by_musicalpitch(lessonfile_ref.m_transpose)
                n.m_octave_i = orig_octave
                if not first:
                    n.m_octave_i = orig_octave
                else:
                    n.m_octave_i = 0
                    first = False
                toc_data.m_pitch = n
        return mpd.parser.Lexer.to_string(tokens)


class ChordCommon(MpdTransposable):
    pass

class Chord(ChordCommon):
    def get_lilypond_code(self, lessonfile_ref):
        if lessonfile_ref.header.random_transpose[0] == 'atonal':
            music = r"  { <%s> }" % self.get_musicdata_transposed(lessonfile_ref)
        else:
            music = r"\transpose c' %s{ <%s> }" % (
                lessonfile_ref.m_transpose.get_octave_notename(),
                self.m_musicdata)
        return r"\score{ "\
               r" %s"\
               r" \layout { "\
               r"  ragged-last = ##t "\
               r'  \context { \Staff \remove "Time_signature_engraver" } '\
               r" }"\
               r"}"  % music
    def get_lilypond_code_first_note(self, lessonfile_ref):
        if lessonfile_ref.header.random_transpose[0] == 'atonal':
            return r"{ %s }" % self.get_musicdata_transposed(lessonfile_ref).split()[0]
        return r"\transpose c' %s{ %s }" % (
            lessonfile_ref.m_transpose.get_octave_notename(),
            self.m_musicdata.split()[0])
    def get_mpd_music_string(self, lessonfile_ref):
        assert isinstance(lessonfile_ref, LessonfileCommon)
        if lessonfile_ref.header.random_transpose[0] == 'atonal':
            return "\\staff{<\n%s\n>}" % self.get_musicdata_transposed(lessonfile_ref)
        if lessonfile_ref.header.random_transpose[0]:
            return "\\staff\\transpose %s{<\n%s\n>}" \
                % (lessonfile_ref.m_transpose.get_octave_notename(),
                   self.m_musicdata)
        return "\\staff{<\n%s\n>}" % self.m_musicdata
    def strip_trailing_digits(self, s):
        # Used by get_music_as_notename_list
        while '0' <= s[-1] <= '9':
            s = s[:-1]
        return s
    def get_music_as_notename_list(self, lessonfile_ref):
        """
        This method will validate the notenames, and raise a
        mpd.musicalpitch.InvalidNotenameException with the
        m_linepos1, m_linepos2 og m_lineno.
        """
        assert isinstance(lessonfile_ref, LessonfileCommon)
        # We strip the trailing digits to allow chords with length modifiers,
        # like chord("c'2 e").
        notenames = [self.strip_trailing_digits(n) for n in self.m_musicdata.split()]
        try:
            if not lessonfile_ref.header.random_transpose[0]:
                return [mpd.MusicalPitch.new_from_notename(n).get_octave_notename() for n in notenames]
            else:
                return [mpd.MusicalPitch.new_from_notename(n).transpose_by_musicalpitch(lessonfile_ref.m_transpose).get_octave_notename() for n in notenames]
        except mpd.InvalidNotenameException, e:
            e.m_obj_lineno, e.m_linepos1, e.m_linepos2 = mpd.parser.validate_only_notenames(self.m_musicdata)
            raise
    def get_music_as_notename_string(self, lessonfile_ref):
        return " ".join(self.get_music_as_notename_list(lessonfile_ref))
    def play(self, lessonfile_ref, question):
        self.__play(lessonfile_ref, question,
                    lessonfile_ref.get_tempo_of_question(question))
    def play_slowly(self, lessonfile_ref, question):
        tempo = lessonfile_ref.get_tempo_of_question(question)
        self.__play(lessonfile_ref, question,
                (tempo[0] /2, tempo[1]))
    def __play(self, lessonfile_ref, question, tempo):
        assert isinstance(lessonfile_ref, LessonfileCommon)
        instrument = lessonfile_ref.get_instruments(question, 3)
        t1, t2, t3 = utils.new_3_tracks()
        t1.set_bpm(tempo[0])
        nlist = self.get_music_as_notename_list(lessonfile_ref)
        t1.set_patch(instrument[0])
        t1.set_volume(instrument[1])
        t2.set_patch(instrument[2])
        t2.set_volume(instrument[3])
        t3.set_patch(instrument[4])
        t3.set_volume(instrument[5])
        # start notes
        t1.note(4, mpd.notename_to_int(nlist[0]))
        for notename in nlist[1:-1]:
            t2.start_note(mpd.notename_to_int(notename))
        t2.notelen_time(4)
        for notename in nlist[1:-1]:
            t2.stop_note(mpd.notename_to_int(notename))
        t3.note(4, mpd.notename_to_int(nlist[-1]))
        soundcard.synth.play_track(t1, t2, t3)
    def play_arpeggio(self, lessonfile_ref, question):
        assert isinstance(lessonfile_ref, LessonfileCommon)
        # We have a problem here because the music need to know
        # things from the question it belongs to.
        instrument = lessonfile_ref.get_instruments(question, 3)
        assert len(instrument) == 6
        t1, t2, t3 = utils.new_3_tracks()
        t1.set_bpm(cfg.get_int('config/arpeggio_bpm'))
        nlist = self.get_music_as_notename_list(lessonfile_ref)
        # set patches and volumes
        t1.set_patch(instrument[0])
        t1.set_volume(instrument[1])
        t2.set_patch(instrument[2])
        t2.set_volume(instrument[3])
        t3.set_patch(instrument[4])
        t3.set_volume(instrument[5])
        # start notes
        t1.note(4, mpd.notename_to_int(nlist[0]))
        t2.notelen_time(4)
        t3.notelen_time(4)
        for notename in nlist[1:-1]:
            t2.note(4, mpd.notename_to_int(notename))
            t3.notelen_time(4)
        t3.note(4, mpd.notename_to_int(nlist[-1]))
        soundcard.synth.play_track(t1, t2, t3)

class VoiceCommon(MpdTransposable):
    pass

class Voice(VoiceCommon):
    def get_lilypond_code(self, lessonfile_ref):
        assert isinstance(lessonfile_ref, LessonfileCommon)
        if lessonfile_ref.header.random_transpose[0] == 'atonal':
            return r"{ %s }" % self.get_musicdata_transposed(lessonfile_ref)
        elif lessonfile_ref.header.random_transpose[0]:
            return r"\transpose c' %s{ %s }" % (
                lessonfile_ref.m_transpose.get_octave_notename(),
                self.m_musicdata)
        return r"{ %s }" % self.m_musicdata
    def get_lilypond_code_first_note(self, lessonfile_ref):
        assert isinstance(lessonfile_ref, LessonfileCommon)
        s = r"\score{" \
            r" \new Staff<<"\
            r" \new Voice%s{ \cadenzaOn %s }"\
            r" \new Voice{ \hideNotes %s }"\
            r" >>"\
            r" \layout { ragged-last = ##t }" \
            r" }"
        if lessonfile_ref.header.random_transpose[0] == 'atonal':
            return s % (
                "",
                self.get_first_pitch().transpose_by_musicalpitch(
                    lessonfile_ref.m_transpose).get_octave_notename(),
                self.m_musicdata,
                )
        elif lessonfile_ref.header.random_transpose[0]:
            return s % (
                "\\transpose c' %s" % lessonfile_ref.m_transpose.get_octave_notename(),
                self.get_first_pitch().get_octave_notename(),
                self.m_musicdata,
                )
        return s % ("", self.get_first_pitch().get_octave_notename(), self.m_musicdata)
    def get_mpd_music_string(self, lessonfile_ref):
        assert isinstance(lessonfile_ref, LessonfileCommon)
        if lessonfile_ref.header.random_transpose[0] == 'atonal':
            return "\\staff{\n%s\n}" % self.get_musicdata_transposed(lessonfile_ref)
        if lessonfile_ref.header.random_transpose[0]:
            return "\\staff\\transpose %s{\n%s\n}" \
                % (lessonfile_ref.m_transpose.get_octave_notename(),
                   self.m_musicdata)
        return "\\staff{\n%s\n}" % self.m_musicdata

class Rvoice(VoiceCommon):
    def get_mpd_music_string(self, lessonfile_ref):
        """
        Since get_mpd_music_string is used by error handling, it can not
        raise any exceptions. If m_musicdata is bad, then it should provide
        a string anyway, that the parser can choke on.
        """
        assert isinstance(lessonfile_ref, LessonfileCommon)
        if lessonfile_ref.header.random_transpose[0] == 'atonal':
            return "\\staff\\relative %s{\n%s\n}" % (
                self.get_first_pitch().transpose_by_musicalpitch(lessonfile_ref.m_transpose).get_octave_notename(),
                self.relative_transpose_musicdata(lessonfile_ref))
        lex = mpd.parser.Lexer(self.m_musicdata)
        try:
            pitch = self.get_first_pitch()
        except mpd.InvalidNotenameException, e:
            errpitch = self.m_musicdata.split("\n")[e.m_lineno][e.m_linepos1:e.m_linepos2]
            if lessonfile_ref.header.random_transpose[0]:
                return "\\staff\\transpose %s\\relative %s{\n%s\n}" % (
                    lessonfile_ref.m_transpose.get_octave_notename(),
                    errpitch,#self.get_first_pitch().get_octave_notename(),
                    lex.m_string
                    )
            # no translation
            return "\\staff\\relative %s{\n%s\n}" \
              % (errpitch, lex.m_string)

        pitch.m_octave_i = 0
        lex.set_first_pitch(pitch)
        if lessonfile_ref.header.random_transpose[0]:
            return "\\staff\\transpose %s\\relative %s{\n%s\n}" % (
                lessonfile_ref.m_transpose.get_octave_notename(),
                self.get_first_pitch().get_octave_notename(),
                lex.m_string
                )
        # no translation
        return "\\staff\\relative %s{\n%s\n}" \
          % (self.get_first_pitch().get_octave_notename(), lex.m_string)
    def get_lilypond_code(self, lessonfile_ref):
        return r"\transpose c' %s\relative c{ %s }" % (
            lessonfile_ref.m_transpose.get_octave_notename(),
            self.m_musicdata)
    def get_lilypond_code_first_note(self, lessonfile_ref):
        return r"\score{" \
               r" \new Staff<<"\
               r" \new Voice\transpose c' %s\relative c{ \cadenzaOn %s }" \
               r" \new Voice{ \hideNotes %s }"\
               r" >>"\
               r" \layout { ragged-last = ##t }" \
               r" }" % (
            lessonfile_ref.m_transpose.get_octave_notename(),
            self.get_first_pitch().get_octave_notename(),
            self.m_musicdata,
            )
    def get_err_context(self, exception, lessonfile_ref):
        """
        This functions expect exception.m_lineno, .m_linepos1 and .m_linepos2
        to be set relative to the m_musicdata of the music object,
        and not relative to the complete mpd string with added \staff{ } etc.

        Return a twoline string showing what caused the exception.

        Rvoice has its own implementation of get_err_context because we
        will modify the first tone in the music, removing the octave
        change characters (' and ,) and thus changing the lenght
        of the string. So we need to adjust the placement of the
        error marker (^^^^^).
        """
        try:
            delta = abs(self.get_first_pitch().m_octave_i)
        except mpd.InvalidNotenameException, e:
            delta = 0
        if hasattr(exception, 'm_obj_lineno'):
            return "\n".join((self.m_musicdata.split("\n")[exception.m_obj_lineno],
            " " * (exception.m_linepos1 + delta) + "^" * (exception.m_linepos2 - exception.m_linepos1)))
        return self._mpd_err_context(exception, lessonfile_ref)


class Satb(ChordCommon):
    def __init__(self, musicdata):
        ChordCommon.__init__(self, musicdata)
        if "\n" in self.m_musicdata:
            self._m_orig_musicdata = self.m_musicdata
            self.m_musicdata = self.m_musicdata.replace("\n", "")
    def get_mpd_music_string(self, lessonfile_ref):
        assert isinstance(lessonfile_ref, LessonfileCommon)
        v = [n.strip() for n in self.m_musicdata.split('|')]
        if len(v) != 4:
            raise MusicObjectException("Satb music should be divided into 4 parts by the '|' character")
        if [x for x in self.m_musicdata.split("|") if not x.strip()]:
            raise MusicObjectException("Satb music does not allow an empty voice")
        #FIXME BUG BUG BUG this only works for the currently active question
        if 'key' in lessonfile_ref.get_question():
            k = lessonfile_ref.get_question()['key']
        else:
            k = "c \major"
        music = "\\staff{ \key %s\\stemUp <%s> }\n" \
                "\\addvoice{ \\stemDown <%s> }\n" \
                "\\staff{ \key %s\\clef bass \\stemUp <%s>}\n"\
                "\\addvoice{ \\stemDown <%s>}" % (k, v[0], v[1], k, v[2], v[3])
        if lessonfile_ref.header.random_transpose[0]:
            music = music.replace(r"\staff",
                      r"\staff\transpose %s" % lessonfile_ref.m_transpose.get_octave_notename())
            music = music.replace(r"\addvoice",
                      r"\addvoice\transpose %s" % lessonfile_ref.m_transpose.get_octave_notename())
        return music
    def play_arpeggio(self, lessonfile_ref, question):
        assert isinstance(lessonfile_ref, LessonfileCommon)
        track = utils.new_track()
        voices = [n.strip() for n in self.m_musicdata.split('|')]
        for x in 0, 1:
            s = voices[x].strip().split(" ")
            for n in s:
                if lessonfile_ref.header.random_transpose[0]:
                    n = mpd.MusicalPitch.new_from_notename(n).transpose_by_musicalpitch(lessonfile_ref.m_transpose).get_octave_notename()
                if cfg.get_string('user/sex') == 'female':
                    track.note(4, mpd.notename_to_int(n))
                else:
                    track.note(4, mpd.notename_to_int(n)-12)
        for x in 2, 3:
            s = voices[x].strip().split(" ")
            for n in s:
                if lessonfile_ref.header.random_transpose[0]:
                    n = mpd.MusicalPitch.new_from_notename(n).transpose_by_musicalpitch(lessonfile_ref.m_transpose).get_octave_notename()
                if cfg.get_string('user/sex') == 'male':
                    track.note(4, mpd.notename_to_int(n))
                else:
                    track.note(4, mpd.notename_to_int(n)+12)
        soundcard.synth.play_track(track)
    def get_err_context(self, exception, lessonfile_ref):
        """
        Return a twoline string showing what caused the exception.
        """
        if len(self.m_musicdata.split("|")) != 4:
            return self.m_musicdata
        if [x for x in self.m_musicdata.split("|") if not x.strip()]:
            return self.m_musicdata
        line1 = []
        line2 = []
        err_found = False
        try:
            if self._m_orig_musicdata:
                bad_err_msg = "\n".join(textwrap.wrap("The music code from the lesson file has been modified by removing the new-line characters. This to more easily show where the error occured. Satb music should not contain music characters.", 60)) + "\n"
        except AttributeError:
            bad_err_msg = ""
        for i, s in enumerate(self.m_musicdata.split("|")):
            line1.append(s)
            if i == exception.m_lineno:
                line2.append("^" * len(s))
                err_found = True
            elif not err_found:
                line2.append(" " * len(s))
        return bad_err_msg + ("\n".join(("|".join(line1), " ".join(line2))))


class PercBaseClass(MpdParsable):
    def get_mpd_music_string(self, lessonfile_ref):
        return "\\rhythmstaff{\n%s\n}" % self.m_musicdata
    def _gen_track(self, lessonfile_ref, question):
        try:
            score = mpd.parser.parse_to_score_object(self.get_mpd_music_string(lessonfile_ref))
        except mpd.MpdException, e:
            self.complete_to_musicdata_coords(lessonfile_ref, e)
            raise
        track = mpd.score_to_tracks(score)[0]
        track.set_volume(cfg.get_int('config/preferred_instrument_volume'))
        track.prepend_bpm(lessonfile_ref.get_tempo()[0],
                          lessonfile_ref.get_tempo()[1])
        return track
    def play(self, lessonfile_ref, question):
        soundcard.synth.play_track(self._gen_track(lessonfile_ref, question))


class Rhythm(PercBaseClass):
    def get_mpd_music_string(self, lessonfile_ref):
        v = list(mpd.parser.Lexer(self.m_musicdata))
        for idx, (toc_type, toc) in enumerate(v):
            if toc_type == mpd.parser.Lexer.NOTE:
                if toc.m_pitch.semitone_pitch() == 48:
                    toc.m_pitch.set_from_int(cfg.get_int("config/rhythm_perc"))
                if toc.m_pitch.semitone_pitch() == 50:
                    toc.m_pitch.set_from_int(cfg.get_int("config/countin_perc"))
        return "\\rhythmstaff{\n%s\n}" % mpd.parser.Lexer.to_string(v)


class Percussion(PercBaseClass):
    pass

class _MusicExternalPlayer(MusicBaseClass):
    def __init__(self, typeid, musicdata):
        MusicBaseClass.__init__(self, musicdata)
        self.m_typeid = typeid
    def play(self, lessonfile_ref, question):
        assert isinstance(lessonfile_ref, LessonfileCommon)
        musicfile = os.path.join(lessonfile_ref.m_location, self.m_musicdata)
        if os.path.exists(musicfile):
            soundcard.play_mediafile(self.m_typeid, musicfile)
        else:
            raise FileNotFound(musicfile)
    def get_err_context(self, exception, lessonfile_ref):
        return ""

class Midifile(_MusicExternalPlayer):
    def __init__(self, musicdata):
        _MusicExternalPlayer.__init__(self, 'midi', musicdata)

class Mma(MusicBaseClass):
    def __init__(self, *v):
        """
        Mma is constructed in one of two ways:
            Mma(mmacode)
            Mma(groove, mmacode)
        If constructed with one argument, the mmacode must be complete and
        valid code that mma will accept.

        Constructed with two arguments, the first is the name of the groove
        to use, and the second is mma code that does not contain a Groove
        statement. This is useful if the groove argument is a nrandom
        or prandom object.
        """
        if len(v) == 1:
            self.m_groove = None
            mmacode = v[0]
        else:
            assert len(v) == 2
            self.m_groove = v[0]
            mmacode = v[1]
        MusicBaseClass.__init__(self, mmacode)
    def randomize(self):
        try:
            if self.m_groove:
               self.m_groove.randomize()
        except AttributeError:
            pass
    def play(self, lessonfile_ref, question):
        infile = os.path.join(self.temp_dir, 'f.mma')
        outfile = os.path.join(self.temp_dir, 'f.mid')
        f = open(infile, "w")
        if self.m_groove:
            print >> f, "Groove %s" % self.m_groove
        if lessonfile_ref.header.random_transpose[0]:
            print >> f, "Transpose %i" % (lessonfile_ref.m_transpose.semitone_pitch() - mpd.MusicalPitch.new_from_notename("c'").semitone_pitch())
        f.write(self.m_musicdata)
        f.close()
        try:
            mma = [cfg.get_string("programs/mma"), "-f", outfile, infile]
            if mma[0].endswith(".py"):
                mma.insert(0, sys.executable)
            subprocess.call(mma)
        except OSError, e:
            raise osutils.BinaryForProgramException("MMA",
                cfg.get_string("programs/mma"), e)
        soundcard.play_mediafile('midi', os.path.join(self.temp_dir, 'f.mid'))

class Wavfile(_MusicExternalPlayer):
    def __init__(self, musicdata):
        _MusicExternalPlayer.__init__(self, 'wav', musicdata)

class Mp3file(_MusicExternalPlayer):
    def __init__(self, musicdata):
        _MusicExternalPlayer.__init__(self, 'mp3', musicdata)

class Oggfile(_MusicExternalPlayer):
    def __init__(self, musicdata):
        _MusicExternalPlayer.__init__(self, 'ogg', musicdata)

class Cmdline(MusicBaseClass):
    def play(self, lessonfile_ref, question):
        assert isinstance(lessonfile_ref, LessonfileCommon)
        try:
            osutils.PopenSingleton(str(self.m_musicdata).split(" "),
                   cwd=lessonfile_ref.m_location)
        except OSError, e:
            raise osutils.RunningExecutableFailed(self.m_musicdata)

class CSound(MusicBaseClass):
    def __init__(self, orc, sco):
        MusicBaseClass.__init__(self, (orc, sco))
    def play(self, lessonfile_ref, question):
        outfile = open(os.path.join(self.temp_dir, "in.orc"), 'w')
        outfile.write(self.m_musicdata[0])
        outfile.close()
        outfile = open(os.path.join(self.temp_dir, "in.sco"), 'w')
        outfile.write(self.m_musicdata[1])
        outfile.close()
        try:
            subprocess.call(
                (cfg.get_string("programs/csound"),
                 os.path.join(self.temp_dir, "in.orc"),
                 os.path.join(self.temp_dir, "in.sco"),
                 "-W", "-d", "-o",
                 os.path.join(self.temp_dir, "out.wav")))
        except OSError, e:
             raise osutils.BinaryForProgramException("Csound", cfg.get_string("programs/csound"), e)
        soundcard.play_mediafile('wav', os.path.join(self.temp_dir, "out.wav"))


class Music(MpdTransposable):
    def get_mpd_music_string(self, lessonfile_ref):
        if lessonfile_ref.header.random_transpose[0]:
            s = self.m_musicdata.replace(r'\staff',
               r'\staff\transpose %s' % lessonfile_ref.m_transpose.get_octave_notename())
            s = s.replace(r'\addvoice',
               r'\addvoice\transpose %s' % lessonfile_ref.m_transpose.get_octave_notename())
            return s
        return self.m_musicdata
    def get_err_context(self, exception, lessonfile_ref):
        """
        Return a twoline string showing what caused the exception.
        This method will report wrong error location if there are
        more than one \staff command in a line.
        """
        first = exception.m_linepos1
        last = exception.m_linepos2
        tr = r'\transpose %s' % lessonfile_ref.m_transpose.get_octave_notename()
        delta = len(tr)
        lines = self.m_musicdata.split("\n")
        if lessonfile_ref.header.random_transpose[0]:
            s = self.m_musicdata.replace(r'\staff', r'\staff%s' % tr)
            s = s.replace(r'\addvoice', r'\addvoice%s' % tr)
            if (r'\staff' in lines[exception.m_lineno]
                or r'\addvoice' in lines[exception.m_lineno]):
                first = exception.m_linepos1 - delta
                last = exception.m_linepos2 - delta
        return "\n".join((self.m_musicdata.split("\n")[exception.m_lineno],
            " " * first + "^" * (last - first)))
    def complete_to_musicdata_coords(self, lessonfile_ref, exception):
        # These two lines are just for extra checking...
        assert not hasattr(exception, '_coords_done')
        exception._coords_done = True
        pass


class Music3(Music):
    def play(self, lessonfile_ref, question):
        """
        Play the music with different instrument for the top and bottom voice.
        Will use the instruments defined in the preferences window.
        """
        utils.play_music3(
            self.get_mpd_music_string(lessonfile_ref),
            lessonfile_ref.get_tempo(),
            lessonfile_ref.get_instruments(question, 3))

def parse_test_def(s):
    m = re.match("(\d+)\s*x", s)
    count = int(m.groups()[0])
    return (count, 'x')


class LessonfileCommon(object):
    def __init__(self, module_predefs=None, header_defaults=None):
        self.m_prev_question = None
        # This variable stores the directory the lesson file is located in.
        # We need this to we can find other files relative to this file.
        # .parse_file will set it to the location of the file.
        self.m_location = "."
        self._idx = None
        self.m_filename = "<STRING>"
        self.m_translation_re = re.compile("(?P<varname>\w+)\[(?P<lang>[\w_+]+)\]")
        if module_predefs is None:
            self.m_module_predefs = {}
        else:
            self.m_module_predefs = module_predefs
        if header_defaults is None:
            self.m_header_defaults = {}
        else:
            self.m_header_defaults = header_defaults
    def parse_file(self, filename):
        """Parse the file named filename. Set these variables:
        self.header     a Header instance
        self.questions  a list of all question
        """
        self.m_location = os.path.split(uri_expand(filename))[0]
        self.m_filename = filename
        # We open and read the file without using the codecs module
        # because the lexer class will check for a coding tag in
        # the lesson file before decoding it.
        s = open(uri_expand(filename), 'rU').read()
        self.parse_string(s, really_filename=filename)
    def parse_string(self, s, really_filename=None):
        """
        See parse_file docstring.
        """
        # FIXME what do we need really_filename for? Error messages?
        self.get_lessonfile(s, really_filename)
        ####################
        # Post parse setup #
        self.m_transpose = mpd.MusicalPitch.new_from_notename("c'")
        self.m_questions = self.blocklists.get('question', [])
        for question in self.m_questions:
            question.active = 1
            # FIXMECOMPAT
            if 'music' in question and isinstance(question.music, basestring):
                # The following line is for backward compatibility
                question.music = Music(question.music)
        self.m_random = xrandom.Random(range(len(self.m_questions)))
        # We have to make random_transpose a list, since this make
        # simplifies if statements in lessonfile.py
        # Also we cannot define the 'yes' and 'no' lesson file keywords
        # to be lists since it is used a a normal boolean for other
        # variables.
        if self.header.random_transpose in (True, False):
            self.header.random_transpose = [self.header.random_transpose,]
        if self.header.random_transpose[0] == True:
            self.header.random_transpose = ['key', -5, 5]
        # Backward compatability to handle old style
        # random_transpose = -4, 5 FIXMECOMPAT
        if self.header.random_transpose and len(self.header.random_transpose) == 2:
            self.header.random_transpose \
                = ['semitones'] + self.header.random_transpose
        # Some variables does only make sense if we have a music displayer
        if self.header.at_question_start:
            self.header.have_music_displayer = True
    def get_lessonfile(self, s, really_filename):
        """
        This is the parsetree interpreter.
        """
        dp = dataparser.Dataparser()
        dp.m_location = self.m_location
        try:
            dp.parse_string(s, really_filename)
        except LessonfileParseException, e:
            e.m_nonwrapped_text = dp._lexer.get_err_context(dp._lexer.pos - 2)
            e.m_token = dp._lexer.m_tokens[dp._lexer.pos - 2]
            raise
        d = lessonfile_builtins.copy()
        d.update(self.m_module_predefs)
        mod = lfmod.parse_tree_interpreter(dp.tree, d)
        self.m_globals = mod.m_globals
        self.blocklists = mod.m_blocklists
        if 'header' in self.blocklists:
            self.header = _Header(self.blocklists['header'][0])
        else:
            self.header = _Header({})
        self.header.update(self.m_header_defaults)


class QuestionsLessonfile(LessonfileCommon):
    def __init__(self, module_predefs=None, header_defaults=None):
        LessonfileCommon.__init__(self, module_predefs, header_defaults)
        self.m_discards = []
    def select_random_question(self):
        """
        Select a new question by random. It will use the music in the
        lesson file question variable 'music' when selecting transposition.
        """
        # when we start the program with --no-random, we want to go
        # throug all the questions in the lesson file in sequential order.
        if cfg.get_bool('config/no_random'):
            try:
                self.m_no_random_idx
            except:
                self.m_no_random_idx = 0
            self.header.random_transpose[0] = False

        count = 0
        available_question_idx = []
        for i in range(len(self.m_questions)):
            if self.m_questions[i]['active']:
                available_question_idx.append(i)
        if not available_question_idx:
            raise NoQuestionsConfiguredException()
        while 1:
            count += 1
            if cfg.get_bool('config/no_random'):
                if self.m_no_random_idx < len(available_question_idx):
                    self._idx = self.m_no_random_idx
                    self.m_no_random_idx += 1
                else:
                    self._idx = self.m_no_random_idx = 0
            else:
                if cfg.get_string("app/random_function") == 'random_by_random':
                    self._idx = self.m_random.random_by_random(available_question_idx)
                elif cfg.get_string("app/random_function") == 'random_by_random2':
                    self._idx = self.m_random.random_by_random2(available_question_idx)
                elif cfg.get_string("app/random_function") == 'random_by_selection':
                    self._idx = self.m_random.random_by_selection(available_question_idx)
                else:
                    self._idx = random.choice(available_question_idx)
            if self.header.random_transpose[0]:
                self.m_transpose = self.find_random_transpose()
            if count == 10:
                break
            if self.m_prev_question == self.get_music() \
                and (len(self.m_questions) > 1 or self.header.random_transpose[0]):
                continue
            break
        try:
            self.get_question().music.randomize()
        except AttributeError, e:
            pass
        self.m_random.add(self._idx)
        self.m_prev_question = self.get_music()
    def find_random_transpose(self):
        """
        Return a MusicalPitch representing a suggested random
        transposition for the currently selected question,
        m_questions[self._idx]
        """
        if 'key' in self.m_questions[self._idx]:
            key = self.m_questions[self._idx]['key']
        else:
            key = "c \major"
        if self.header.random_transpose[0] == True:
            self.header.random_transpose = ['key', -5, 5]
        if self.header.random_transpose[0] in ('semitones', 'atonal'):
            retval = self.semitone_find_random_transpose()
            if random.randint(0, 1):
                retval.enharmonic_flip()
        else:
            retval = self._xxx_find_random_transpose(key)
        return retval
    def semitone_find_random_transpose(self):
        """
        Called to find random transposition in "semitone" mode.
        Create and return a random MusicalPitch representing this transposition.
        """
        assert self.header.random_transpose[0] in ('semitones', 'atonal')
        return mpd.MusicalPitch().randomize(
              mpd.transpose_notename("c'", self.header.random_transpose[1]),
              mpd.transpose_notename("c'", self.header.random_transpose[2]))
    def _xxx_find_random_transpose(self, key):
        """
        Called to create random transposition in "accidentals" or "key" mode.
        Create and return a random MusicalPitch representing this transposition.
        Keyword arguments:
        key -- the key the question is written in, for example "c \major"
        """
        assert self.header.random_transpose[0] in ('key', 'accidentals')
        low, high = self.header.random_transpose[1:3]
        tone, minmaj = key.split()
        k = mpd.MusicalPitch.new_from_notename(tone).get_octave_notename()
        #FIXME this list say what key signatures are allowed in sing-chord
        # lesson files. Get the correct values and document them.
        kv = ['des', 'aes', 'ees', 'bes', 'f', 'c',
              'g', 'd', 'a', 'e', 'b', 'fis', 'cis', 'gis']
        # na tell the number of accidentals (# is positive, b is negative)
        # the question has from the lessonfile before anything is transpose.
        na = kv.index(k) - 5
        if minmaj == '\\minor':
            na -= 3
        if self.header.random_transpose[0] == 'accidentals':
            # the number of steps down the circle of fifths we can go
            n_down = low - na
            # the number of steps up the circle of fifths we can go
            n_up = high - na
        else:
            assert self.header.random_transpose[0] == 'key'
            n_down = low
            n_up = high
        interv = mpd.Interval()
        interv.set_from_string(_keys_to_interval[random.choice(range(n_down, n_up+1))])
        return mpd.MusicalPitch.new_from_notename("c'") + interv
    def iterate_questions_with_unique_names(self):
        """Iterate the questions in the lessonfile, but only yield the
        first question if several questions have the same name. The
        untranslated name is used when deciding if a name is unique.
        """
        names = {}
        for question in self.m_questions:
            if 'name' in question and question.name.cval not in names:
                names[question.name.cval] = 1
                yield question
    def get_unique_cnames(self):
        """Return a list of all cnames in the file, in the same order
        as they appear in the file. Only list each cname once, even if
        there are more questions with the same cname.
        """
        names = []
        for question in self.m_questions:
            if 'name' in question and question.name.cval not in names:
                names.append(question.name.cval)
        return names
    def get_question(self):
        """
        Return the currently selected question.
        """
        assert self._idx is not None
        return self.m_questions[self._idx]
    def get_tempo(self):
        """
        Return the tempo of the currently selected question
        """
        assert self._idx is not None
        if 'tempo' in self.m_questions[self._idx]:
            return self.m_questions[self._idx]['tempo']
        return self.m_globals['tempo']
    def get_tempo_of_question(self, question):
        if 'tempo' in question:
            return question['tempo']
        return self.m_globals['tempo']
    def get_name(self):
        """
        Return the translated name of the currently selected question.
        """
        assert self._idx is not None
        return self.m_questions[self._idx].name
    def get_cname(self):
        """
        The 'cname' of a question is the C locale of the question name.
        Said easier: If the lesson file supplies translations, then 'cname'
        is the untranslated name.
        """
        assert self._idx is not None
        return self.m_questions[self._idx].name.cval
    def get_lilypond_code(self):
        assert self._idx is not None
        return self.m_questions[self._idx].music.get_lilypond_code(self)
    def get_lilypond_code_first_note(self):
        assert self._idx is not None
        return self.m_questions[self._idx].music.get_lilypond_code_first_note(self)
    def get_music(self, varname='music'):
        """
        Return the music for the currently selected question. This is complete
        music code that can be fed to utils.play_music(...).

        If the music type not of a type that utils.play_music can handle,
        for example a midi file or a cmdline type, then we return a string
        that can be used to compare if the music of two questions are equal.
        This string is not parsable by any functions and should only be used
        to compare questions.
        """
        assert self._idx is not None
        return self.m_questions[self._idx][varname].get_mpd_music_string(self)
    def get_music_as_notename_list(self, varname):
        """
        Return a list of notenames from the variabale VARNAME in the
        currently selected question. The notes are transposed if
        header.random_transpose is set.
        """
        assert self._idx is not None
        return self.get_question()[varname].get_music_as_notename_list(self)
    def get_music_as_notename_string(self, varname):
        """
        Return a string with notenames representing the question currently
        selected question. The notes are transposed if
        header.random_transpose is set.
        """
        return " ".join(self.get_music_as_notename_list(varname))
    def get_score(self, varname='music'):
        """
        Return the elems.Score object of the music in the variable named
        by VARNAME.
        """
        assert self._idx is not None
        musicobj = self.m_questions[self._idx][varname]
        assert isinstance(musicobj, MpdParsable)
        return musicobj.get_score(self, as_name=varname)
    def has_question(self):
        """
        Return True if a question is selected.
        """
        return self._idx is not None
    def parse_string(self, s, really_filename=None):
        super(QuestionsLessonfile, self).parse_string(s, really_filename)
        if not self.m_questions:
            raise NoQuestionsInFileException(self.m_filename)
    def play_question(self, question=None, varname='music'):
        """Play the question. Play the current question if question is none.
        varname is the name of the variable that contains the music.
        """
        if not question:
            question = self.get_question()
        try:
            question[varname].play(self, question)
        except mpd.MpdException, e:
            # This code have to be here for code that run m_P.play_question
            # exception_handled to be able to say which variable has the bug
            # and show the bad code.
            if 'm_mpd_varname' not in dir(e):
                e.m_mpd_varname = varname
            if 'm_mpd_badcode' not in dir(e):
                e.m_mpd_badcode = question[varname].get_err_context(e, self)
            raise
    def play_question_slowly(self, question=None, varname='music'):
        if not question:
            question = self.get_question()
        question[varname].play_slowly(self, question)
    def play_question_arpeggio(self, varname='music'):
        self.get_question()[varname].play_arpeggio(self, self.get_question())
    def get_instrument(self, question):
        """
        Music objects that will use the "config/preferred_instrument"
        or the music instrument selected in the lesson file should
        call this method.
        """
        if 'instrument' in question:
            retval = question['instrument']
        elif 'instrument' in self.m_globals:
            retval = self.m_globals['instrument']
        else:
            retval = [cfg.get_int('config/preferred_instrument'),
                      cfg.get_int('config/preferred_instrument_volume')]
        if isinstance(retval[0], unicode):
            try:
                retval[0] = soundcard.find_midi_instrument_number(retval[0])
            except KeyError, e:
                print >> sys.stderr, "Warning: Invalid instrument name '%s' in lesson file:" % retval[0], e
                retval[0] = cfg.get_int('config/preferred_instrument')
        return retval
    def get_instruments(self, question, count):
        """
        Music objects that want 2 or 3 of the instruments we can configure
        if we select "Override default instrument" should call this method.
        """
        assert count in (1, 2, 3)
        if (count in (2, 3) and
            cfg.get_bool('config/override_default_instrument')):
                retval = [cfg.get_int('config/lowest_instrument'),
                          cfg.get_int('config/lowest_instrument_volume'),
                          cfg.get_int('config/middle_instrument'),
                          cfg.get_int('config/middle_instrument_volume'),
                          cfg.get_int('config/highest_instrument'),
                          cfg.get_int('config/highest_instrument_volume')]
        else:
            retval = [cfg.get_int('config/preferred_instrument'),
                      cfg.get_int('config/preferred_instrument_volume')]
        if 'instrument' in question:
            retval = question['instrument']
        elif 'instrument' in self.m_globals:
            retval = self.m_globals['instrument']
        while len(retval) < count * 2:
            retval.extend(retval[-2:])
        for idx in range(0, len(retval), 2):
            if isinstance(retval[idx], unicode):
                try:
                    retval[idx] = soundcard.find_midi_instrument_number(retval[idx])
                except KeyError, e:
                    print >> sys.stderr, "Warning: Invalid instrument name '%s' in lesson file:" % retval[idx], e
                    retval[idx] = cfg.get_int('config/preferred_instrument')
        return retval
    def discard_questions_without_name(self):
        # Delete questions that does not have a name
        q = self.m_questions
        self.m_questions = []
        for idx, question in enumerate(q):
            if 'name' not in question:
                self.m_discards.append("\n".join(textwrap.wrap(_('Discarding question %(questionidx)i from the lessonfile "%(filename)s" because it is missing the "name" variable. All questions in lesson files of this type must have a name variable.' % {'questionidx': idx, 'filename': self.m_filename}))))
                continue
            else:
                self.m_questions.append(question)
    def implements_music_displayer_stafflines(self):
        if 'music_displayer_stafflines' not in self.header:
            self.header.music_displayer_stafflines = 1


class TestSupport(object):
    """
    Lessonfile classes can add this class to the list of classes it
    inherits from if the exercise want to have tests.
    """
    def _generate_test_questions(self):
        count, t = parse_test_def(self.header.test)
        q = range(len(self.m_questions)) * count
        random.shuffle(q)
        return q
    def get_test_num_questions(self):
        """
        Return the number of questions in the running test.
        This method is undefined if not running a test.
        """
        return len(self.m_questions) * parse_test_def(self.header.test)[0]
    def get_test_requirement(self):
        """
        Return the amount of exercises that has to be correct to
        pass the test. (values 0.0 to 1.0)
        """
        m = re.match("([\d\.]+)%", self.header.test_requirement)
        if m:
            return float(m.groups()[0])/100.0
        else:
            return 0.9
    def enter_test_mode(self):
        self.m_test_questions = self._generate_test_questions()
        self.m_test_idx = -1
    def next_test_question(self):
        assert self.m_test_idx < len(self.m_test_questions)
        self.m_test_idx += 1
        self._idx = self.m_test_questions[self.m_test_idx]
        if self.header.random_transpose[0]:
            old = self.m_transpose
            # try really hard not to get the same tonika:
            for x in range(100):
                self.m_transpose = self.find_random_transpose()
                if old != self.m_transpose:
                    break
    def is_test_complete(self):
        """
        Return True if the test is compleded.
        """
        return self.m_test_idx == len(self.m_test_questions) -1

class HeaderLessonfile(LessonfileCommon):
    """
    This lesson file class should be used by all the exercise modules
    that does not need any question blocks defined.
    """
    pass

class DictationLessonfile(QuestionsLessonfile):
    def get_breakpoints(self):
        assert self._idx is not None
        r = []
        if 'breakpoints' in self.m_questions[self._idx]:
            r = self.m_questions[self._idx]['breakpoints']
            if not type(r) == type([]):
                r = [r]
        r = map(lambda e: Rat(e[0], e[1]), r)
        return r
    def get_clue_end(self):
        assert self._idx is not None
        if 'clue_end' in self.m_questions[self._idx]:
            try:
                return Rat(*self.m_questions[self._idx]['clue_end'])
            except TypeError:
                raise LessonfileException("The 'clue_end' variable was not well formed")
    def get_clue_music(self):
        assert self._idx is not None
        if 'clue_music' in self.m_questions[self._idx]:
            return self.m_questions[self._idx]['clue_music']
    def select_previous(self):
        """
        Select the previous question. Do nothing if we are on the first
        question.
        """
        assert self._idx is not None
        if self._idx > 0:
            self._idx = self._idx - 1
    def select_next(self):
        """
        Select the next question. Do nothing if we are on the last question.
        """
        assert self._idx is not None
        if self._idx < len(self.m_questions) -1:
            self._idx = self._idx + 1
    def select_first(self):
        """
        Select the first question.
        """
        self._idx = 0

class SingChordLessonfile(QuestionsLessonfile):
    pass


class RhythmDictation2Lessonfile(QuestionsLessonfile):
    """
    We inherit from QuestionsLessonfile just to get the .get_tempo()
    method. Lots of the other methods from QuestionsLessonfile does
    not make sense to use in the class.
    """
    def parse_string(self, s, really_filename=None):
        LessonfileCommon.parse_string(self, s, really_filename)
        if not self.m_questions:
            raise NoQuestionsInFileException(self.m_filename)
        # Make sure the variables are lists. If there is only one elemt
        # in the lesson file then we must make a list of them.
        for question in self.m_questions:
            if not isinstance(question['bars'], list):
                question['bars'] = [question['bars']]
            if not isinstance(question['elements'], list):
                question['elements'] = [question['elements']]
    def generate_random_question(self):
        def rat_len_of_digits(digits):
            """
            Return a Rat representing the length of the digits.
            "4 8 8" returns Rat(2, 4)
            """
            ret = Rat(0, 1)
            for d in digits.split():
                ret += Duration.new_from_string(d).get_rat_value()
            return ret
        notename = mpd.MusicalPitch.new_from_int(cfg.get_int("config/rhythm_perc")).get_octave_notename()
        self._idx = random.randint(0, len(self.m_questions) - 1)
        # The score where the user enters his answer
        self.m_answer_score = score = elems.Score()
        score.add_staff(staff_class=elems.RhythmStaff)
        for num, den in self.m_questions[self._idx]['bars']:
            score.add_bar(elems.TimeSignature(num, den))
        for bar in score.m_bars:
            bar.fill_skips(score.voice11)
        # the question being played
        self.m_question_score = score = elems.Score()
        score.add_staff(staff_class=elems.RhythmStaff)
        for num, den in self.m_questions[self._idx]['bars']:
            score.add_bar(elems.TimeSignature(num, den))
            bar = self.m_question_score.m_bars[-1]
            total = Rat(0, 1)
            # We try only 1000 times, since it is possible that the lesson
            # file is badly written with too long elements or too short bars.
            count = 0
            max_count = 100
            while total < bar.m_timesig.as_rat() and count < max_count:
                elem = random.choice(self.m_questions[self._idx]['elements'])
                if total + rat_len_of_digits(elem) > bar.m_timesig.as_rat():
                    count += 1
                    continue
                total += rat_len_of_digits(elem)
                for e in elem.split(" "):
                    e = e.strip()
                    n = elems.Note.new_from_string(u"%s%s" % (notename, e))
                    score.voice11.append(n)
                    count = 0
                count += 1
            if count == max_count:
                raise LessonfileException("Bad elements variable in the lessonfile. Too long elements.")
    def play_question(self):
        tracks = mpd.score_to_tracks(self.m_question_score)
        tracks[0].prepend_bpm(*self.m_questions[self._idx]['tempo'])
        soundcard.synth.play_track(*tracks)

class NameIntervalLessonfile(HeaderLessonfile):
    def parse_string(self, s, really_filename=None):
        super(NameIntervalLessonfile, self).parse_string(s, really_filename)
        iquality = []
        inumbers = []
        self.header.intervals = [mpd.Interval(n) for n in self.header.intervals]
        for i in self.header.intervals:
            if i.get_quality_short() not in iquality:
                iquality.append(i.get_quality_short())
            if i.steps() not in inumbers:
                inumbers.append(i.steps())
        def quality_sort(a, b):
            v = ['dd', 'd', 'm', 'M', 'p', 'a', 'aa']
            return cmp(v.index(a), v.index(b))
        iquality.sort(quality_sort)
        inumbers.sort()
        if not self.header.interval_number:
            self.header.interval_number = inumbers
        if not isinstance(self.header.interval_number, list):
            self.header.interval_number = [self.header.interval_number]
        if not self.header.interval_quality:
            self.header.interval_quality = iquality
        if not isinstance(self.header.interval_quality, list):
            self.header.interval_number = [self.header.interval_quality]
        if self.header.accidentals == "":
            self.header.accidentals = 1
        if self.header.clef == "":
            self.header.clef = u"violin"
        if not self.header.tones:
            self.header.tones = [mpd.MusicalPitch.new_from_notename("b"),
                                mpd.MusicalPitch.new_from_notename("g''")]
        else:
            if len(self.header.tones) != 2:
                raise LessonfileParseException("The length of the lesson file header variable 'tones' has to be 2")
            self.header.tones = [mpd.MusicalPitch.new_from_notename(n) for n in self.header.tones]

class IdByNameLessonfile(QuestionsLessonfile, TestSupport):
    def parse_string(self, s, really_filename=None):
        super(IdByNameLessonfile, self).parse_string(s, really_filename)
        # Also, if some questions has cuemusic, then we need the displayer
        if [q for q in self.m_questions if 'cuemusic' in q]:
            self.header.have_music_displayer = True
        # FIXME to be backward compatible. FIXMECOMPAT
        # These 3 lines make the idbyname lesson header assignment
        # "labelformat = progression" do as advertised.
        if self.header.labelformat == 'progression':
            for question in self.m_questions:
                question.label = lessonfile_builtins["progressionlabel"][1](question.name)
        self.discard_questions_without_name()
        self.implements_music_displayer_stafflines()

class SingAnswerLessonfile(QuestionsLessonfile):
    def parse_string(self, s, really_filename=None):
        super(SingAnswerLessonfile, self).parse_string(s, really_filename)
        v = [q for q in self.m_questions if 'question_text' not in q]
        if [q for q in self.m_questions if 'question_text' not in q]:
            raise LessonfileParseException(_('Question number %(index)i in the lesson file "%(filename)s" is missing the "question_text" variable.') % {
                'index': self.m_questions.index(v[0]),
                'filename': self.m_filename})

class IntervalsLessonfile(HeaderLessonfile, TestSupport):
    """
    Common lesson file class for some interval exercises.
    We inherit from TestSupport, but overwrites some methods from it.
    """
    def get_test_num_questions(self):
        count, t = parse_test_def(self.header.test)
        if self.header.intervals:
            return len(self.header.intervals) * count
        else:
            return len(self.header.ask_for_intervals_0) * count
    def enter_test_mode(self):
        count, t = parse_test_def(self.header.test)
        if self.header.intervals:
            self.m_test_questions = self.header.intervals * count
        else:
            self.m_test_questions = self.header.ask_for_intervals_0 * count
        random.shuffle(self.m_test_questions)
        self.m_test_idx = -1
    def next_test_question(self):
        self.m_test_idx += 1

class IdPropertyLessonfile(QuestionsLessonfile):
    def parse_string(self, s, really_filename=None):
        """
        Call IdPropertyLessonfile.parse_string and set the self.m_props dict.
        Change some question variables, so that:

          inversion = 0

        is the same as

          inversion = _("root position")
        """
        super(IdPropertyLessonfile, self).parse_string(s, really_filename)
        if self.header.flavour == 'chord':
            if not self.header.new_button_label:
                self.header.new_button_label = _("_New chord")
            if not self.header.lesson_heading:
                self.header.lesson_heading = _("Identify the chord")
            if not self.header.qprops:
                self.header.qprops = ['name', 'inversion', 'toptone']
                self.header.qprop_labels = [
                             istr.new_translated("Chord type", _("Chord type")),
                             istr.new_translated("Inversion", _("Inversion")),
                             istr.new_translated("Toptone", _("Toptone"))]
        if not self.header.qprops:
            raise LessonfileParseException(_("Missing qprops variable in the lesson file %s.") % self.m_filename)
        # These two tests are needed, so we can have qprops and qprop_labels
        # lists with only one element.
        if not isinstance(self.header.qprops, list):
            self.header.qprops = [self.header.qprops]
        if not isinstance(self.header.qprop_labels, list):
            self.header.qprop_labels = [self.header.qprop_labels]
        if len(self.header.qprops) != len(self.header.qprop_labels):
            raise LessonfileParseException(_("Error in the lesson file header of \"%(filename)s\". The variables qprops and qprop_labels must have the same length.") % {'filename': self.m_filename})
        # m_props will be a dict where each key is the property var name.
        # The values will be a list of possible values for that property.
        # The values are of type istr. This mean that .cval holds the
        # C locale string.
        self.m_props = {}
        for k in self.header.qprops:
            self.m_props[k] = []
        for question in self.m_questions:
            for varname in self.header.qprops:
                if varname in question:
                    if varname == 'inversion':
                        if question[varname] == 0:
                            question[varname] = istr(_("root position"))
                            question[varname].cval= "root position"
                        elif type(question[varname]) == int \
                            and question[varname] > 0:
                            i = question[varname]
                            question[varname] = istr(_("%i. inversion") % i)
                            question[varname].cval = "%i. inversion" % i
                    # FIXMECOMPAT convert integer properties to strings.
                    # This to be compatible with solfege 3.9.1 and older.
                    if type(question[varname]) in (int, float):
                        question[varname] = istr(unicode(question[varname]))
                    # then add to m_props
                    if question[varname] not in self.m_props[varname]:
                        self.m_props[varname].append(question[varname])
        for k in self.m_props.keys():
            if not self.m_props[k]:
                idx = self.header.qprops.index(k)
                del self.header.qprops[idx]
                del self.header.qprop_labels[idx]
        for k in [k for k in self.m_props if not self.m_props[k]]:
            del self.m_props[k]
        # Have to use [:] when deleting from the list
        for idx, question in enumerate(self.m_questions[:]):
            # The list we create has the name of all the missing properties
            # in the question
            missing_props = [p for p in self.m_props if p not in question]
            if missing_props:
                self.m_discards.append("\n".join(textwrap.wrap(ungettext(
                    'Discarding question %(questionidx)i from the lesson file "%(filename)s" because of a missing variable: %(var)s',
                    'Discarding question %(questionidx)i from the lesson file "%(filename)s" because of some missing variables: %(var)s',
                    len(missing_props)) %  {'questionidx': idx, 'filename': self.m_filename, 'var': ", ".join(missing_props)})))
                self.m_questions[idx] = None
        self.m_questions = [q for q in self.m_questions if q is not None]

class ChordLessonfile(IdPropertyLessonfile):
    def parse_string(self, s, really_filename=None):
        super(ChordLessonfile, self).parse_string(
        s.replace("header {",
                """
                header {
                   qprops = "name", "inversion", "toptone"
                   qprop_labels = _("Chord type"), _("Inversion"), _("Chord type")
                """),
        really_filename)


class ElembuilderLessonfile(QuestionsLessonfile):
    def parse_string(self, s, really_filename=None):
        super(ElembuilderLessonfile, self).parse_string(s, really_filename)
        # We need the name variable for statistics
        self.discard_questions_without_name()
        # question['elements'] should always be a list. If a question allows
        # a single element as answer one gets a dict from parse_string and not
        # a list. Thus we pack the dict in a list and are happy.
        for question in self.m_questions:
            if type(question['elements']) <> (type([])):
                question['elements'] = [question['elements']]
        # This loop let us use normal strings and lesson file functions
        # like pangomarkup as element labels.
        for question in self.m_questions:
            if [e for e in question['elements'] if type(e) in (istr, LabelObject)]:
                v = []
                for e in question['elements']:
                    if type(e) == istr:
                        v.append({'name': e.cval, 'label': e.cval})
                    elif type(e) == LabelObject:
                        v.append({'name':e, 'label': e})
                    else:
                        v.append(e)
                question['elements'] = v
        self.implements_music_displayer_stafflines()
        if 'element' not in self.blocklists:
            self.blocklists['element'] = []
        self.m_elements = {}
        for question in self.m_questions:
            for e in question['elements']:
                if e['name'] not in self.m_elements:
                    self.m_elements[e['name']] = e


class InfoCache(object):
    class InfoCacheException(IOError):
        pass
    class FileNotFound(InfoCacheException):
        pass
    class FileNotLessonfile(InfoCacheException):
        pass
    class FrontPageCache(object):
        OLD_FORMAT = 1
        PARSE_ERROR = 2
        def __init__(self):
            self._data = {}
        def get(self, filename, field):
            if filename not in self._data:
                self.parse_file(filename)
            elif os.path.getmtime(filename) != self._data[filename]['mtime']:
                self.parse_file(filename)
            return self._data[filename][field]
        def parse_file(self, filename):
            from solfege import frontpage
            try:
                p = frontpage.load_tree(filename)
                self._data[filename] = {'title': p.m_name,
                                        'mtime': os.path.getmtime(filename)}
            except frontpage.OldFormatException:
                self._data[filename] = self.OLD_FORMAT
            except frontpage.FrontPageException:
                self._data[filename] = self.PARSE_ERROR
        def iter_old_format_files(self):
            for filename, value in self._data.items():
                if value == self.OLD_FORMAT:
                    yield filename
    def __init__(self):
        self._data = {}
        self._dir_mtime = {}
        self.frontpage = self.FrontPageCache()
    def get(self, filename, field):
        """
        filename is either a solfege: uri or an absolute file name.
        Relative file names are not allowed, since we want the program
        to refer to standard lesson files with the solfege: uri
        """
        assert is_uri(filename) or os.path.isabs(filename)
        if not os.path.isfile(uri_expand(filename)):
            raise InfoCache.FileNotFound(filename)
        mtime = os.path.getmtime(uri_expand(filename))
        if filename not in self._data or self._data[filename]['mtime'] < mtime:
            self.parse_file(filename, mtime)
        return self._data[filename][field]
    def parse_file(self, filename, mtime=None):
        assert is_uri(filename) or os.path.isabs(filename)
        p = parse_lesson_file_header(uri_expand(filename))
        if not p:
            raise self.FileNotLessonfile(filename)
        try:
            try:
                module = p.header['module'].m_name
            except AttributeError:
                # If the module name is the same as a word defined in predef
                module = p.header['module']
            self._data[filename] = {
                'title': p.header.get('title', 'error: no title in file'),
                'module': module,
                'test': p.header.get('test', None),
                'test_requirement': p.header.get('test_requirement', None),
                'mtime': mtime if mtime else os.path.getmtime(uri_expand(filename)),
                'replaces': p.header.get('replaces', []),
        }
        except KeyError:
            logging.debug("InfoCache.parse_file: FileNotLessonfile(%s)", filename)
            print "file not lessonfile:", filename
            raise self.FileNotLessonfile(filename)
        if not self._data[filename]['title']:
            self._data[filename]['title'] = "error: empty string as title in '%s'" % filename
    def iter_parse_all_files(self):
        """
        Parse the files and put then in the cache.
        yield filename.
        """
        logging.debug("iter_parse_all_files()")
        for filename in self._iter_files(
                os.path.join(exercises_dir, u"lesson-files")):
            yield filename
        for filename in self.iter_user_files():
            yield filename
    def _iter_files(self, *path):
        """
        Parse and put into the cache all lesson files in the directories
        in the list path and yield the file names of the files that are
        parsed and found to be lesson files.
        """
        for directory in path:
            if os.path.isdir(directory):
                for fn in os.listdir(directory):
                    filename = os.path.join(directory, fn)
                    if not os.path.isfile(filename):
                        continue
                    filename = mk_uri(filename)
                    try:
                        self.parse_file(filename)
                    except self.FileNotLessonfile:
                        continue
                    yield filename
    def parse_all_files(self, when_idle):
        """
        Parse all standard lesson files and the user_lessonfiles.
        Will not check if reparse is necessary.
        """
        logging.debug("parse_all_files(when_idle=%s)", when_idle)
        if when_idle:
            self._lessonfiles_iterator = self.iter_parse_all_files()
            def on_idle_parse():
                try:
                    filename = self._lessonfiles_iterator.next()
                    return True
                except StopIteration:
                    logging.debug("parse_all_files(...) done.")
                    import time
                    print "all files parsed:", time.time() - start_time
                    pt.Identifier.check_ns = True
                    return False
            GObject.idle_add(on_idle_parse)
        else:
            list(self.iter_parse_all_files())
    def update_modified_files(self):
        self.cond_parse_dir(filesystem.user_lessonfiles())
        self.cond_parse_dir(os.path.join(exercises_dir, u"lesson-files"))
    def cond_parse_dir(self, dir):
        """
        Check the mtime of the files in dir if dirs mtime has changed
        or is not in _data. Parse the lesson files if their mtime has
        changed or is not in _data.
        Do nothing if the dir does not exist.
        """
        if not os.path.exists(dir):
            return
        mtime = os.path.getmtime(dir)
        assert isinstance(dir, unicode)
        logging.debug("cond_parse_dir(%s) mtime=%s", dir, mtime)
        if dir not in self._dir_mtime:
            for filename in os.listdir(dir):
                fn = os.path.join(dir, filename)
                if not os.path.isfile(fn):
                    continue
                fn = mk_uri(fn)
                file_mtime = os.path.getmtime(uri_expand(fn))
                if fn not in self._data or file_mtime > self._data[fn]['mtime']:
                    try:
                        logging.debug(" will parse %s. in data:%s", fn, fn in self._data)
                        self.parse_file(fn, file_mtime)
                    except self.InfoCacheException:
                        logging.debug(" exception, not parsed: %s", fn)
                        pass
    def iter_user_files(self, only_user_collection=False):
        """
        Put the data from the lesson files below ~/.solfege/exercises/
        in the cache and yield the filename.

        If only_user_collection=True it will only iterate the lesson files
        in .solfege/exercises/user/lesson-files
        """
        logging.debug("iter_user_files(%s)", only_user_collection)
        if only_user_collection:
            mask = u"user/lesson-files/*"
        else:
            mask = u"*/*/*"
        for fn in glob.glob(os.path.join(filesystem.user_data(), u"exercises", mask)):
            if os.path.isfile(fn):
                try:
                    self.parse_file(fn)
                    yield fn
                except self.InfoCacheException:
                    continue


def parse_lesson_file_header(filename):
    """
    This function is used at program starup to get the info the
    lessonfile_manager needs. This might not be bullet proof, but
    it provides a 22x speedup, and that was necessary when we got
    many lesson files.

    Return None if we find no header block.
    """
    r = re.compile("header\s*{.*?}", re.MULTILINE|re.DOTALL)
    # We cannot read the whole file, since we don't know what the user
    # have placed in the directory. It could be a whole DVD iso image.
    # The actual size we read, 40k, is mentioned in the user manual,
    # and must be updated there too if changed.
    s = open(filename, 'rU').read(40960)
    m = r.search(s)
    p = LessonfileCommon()
    ###############################
    if not m:
        return
    check_ns = pt.Identifier.check_ns
    pt.Identifier.check_ns = False
    try:
        p.get_lessonfile(m.group(), None)
    except dataparser.DataparserException:
        return None
    finally:
        pt.Identifier.check_ns = check_ns
    return p

