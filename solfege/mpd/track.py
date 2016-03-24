# GNU Solfege - free ear training software
# Copyright (C) 2000, 2001, 2002, 2003, 2004, 2006, 2007, 2008, 2011   Tom Cato Amundsen
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
import logging

from solfege.mpd.rat import Rat
from solfege.mpd import mfutils
from solfege.mpd.const import DEFAULT_VELOCITY, DEFAULT_VOLUME

set_patch_delay = 0

class EventBase(object):
    def __init__(self):
        self.m_time = None
    def __str__(self):
        return "(%s, time:%s)" % ( self.__class__.__name__, self.m_time)

class NoteEventBase(EventBase):
    def __init__(self, pitch, velocity):
        EventBase.__init__(self)
        assert 0 <= pitch
        self.m_pitch = pitch
        self.m_velocity = velocity
    def __str__(self):
        return "(%s, pitch:%s, vel:%s, time:%s)" % (self.__class__.__name__, self.m_pitch, self.m_velocity, self.m_time)

class NoteOnEvent(NoteEventBase):
    def __init__(self, pitch, velocity):
        NoteEventBase.__init__(self, pitch, velocity)

class NoteOffEvent(NoteEventBase):
    def __init__(self, pitch, velocity):
        NoteEventBase.__init__(self, pitch, velocity)

class Delay(EventBase):
    def __init__(self, duration):
        """
        duration is a Rat. Rat(1, 4) denotes a quarter-note.
        """
        EventBase.__init__(self)
        self.m_duration = duration
    def __str__(self):
        return "(%s, dur:%s, time:%s)" % (self.__class__.__name__, self.m_duration, self.m_time)

class SetPatchEvent(EventBase):
    def __init__(self, patch):
        EventBase.__init__(self)
        assert 0 <= patch < 128
        self.m_patch = patch
    def __str__(self):
        return "(%s, time:%s, patch:%i)" % ( self.__class__.__name__, self.m_time, self.m_patch)

class SetVolumeEvent(EventBase):
    def __init__(self, volume):
        EventBase.__init__(self)
        assert 0 <= volume < 256
        self.m_volume = int(volume)
    def __str__(self):
        return "(%s, time:%s, volume:%i)" % ( self.__class__.__name__, self.m_time, self.m_volume)

class TempoEvent(EventBase):
    def __init__(self, bpm, notelen):
        EventBase.__init__(self)
        self.m_bpm = bpm
        self.m_notelen = notelen
    def __str__(self):
        return "(%s, time:%s, bpm/notelen: %s/%s)" % ( self.__class__.__name__, self.m_time, self.m_bpm, self.m_notelen)

