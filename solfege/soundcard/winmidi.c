/* GNU Solfege - ear training for GNOME
 * Copyright (C) 2001 Joe Lee
 *
 * Ported to gcc by Steve Lee
 *
 * This program is free software; you can redistribute it and/or modify
 *it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin ST, Fifth Floor, Boston, MA  02110-1301  USA
 */

//lint -e725

/////////////////////////////////////////////////////////////////////////////
// Don't define/include unused stuff
#define WIN32_LEAN_AND_MEAN
#define NOGDI
#define NOSERVICE
#define NOMCX
#define NOIME

#include <windows.h>
#include <windowsx.h>

/////////////////////////////////////////////////////////////////////////////
// Turn off warnings for /W4
// To resume any of these warning: #pragma warning(default: 4xxx)
#ifndef ALL_WARNINGS
#pragma warning(disable: 4201)  // mmsystem.h uses nameless structs
#endif

#include <mmsystem.h>

#include <python.h>
//#include <stdio.h>
//#include <string.h>
//#include <stdlib.h>
//#include <assert.h>

#define UNUSED(x) ((void)x)	// for unreferenced parameters

#define DLL_EXPORT __declspec(dllexport)


////////////////////////////////////////////////////////

#define MAX_MIDI_BLOCK_SIZE 1024

enum {
	BLOCK_WRITING = 0,
	BLOCK_READY,
	BLOCK_PLAYING,
	BLOCK_PLAYED 
};

struct tag_MidiBlock {
	MIDIHDR m_header;
	int m_blockState;
	struct tag_MidiBlock* m_next;
};
typedef struct tag_MidiBlock MidiBlockNode;

typedef struct {
	PyObject_HEAD

	int m_initialized;
	HMIDISTRM m_midiOut;
	MidiBlockNode *m_list;
	MidiBlockNode *m_playNode;
	MidiBlockNode *m_listEnd;
} WinmidiObject;


static PyTypeObject s_winmidiObjectType;

static PyObject *s_output_devices(PyObject *self, PyObject *args);
static PyObject *Winmidi_New(PyObject *self, PyObject *args);
static void Winmidi_Dealloc(WinmidiObject *obj);
static PyObject *Winmidi_GetAttr(WinmidiObject *self, char *name);
static PyObject *Winmidi_NoteOn(PyObject *self, PyObject *args);
static PyObject *Winmidi_NoteOff(PyObject *self, PyObject *args);
static PyObject *Winmidi_ProgramChange(PyObject *self, PyObject *args);
static PyObject *Winmidi_SetTempo(PyObject *self, PyObject *args);
static PyObject *Winmidi_Play(PyObject *self, PyObject *args);
static PyObject *Winmidi_Reset(PyObject *self, PyObject *args);


static PyMethodDef s_winmidiObjectMethods[] = {
	{"note_on", 		Winmidi_NoteOn, 		METH_VARARGS,	NULL},
	{"note_off",		Winmidi_NoteOff,		METH_VARARGS,	NULL},
	{"program_change",	Winmidi_ProgramChange,	METH_VARARGS,	NULL},
	{"set_tempo",		Winmidi_SetTempo,		METH_VARARGS,	NULL},
	{"play",			Winmidi_Play,			METH_VARARGS,	NULL},
	{"reset",			Winmidi_Reset,			METH_VARARGS,	NULL},
	{NULL,				NULL,					0,				NULL}
};


static PyMethodDef s_winmidiMethods[] = {
	{"Winmidi", 	Winmidi_New,		METH_VARARGS,	NULL},
	{"output_devices", s_output_devices,    METH_NOARGS, NULL},       
	{NULL,			NULL,				0,				NULL}
};


static void s_SetMidiError(const char *reason, UINT val) {
	UINT retVal;
	char errBuffer[MAXERRORLENGTH];

	retVal = midiOutGetErrorText(val, errBuffer, MAXERRORLENGTH);
	if(retVal == MMSYSERR_NOERROR) {
	/* Returned OK.  Do nothing. */

	} else if(retVal == MMSYSERR_BADERRNUM) {
	sprintf(errBuffer, "Unrecognized MIDI error occurred (%d).", val);

	} else if(retVal == MMSYSERR_INVALPARAM) {
	sprintf(errBuffer, "Invalid error parameter found while retrieving error %d.", val);

	} else {
	sprintf(errBuffer, "Unknown error occurred while retrieving error %d.", val);
	}

	(void)PyErr_Format(PyExc_RuntimeError, "MIDI error encountered while %s: %s", reason, errBuffer);
}


static void FAR PASCAL s_MidiCallback(HMIDISTRM hms, UINT uMsg, DWORD dwUser, DWORD dw1, DWORD dw2) {
	WinmidiObject *obj = (WinmidiObject *) dwUser;
	int retVal;

	UNUSED(hms);
	UNUSED(dw1);
	UNUSED(dw2);

	assert(obj);

	/* Only process Done messages. */
	if(uMsg != MOM_DONE) {
	return;
	}

	while(obj->m_playNode) {
	/* Clear the playing flag. */
	obj->m_playNode->m_blockState = BLOCK_PLAYED;

	/* Play the next block, if available. */
	obj->m_playNode = obj->m_playNode->m_next;
	if(obj->m_playNode) {
		/* Check to see if we have exhausted the ready blocks. */
		if(obj->m_playNode->m_blockState != BLOCK_READY) {
		return;
		}

		obj->m_playNode->m_blockState = BLOCK_PLAYING;

		retVal = midiStreamOut(obj->m_midiOut, &obj->m_playNode->m_header,
			sizeof(obj->m_playNode->m_header));
		if(retVal == MMSYSERR_NOERROR) {
		return;
		} else {
		fprintf(stderr, "Error occurred while advancing MIDI block pointer.\n");
		}
	} else {
		retVal = midiStreamPause(obj->m_midiOut);
		if(retVal != MMSYSERR_NOERROR) {
		fprintf(stderr, "Error occurred while pausing MIDI playback.");
		}
		return;
	}
	}
}


static int s_PrepareBlockNodes(WinmidiObject *obj) {
	UINT retVal;
	MidiBlockNode *node;
	MidiBlockNode *firstReady = 0;

	assert(obj);

	/* Go through the list and prepare all written blocks. */
	node = obj->m_list;
	while(node) {
	if(node->m_blockState == BLOCK_WRITING) {
		if(!firstReady) {
		firstReady = node;
		}

		retVal = midiOutPrepareHeader((HMIDIOUT)obj->m_midiOut,
			&node->m_header,
			sizeof(node->m_header));
		if(retVal != MMSYSERR_NOERROR) {
		s_SetMidiError("preparing header", retVal);
		return 0;
		}

		node->m_blockState = BLOCK_READY;
	}
	node = node->m_next;
	}

	/* If we actually prepared some blocks for playing, queue the first
	 * one. */
	if(!obj->m_playNode && firstReady) {
	obj->m_playNode = firstReady;
	(void)midiStreamOut(obj->m_midiOut, &firstReady->m_header,
		sizeof(firstReady->m_header));
	}

	retVal = midiStreamRestart(obj->m_midiOut);
	if(retVal != MMSYSERR_NOERROR) {
	s_SetMidiError("restarting MIDI stream", retVal);
	return 0;
	}

	return 1;
}


static int s_CleanUpBlockNodes(WinmidiObject *obj) {
	UINT retVal;
	MidiBlockNode *node, *nextNode;

	assert(obj);

	node = obj->m_list;
	while(node) {
	nextNode = node->m_next;
	if(node->m_blockState == BLOCK_PLAYED) {
		obj->m_list = node->m_next;
		if(node == obj->m_listEnd) {
		obj->m_listEnd = 0;
		}

		/* Dispose of the block. */
		retVal = midiOutUnprepareHeader((HMIDIOUT)obj->m_midiOut, &node->m_header,
			sizeof(node->m_header));
		if(retVal != MMSYSERR_NOERROR) {
		s_SetMidiError("unpreparing header", retVal);
		return 0;
		} else {
		(void)GlobalFreePtr(node->m_header.lpData);
		free(node);
		}
	}
	node = nextNode;
	}

	return 1;
}


static int s_FreeNodes(WinmidiObject *obj) {
	MidiBlockNode *node, *nextNode;

	assert(obj);

	node = obj->m_list;
	while(node) {
	nextNode = node->m_next;
	obj->m_list = node->m_next;
	if(node == obj->m_listEnd) {
		obj->m_listEnd = 0;
	}

	/* Dispose of the block. */
	(void)GlobalFreePtr(node->m_header.lpData);
	free(node);

	node = nextNode;
	}

	return 1;
}