class MidiEventStream(object):
    TEMPO = 'tempo'
    VOLUME = 'volume'
    NOTE_ON = 'note-on'
    NOTE_OFF = 'note-off'
    NOTELEN_TIME = 'notelen-time'
    BENDER = 'bender'
    SET_PATCH = 'program-change'
    class ChannelDevice(object):
        """
        Bad name, but I don't have a better idea right now. This
        class will handle all 16 midi channels.
        """
        # We are zero-indexed, so this is MIDI channel 10
        percussion_MIDI_channel = 9
        class MidiChannel(object):
            def __init__(self, number):
                self.m_number = number
                self.m_tones = set()
            def start_tone(self, i):
                assert i not in self.m_tones
                self.m_tones.add(i)
            def stop_tone(self, i):
                assert i in self.m_tones
                self.m_tones.remove(i)
            def is_silent(self):
                """
                Return True if no tones are playing on this channel.
                """
                return not bool(self.m_tones)
        def __init__(self, nc=16):
            self.free_MIDI_channels = []
            if nc > self.percussion_MIDI_channel:
                for i in range(self.percussion_MIDI_channel) \
                         + range(self.percussion_MIDI_channel, 16):
                    self.free_MIDI_channels.append(self.MidiChannel(i))
            else:
                for i in range(nc):
                    self.free_MIDI_channels.append(self.MidiChannel(i))
            # The dict key will be the (patch number, volume).
            # The value is a list of MidiChannel object that play with
            # the patch and volume the key say.
            self.allocated_MIDI_channels = {}
            # This dict maps from MIDI channel number to the actual
            # MidiChannel object
            self.int_to_channel_object = {}
            for channel in self.free_MIDI_channels:
                self.int_to_channel_object[channel.m_number] = channel
        def set_channel_data(self, channel, key, data):
            setattr(self.int_to_channel_object[channel], key, data)
        def get_channel_data(self, channel, key):
            return getattr(self.int_to_channel_object[channel], key, None)
        def require_channel(self, pitch, patch, volume):
            key = (patch, volume)
            if key in self.allocated_MIDI_channels:
                for channel in self.allocated_MIDI_channels[key]:
                    if pitch not in channel.m_tones:
                        return channel.m_number
                else:
                    # we have to alloc a new MIDI channel if the pitch is
                    # already playing
                    self.allocated_MIDI_channels[key].append(self.alloc_channel())
                    return self.allocated_MIDI_channels[key][-1].m_number
            else:
                self.allocated_MIDI_channels[key] = [self.alloc_channel()]
                return self.allocated_MIDI_channels[key][-1].m_number
            return -1
        def alloc_channel(self):
            """
            Return a unused MIDI channel. Search for silent channels first,
            allocate a new if none found.
            """
            if self.free_MIDI_channels:
                return self.free_MIDI_channels.pop(0)
            # First try to find an allocated channel that is silent.
            for key, channel_list in self.allocated_MIDI_channels.items():
                for idx, channel in enumerate(channel_list):
                    if channel.is_silent():
                        ret = self.allocated_MIDI_channels[key].pop(idx)
                        if not self.allocated_MIDI_channels[key]:
                            del self.allocated_MIDI_channels[key]
                        return ret
            raise Exception("FIXME: handle running out of MIDI channels!")
        def get_channel_for_patch(self, patch, volume):
            """
            Return the MIDI channel number we should use to play a tone
            with this patch number. Raise KeyError if no channel is allocated
            yet.
            """
            return self.allocated_MIDI_channels[patch, volume].m_number
        def start_note(self, channel, pitch):
            self.int_to_channel_object[channel].start_tone(pitch)
        def stop_note(self, channel, pitch):
            self.int_to_channel_object[channel].stop_tone(pitch)
        def is_playing(self, channel, pitch):
            return pitch in self.int_to_channel_object[channel].m_tones
    def __init__(self, *tracks):
        # The number of MIDI channels are changed in the test suite to easier
        # test handling of too few midi channels.
        self.num_MIDI_channels = 16
        self.m_tracks = tracks
        for track in self.m_tracks:
            track.calculate_event_times()
    def _create_dict_of_track(self, track):
        """
        Return a dict of the track, where the key is a list with
        all events with the same m_time variable.
        The dict values are a dict with three keys:
        NoteOffEvents, OtherEvents, NoteOnEvents
        """
        retval = {}
        for event in track.m_v:
            retval[event.m_time] = retval.get(event.m_time, [])
            retval[event.m_time].append(event)
        for key in retval:
            retval[key] = {
              'NoteOffEvents': [x for x in retval[key] if isinstance(x, NoteOffEvent)],
              'OtherEvents': [x for x in retval[key] if not isinstance(x, (NoteOffEvent, NoteOnEvent))],
              'NoteOnEvents': [x for x in retval[key] if isinstance(x, NoteOnEvent)]}
        return retval
    def sorted_events(self):
        """
        This method will rearrange the midi events so that all events of the
        same type is after each other. We do this because we want to be
        able to do a little hack after the last SET_PATCH event, it multiple
        SET_PATCH happen at the same time.
        """
        data = {self.NOTELEN_TIME: [],
                self.NOTE_OFF: [],
                self.TEMPO: [],
                self.SET_PATCH: [],
                self.VOLUME: [],
                self.NOTE_ON: []
        }
        for e in self:
            if e[0] == self.NOTELEN_TIME:
                for k in (self.NOTE_OFF, self.TEMPO, self.SET_PATCH,
                          self.VOLUME, self.NOTE_ON):
                    for event in data[k]:
                        yield event
                    data[k] = []
                yield e
            else:
                data[e[0]].append(e)
        for event in data[self.NOTE_OFF]:
            yield event
    def __iter__(self):
        ret = []
        for e in self.__mkevents():
            if e[0] == 'program-change' and ret:
                i = len(ret)
                while (isinstance(ret[i-1][1], Rat) or ret[i-1][1] != e[1]) and i > 1:
                    i -= 1
                if i < len(ret):
                    while ret[i][0] == 'program-change' and i < len(ret) - 1 and ret[i][1] < e[1]:
                        i += 1
                ret.insert(i, e)
            else:
                ret.append(e)
        for e in ret:
            yield e
    def __mkevents(self):
        # tpos_set will know all the positions in time where anything happens
        # on any staff
        tpos_set = set()
        for track in self.m_tracks:
            tpos_set.update([x.m_time for x in track.m_v if x.m_time])
        tracks2 = [self._create_dict_of_track(track) for track in self.m_tracks]
        tpos_list = list(tpos_set)
        tpos_list.sort()
        # We use this variable to remember which instrument
        # we want the track to play.
        track_state = {}
        for x in range(len(self.m_tracks)):
            track_state[x] = {'volume-requested': DEFAULT_VOLUME,
                        'patch-requested': 0}
        tempo_request = None
        tempo_current = None
        # We use this list of dicts to know which MIDI channel the tones are
        # playing on. The key of the dicts are the integer value representing
        # the pitch, and the value is the MIDI channel the tone is playing on.
        track_notes = []
        for x in range(len(self.m_tracks)):
            track_notes.append({})
        ch_dev = self.ChannelDevice(self.num_MIDI_channels)
        last_pos = Rat(0, 1)
        for tpos in tpos_list:
            if tpos != last_pos: # Just to not insert before the first events
                yield self.NOTELEN_TIME, tpos - last_pos
            for idx, track in enumerate(tracks2):
                if tpos in track:
                    for e in track[tpos]['NoteOffEvents']:
                        if e.m_pitch not in track_notes[idx]:
                            # This could happen if the user adds extra NoteOffEvents or adds one
                            # with the wrong pitch.
                            logging.debug("not stopping, not playing now: %s", e)
                            continue
                        chn = track_notes[idx][e.m_pitch]
                        del track_notes[idx][e.m_pitch]
                        assert ch_dev.is_playing(chn, e.m_pitch)
                        ch_dev.stop_note(chn, e.m_pitch)
                        yield self.NOTE_OFF, chn, e.m_pitch, e.m_velocity
            for idx, track in enumerate(tracks2):
                if tpos in track:
                    for e in track[tpos]['OtherEvents']:
                        if isinstance(e, SetPatchEvent):
                            track_state[idx]['patch-requested'] = e.m_patch
                        elif isinstance(e, SetVolumeEvent):
                            track_state[idx]['volume-requested'] = e.m_volume
                        elif isinstance(e, TempoEvent):
                            tempo_request = e
                        else:
                            logging.debug("MidiEventStream: NOT HANDLING EVENT: %s", e)
            for idx, track in enumerate(tracks2):
                if tpos in track:
                    for e in track[tpos]['NoteOnEvents']:
                        assert e.m_pitch not in track_notes[idx]
                        if tempo_request != tempo_current:
                            yield self.TEMPO, tempo_request.m_bpm, tempo_request.m_notelen
                            tempo_current = tempo_request
                        if isinstance(self.m_tracks[idx], PercussionTrack):
                            chn = ch_dev.percussion_MIDI_channel
                            if ch_dev.get_channel_data(chn, 'volume') != track_state[idx]['volume-requested']:
                                ch_dev.set_channel_data(chn, 'volume', track_state[idx]['volume-requested'])
                                yield self.VOLUME, chn, track_state[idx]['volume-requested']
                        else:
                            chn = ch_dev.require_channel(e.m_pitch,
                                        track_state[idx]['patch-requested'],
                                        track_state[idx]['volume-requested'])
                            if ch_dev.get_channel_data(chn, 'patch') != track_state[idx]['patch-requested']:
                                ch_dev.set_channel_data(chn, 'patch', track_state[idx]['patch-requested'])
                                yield self.SET_PATCH, chn, track_state[idx]['patch-requested']
                            if ch_dev.get_channel_data(chn, 'volume') != track_state[idx]['volume-requested']:
                                ch_dev.set_channel_data(chn, 'volume', track_state[idx]['volume-requested'])
                                yield self.VOLUME, chn, track_state[idx]['volume-requested']
                        if ch_dev.is_playing(chn, e.m_pitch):
                            logging.debug("MidiEventStream: ignoring duplicate tone: %s", e)
                            continue
                        track_notes[idx][e.m_pitch] = chn
                        # ch_dev must know which tones are sounding on which
                        # MIDI channels, so it can handle the midi resources.
                        ch_dev.start_note(chn, e.m_pitch)
                        yield self.NOTE_ON, chn, e.m_pitch, e.m_velocity
            last_pos = tpos
    def create_midifile(self, filename, appendstreams=[]):
        """
        filename -- a string naming the file to write the generated midi file to.
                    Will overwrite a existing file.
        appendstrings -- a list of additional MidiEventStreams to append to
                    the midi file.
        """
        v = []
        notelen = 0
        set_patch_flag = False
        v += mfutils.mf_tempo(60 * 4 / 4)
        for stream in [self] + appendstreams:
            for e in stream.sorted_events():
                if e[0] == self.TEMPO:
                    v = v + mfutils.mf_tempo(e[1] * 4 / e[2])
                elif e[0] == self.NOTELEN_TIME:
                    notelen = e[1]
                elif e[0] == self.NOTE_ON:
                    if set_patch_flag:
                        if set_patch_delay:
                            v = v + mfutils.mf_note_off(set_patch_delay, 0, 0, 0)
                        set_patch_flag = False
                    v = v + mfutils.mf_note_on(int(96 * 4 * notelen), e[1], e[2], e[3])
                    notelen = 0
                elif e[0] == self.NOTE_OFF:
                    v = v + mfutils.mf_note_off(int(96 * 4 * notelen), e[1], e[2], e[3])
                    notelen = 0
                elif e[0] == self.SET_PATCH:
                    v = v + mfutils.mf_program_change(e[1], e[2])
                    set_patch_flag = True
                elif e[0] == self.VOLUME:
                    v = v + mfutils.mf_volume_change(e[1], e[2])
                elif e[0] == self.BENDER:
                    logging.debug("create_midifile: FIXME todo: seq_bender for play_with_drvmidi")
                    #m.seq_bender(DEV, e[1], e[2])
                else:
                    raise Exception("mpd.track: Corrupt track error")
        f = open(filename, "w")
        mfutils.MThd(f)
        f.write("MTrk")
        mfutils.write_int32(f, len(v)+4)
        v = v + mfutils.mf_end_of_track()
        mfutils.write_vect(f, v)
        f.close()
    def str_repr(self, details=0):
        v = []
        for e in self:
            if e[0] == self.TEMPO:
                v.append("t%s/%s" % (e[1], e[2]))
            elif e[0] == self.NOTE_ON:
                if e[1] == 9:
                    v.append("P%s" % e[2])
                else:
                    if details == 0:
                        v.append("n%s" % e[2])
                    elif details == 1:
                        v.append("n%s:%s" % (e[1], e[2]))
            elif e[0] == self.NOTE_OFF:
                v.append("o%s" % e[2])
            elif e[0] == self.SET_PATCH:
                v.append("p%i:%i" % (e[1], e[2]))
            elif e[0] == self.VOLUME:
                v.append("v%i:%i" % (e[1], e[2]))
            elif e[0] == self.NOTELEN_TIME:
                v.append("d%i/%i" % (e[1].m_num, e[1].m_den))
        return " ".join(v)