int s_ResetMidiStream(WinmidiObject *obj, UINT devNum) {
	UINT retVal;

	assert(obj);

	(void)midiOutReset((HMIDIOUT)obj->m_midiOut);
	if(!s_CleanUpBlockNodes(obj)) {
	return 0;
	}
	(void)midiStreamClose(obj->m_midiOut);
	if(!s_FreeNodes(obj)) {
	return 0;
	}

	retVal = midiStreamOpen(&(obj->m_midiOut), &devNum, 1,
		(DWORD) s_MidiCallback, (DWORD) obj, CALLBACK_FUNCTION); //lint !e620
	if(retVal != MMSYSERR_NOERROR) {
	s_SetMidiError("opening a MIDI stream", retVal);
	return 0;
	}
	assert(obj->m_midiOut);
	
	return 1;
}


static int s_SetUpNewBlock(WinmidiObject *obj) {
	MidiBlockNode *node;

	assert(obj);
	node = malloc(sizeof(MidiBlockNode));
	if(!node) {
	PyErr_SetString(PyExc_RuntimeError,
		"Out of memory while allocating MIDI block.");
	return 0;
	}

	/* Allocate MIDI buffer memory. */
	memset(node, 0, sizeof(MidiBlockNode));
	node->m_header.lpData = GlobalAllocPtr(GMEM_MOVEABLE | GMEM_SHARE,
		MAX_MIDI_BLOCK_SIZE);
	if(!node->m_header.lpData) {
	PyErr_SetString(PyExc_RuntimeError,
		"Out of memory while allocating MIDI block.");
	free(node);
	return 0;
	}
	node->m_header.dwBufferLength = MAX_MIDI_BLOCK_SIZE;
	node->m_blockState = BLOCK_WRITING;

	/* Place new block at end of the list. */
	if(!obj->m_listEnd) {
	assert(!obj->m_list);
	obj->m_listEnd = node;
	obj->m_list = node;
	} else {
	obj->m_listEnd->m_next = node;
	obj->m_listEnd = node;
	}

	return 1;
}


static MIDIEVENT *s_PrepWriteBlock(WinmidiObject *obj, int size) {
	MidiBlockNode *node;
	MIDIEVENT *midiEvent;
	assert(obj);

	node = obj->m_listEnd;
	if(!node) {
	/* If there are no blocks in the list, get a new one. */
	if(!s_SetUpNewBlock(obj)) {
		return 0;
	}

	} else if(node->m_blockState != BLOCK_WRITING) {
	/* If the last block is not a writing block, get a new one.*/
	if(!s_SetUpNewBlock(obj)) {
		return 0;
	}

	} else if(node->m_header.dwBytesRecorded + size * sizeof(DWORD) >
		node->m_header.dwBufferLength) {
	/* If there's not enough room in the last block, get a new one. */ 
	if(!s_SetUpNewBlock(obj)) {
		return 0;
	}
	}

	/* We're OK for writing. */
	node = obj->m_listEnd;
	assert(node);
	assert(node->m_blockState == BLOCK_WRITING);
	midiEvent =
	(MIDIEVENT *) (node->m_header.lpData + node->m_header.dwBytesRecorded);
	node->m_header.dwBytesRecorded += size * sizeof(DWORD);

	return midiEvent;
}


static PyObject *s_output_devices(PyObject *self, PyObject *args) {
	MIDIOUTCAPS caps;
	UINT		numDevs, i;
	PyObject    *result;
	
	result = PyList_New(0);
	numDevs = midiOutGetNumDevs();
	if (midiOutGetDevCaps(MIDI_MAPPER, &caps, sizeof(caps)) == 0)
		PyList_Append(result, PyString_FromString(caps.szPname));
	else
		PyList_Append(result, Py_None);		
	for(i = 0; i < numDevs; i++) {
		if (midiOutGetDevCaps(i, &caps, sizeof(caps)) == 0)
			PyList_Append(result, PyString_FromString(caps.szPname));
		else
			PyList_Append(result, Py_None);		
	}
	return result;
}

static PyObject *Winmidi_New(PyObject *self, PyObject *args) {
	WinmidiObject *obj;
	UINT		retVal;
	UINT		numDevs;
	UINT		devNum;

	UNUSED(self);

	if(!PyArg_ParseTuple(args, "i:Winmidi", &devNum)) {
	return NULL;
	}

	/* Initialize the new object. */
	obj = PyObject_NEW(WinmidiObject, &s_winmidiObjectType);
	if(!obj) {
	return NULL;
	}
	obj->m_midiOut = 0;
	obj->m_initialized = 0;
	obj->m_playNode = 0;
	obj->m_list = 0;
	obj->m_listEnd = 0;

	/* Get the number of MIDI devices on the system. */
	numDevs = midiOutGetNumDevs();
	if(numDevs == 0) {
	PyErr_SetString(PyExc_RuntimeError, 
		"No MIDI output devices found.");
	Py_DECREF(obj);
	return NULL;
	}

	/* Open the MIDI output device. */
	obj->m_midiOut = 0;
	retVal = midiStreamOpen(&(obj->m_midiOut), &devNum, 1,
		(DWORD) s_MidiCallback, (DWORD) obj, CALLBACK_FUNCTION); //lint !e620
	if(retVal != MMSYSERR_NOERROR) {
	s_SetMidiError("opening a MIDI stream", retVal);
	Py_DECREF(obj);
	return NULL;
	}
	assert(obj->m_midiOut);

	/* printf("Winmidi object created.\n"); */
	return (PyObject *) obj;
}


static void Winmidi_Dealloc(WinmidiObject *obj) {
	assert(obj);

	/* XXX - s_CleanUpBlockNodes and s_FreeNodes set the Python error
	 * string on errors...	Should we do something different? */
	if (obj->m_midiOut)
        midiStreamStop(obj->m_midiOut);
    (void)s_CleanUpBlockNodes(obj);
	(void)midiStreamClose(obj->m_midiOut);
	(void)s_FreeNodes(obj);

	/* printf("Winmidi object destroyed.\n"); */
	PyObject_Del(obj);
}


static PyObject *Winmidi_GetAttr(WinmidiObject *self, char *name) {
	return Py_FindMethod(s_winmidiObjectMethods, (PyObject *) self, name);
}


static PyObject *Winmidi_NoteOn(PyObject *self, PyObject *args) {
	int delta, channel, note, vel;
	WinmidiObject *obj;
	MIDIEVENT *evt;

	if(!PyArg_ParseTuple(args, "iiii:note_on", &delta, &channel,
		&note, &vel)) {
	return NULL;
	}
	if(channel < 0 || channel >= 16) {
	PyErr_SetString(PyExc_RuntimeError, "channel out of range");
	return NULL;
	}
	if(note < 0 || note >= 128) {
	PyErr_SetString(PyExc_RuntimeError, "note out of range");
	return NULL;
	}
	if(vel < 0 || vel >= 128) {
	PyErr_SetString(PyExc_RuntimeError, "vel out of range");
	return NULL;
	}
	obj = (WinmidiObject *) self;
	if(!obj) {
	PyErr_SetString(PyExc_RuntimeError, "invalid Winmidi object");
	return NULL;
	}

	/* printf("Note on:  %d %d %d %d\n", delta, channel, note, vel); */
	evt = s_PrepWriteBlock(obj, 3);
	if(!evt) {
	return NULL;
	}
	evt->dwDeltaTime = (DWORD)delta;
	evt->dwStreamID = 0;
	evt->dwEvent = ((MEVT_SHORTMSG) << 24) +
	(((DWORD)vel) << 16) +
	(((DWORD)note) << 8) +
	(((DWORD)channel + 0x90U));

	Py_INCREF(Py_None);
	return Py_None;
}

static PyObject *Winmidi_NoteOff(PyObject *self, PyObject *args) {
	int delta, channel, note, vel;
	WinmidiObject *obj;
	MIDIEVENT *evt;

	if(!PyArg_ParseTuple(args, "iiii:note_off", &delta, &channel,
		&note, &vel)) {
	return NULL;
	}
	if(channel < 0 || channel >= 16) {
	PyErr_SetString(PyExc_RuntimeError, "channel out of range");
	return NULL;
	}
	if(note < 0 || note >= 128) {
	PyErr_SetString(PyExc_RuntimeError, "note out of range");
	return NULL;
	}
	if(vel < 0 || vel >= 128) {
	PyErr_SetString(PyExc_RuntimeError, "vel out of range");
	return NULL;
	}
	obj = (WinmidiObject *) self;
	if(!obj) {
	PyErr_SetString(PyExc_RuntimeError, "invalid Winmidi object");
	return NULL;
	}

	/* printf("Note off: %d %d %d %d\n", delta, channel, note, vel); */
	evt = s_PrepWriteBlock(obj, 3);
	if(!evt) {
	return NULL;
	}
	evt->dwDeltaTime = (DWORD)delta;
	evt->dwStreamID = 0;
	evt->dwEvent = ((MEVT_SHORTMSG) << 24) +
	(((DWORD)vel) << 16) +
	(((DWORD)note) << 8) +
	(((DWORD)channel + 0x80U));

	Py_INCREF(Py_None);
	return Py_None;
}