class Track:
    """
    A pitch is represented by an integer value 0-127.
    * There can only be one instance of a pitch sounding at the same time.
    * There can only be one instrument sounding at the same time.
    Right now there are no code that checks that this is true while
    adding notes.
    """
    def txtdump(self):
        for event in self.m_v:
            print event
    def str_repr(self):
        retval = []
        for e in self.m_v:
            if isinstance(e, SetPatchEvent):
                retval.append('p%i' % e.m_patch)
            elif isinstance(e, TempoEvent):
                retval.append('t%i/%i' % (e.m_bpm, e.m_notelen))
            elif isinstance(e, SetVolumeEvent):
                retval.append('v%i' % e.m_volume)
            elif isinstance(e, NoteOnEvent):
                retval.append('n%i' % e.m_pitch)
            elif isinstance(e, NoteOffEvent):
                retval.append('o%i' % e.m_pitch)
            elif isinstance(e, Delay):
                retval.append('d%i/%i' % (e.m_duration.m_num, e.m_duration.m_den))
        return " ".join(retval)
    def __init__(self, default_velocity=None):
        if default_velocity is None:
            self.m_default_velocity = DEFAULT_VELOCITY
        else:
            self.m_default_velocity = default_velocity
        self.m_v = []
    def start_note(self, pitch, vel=None):
        assert 0 <= int(pitch) < 128
        if vel is None:
            vel = self.m_default_velocity
        assert 0 <= vel < 128
        self.m_v.append(NoteOnEvent(int(pitch), int(vel)))
    def stop_note(self, pitch, vel=None):
        assert 0 <= int(pitch) < 128
        if vel is None:
            vel = self.m_default_velocity
        assert 0 <= vel < 128
        self.m_v.append(NoteOffEvent(int(pitch), int(vel)))
    def notelen_time(self, notelen):
        """
        To avoid having to alter all code calling this, we interpret
        notelen in two different ways depending on its type:
        int: replace to Rat(1, notelen)
        Rat: the value tell the note length. For example Rat(1, 4) for a
             quarter note.
        """
        if isinstance(notelen, int):
            self.m_v.append(Delay(Rat(1, notelen)))
        else:
            assert isinstance(notelen, Rat)
            self.m_v.append(Delay(notelen))
    def note(self, notelen, pitch, vel=None):
        """
        See notelen_time docstring.
        """
        if vel is None:
            vel = self.m_default_velocity
        assert 0 <= vel < 128
        self.start_note(pitch, vel)
        self.notelen_time(notelen)
        self.stop_note(pitch, vel)
    def set_patch(self, patch):
        """
        Add an event that will change the midi instrument for the
        notes following this event.
        """
        self.m_v.append(SetPatchEvent(patch))
    def prepend_patch(self, patch):
        """
        Insert an event that will change the midi instrument at the
        beginning of the track. If you call this method several times,
        only the first call will have any effect.
        """
        self.m_v.insert(0, SetPatchEvent(patch))
    def set_volume(self, volume):
        self.m_v.append(SetVolumeEvent(volume))
    def prepend_volume(self, volume):
        self.m_v.insert(0, SetVolumeEvent(volume))
    def set_bpm(self, bpm, notelen=4):
        self.m_v.append(TempoEvent(bpm, notelen))
    def prepend_bpm(self, bpm, notelen=4):
        self.m_v.insert(0, TempoEvent(bpm, notelen))
    def bender(self, chn, value):
        "value >= 0"
        self.m_v.append([self.BENDER, chn, value])
    def merge_with(self, B):
        D = {}
        for track in [self, B]:
            pos = Rat(0, 1)
            for event in track.m_v:
                if isinstance(event, Delay):
                    pos = pos + event.m_duration
                else:
                    if pos not in D:
                        D[pos] = []
                    D[pos].append(event)
        kv = D.keys()
        kv.sort()
        self.m_v = []
        for x in range(len(kv)-1):
            for event in D[kv[x]]:
                self.m_v.append(event)
            self.m_v.append(Delay(kv[x+1]-kv[x]))
        for event in D[kv[-1]]:
            self.m_v.append(event)
    def replace_note(self, old, new):
        assert isinstance(old, int)
        assert 0 <= old < 128
        assert isinstance(new, int)
        assert 0 <= new < 128
        for event in self.m_v:
            if isinstance(event, (NoteOnEvent, NoteOffEvent)) \
                    and event.m_pitch == old:
                event.m_pitch = new
    def calculate_event_times(self):
        """
        Set the variable m_time on each Event. Well actually we don't set
        it on the Delay events because events of that type does not generate
        any events when generating music.
        """
        pos = Rat(0, 1)
        for e in self.m_v:
            if isinstance(e, Delay):
                pos += e.m_duration
            else:
                e.m_time = pos

class PercussionTrack(Track):
    def __init__(self):
        Track.__init__(self)