static PyObject *Winmidi_ProgramChange(PyObject *self, PyObject *args) {
	int channel, program;
	WinmidiObject *obj;
	MIDIEVENT *evt;

	if(!PyArg_ParseTuple(args, "ii:program_change", &channel, &program)) {
	return NULL;
	}
	if(channel < 0 || channel >= 16) {
	PyErr_SetString(PyExc_RuntimeError, "channel out of range");
	return NULL;
	}
	if(program < 0 || program >= 128) {
	PyErr_SetString(PyExc_RuntimeError, "program out of range");
	return NULL;
	}
	obj = (WinmidiObject *) self;
	if(!obj) {
	PyErr_SetString(PyExc_RuntimeError, "invalid Winmidi object");
	return NULL;
	}

	/* printf("Program change: %d %d\n", channel, program); */
	evt = s_PrepWriteBlock(obj, 3);
	if(!evt) {
	return NULL;
	}
	evt->dwDeltaTime = 0;
	evt->dwStreamID = 0;
	evt->dwEvent = ((MEVT_SHORTMSG) << 24) +
	(((DWORD)program) << 8U) +
	(((DWORD)channel + 0xc0U));

	Py_INCREF(Py_None);
	return Py_None;
}


static PyObject *Winmidi_SetTempo(PyObject *self, PyObject *args) {
	int tempo;
	WinmidiObject *obj;
	MIDIEVENT *evt;

	if(!PyArg_ParseTuple(args, "i:set_tempo", &tempo)) {
	return NULL;
	}
	if((unsigned int) tempo >= (unsigned int) (1 << 24)) {
	PyErr_SetString(PyExc_RuntimeError, "tempo out of range");
	return NULL;
	}
	obj = (WinmidiObject *) self;
	if(!obj) {
	PyErr_SetString(PyExc_RuntimeError, "invalid Winmidi object");
	return NULL;
	}

	/* printf("Tempo: %d\n", tempo); */
	evt = s_PrepWriteBlock(obj, 3);
	if(!evt) {
	return NULL;
	}
	evt->dwDeltaTime = 0;
	evt->dwStreamID = 0;
	evt->dwEvent = ((MEVT_TEMPO) << 24) +
	(tempo);


	Py_INCREF(Py_None);
	return Py_None;
}


static PyObject *Winmidi_Play(PyObject *self, PyObject *args) {
	WinmidiObject *obj;
	
	if(!PyArg_ParseTuple(args, ":play")) {
	return NULL;
	}
	obj = (WinmidiObject *) self;
	if(!obj) {
	PyErr_SetString(PyExc_RuntimeError, "invalid Winmidi object");
	return NULL;
	}

	/* printf("Play called.\n"); */
	if(!s_CleanUpBlockNodes(obj)) {
	return NULL;
	}
	if(!s_PrepareBlockNodes(obj)) {
	return NULL;
	}		

	Py_INCREF(Py_None);
	return Py_None;
}


static PyObject *Winmidi_Reset(PyObject *self, PyObject *args) {
	WinmidiObject *obj;
	UINT devNum;
	
	if(!PyArg_ParseTuple(args, "i:reset", &devNum)) {
	return NULL;
	}
	obj = (WinmidiObject *) self;
	if(!obj) {
	PyErr_SetString(PyExc_RuntimeError, "invalid Winmidi object");
	return NULL;
	}

	if(!s_ResetMidiStream(obj, devNum)) {
	return NULL;
	}

	Py_INCREF(Py_None);
	return Py_None;
}


DLL_EXPORT void initwinmidi(void) {
	PyObject *m = Py_InitModule("winmidi", s_winmidiMethods);
	if(!m) {
	return;
	}

	memset(&s_winmidiObjectType, 0, sizeof(s_winmidiObjectType));
	s_winmidiObjectType.ob_type = &PyType_Type;
	s_winmidiObjectType.tp_name = "Winmidi";
	s_winmidiObjectType.tp_basicsize = sizeof(WinmidiObject);
	s_winmidiObjectType.tp_dealloc = (destructor) Winmidi_Dealloc;
	s_winmidiObjectType.tp_getattr = (getattrfunc) Winmidi_GetAttr;

}

/* vim:set sw=4 sta: */
