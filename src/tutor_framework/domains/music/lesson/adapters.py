"""Bounded local media verification helpers. Remote providers are never implied."""
from __future__ import annotations
import math, struct
from fractions import Fraction

LOCAL_PROVIDERS={"kokoro-local","musescore-local","verovio-local"}

def require_local_provider(provider:str)->None:
    if provider not in LOCAL_PROVIDERS:
        raise PermissionError("remote or paid provider requires a separate production authorization")

def _var(data:bytes,i:int):
    value=0
    for _ in range(4):
        if i>=len(data): raise ValueError("truncated MIDI variable integer")
        b=data[i]; i+=1; value=(value<<7)|(b&127)
        if b<128: return value,i
    raise ValueError("invalid MIDI variable integer")

def midi_notes(raw:bytes)->list[dict]:
    if len(raw)<14 or raw[:4]!=b"MThd": raise ValueError("invalid MIDI header")
    hlen,fmt,ntracks,division=struct.unpack(">IHHH",raw[4:14])
    if hlen<6 or fmt not in (0,1) or not ntracks or division<=0 or division&0x8000:
        raise ValueError("unsupported MIDI header")
    pos=8+hlen; events=[]
    for track in range(ntracks):
        if pos+8>len(raw) or raw[pos:pos+4]!=b"MTrk": raise ValueError("missing MIDI track")
        size=struct.unpack(">I",raw[pos+4:pos+8])[0]; data=raw[pos+8:pos+8+size]; pos+=8+size
        if len(data)!=size: raise ValueError("truncated MIDI track")
        i=tick=0; running=None
        while i<len(data):
            delta,i=_var(data,i); tick+=delta
            if i>=len(data): raise ValueError("missing MIDI status")
            status=data[i]
            if status>=128: i+=1
            elif running is not None: status=running
            else: raise ValueError("running status without predecessor")
            if status==255:
                running=None
                if i>=len(data): raise ValueError("truncated MIDI meta")
                kind=data[i]; i+=1; n,i=_var(data,i); value=data[i:i+n]; i+=n
                if len(value)!=n: raise ValueError("truncated MIDI meta payload")
                if kind==81:
                    if n!=3 or int.from_bytes(value,"big")<=0: raise ValueError("invalid tempo")
                    events.append((tick,-1,track,"tempo",0,int.from_bytes(value,"big"),None))
                continue
            if status in (240,247):
                running=None; n,i=_var(data,i); i+=n
                if i>len(data): raise ValueError("truncated MIDI sysex")
                continue
            if not 128<=status<=239: raise ValueError("invalid MIDI status")
            running=status; kind=status>>4; channel=status&15; length=1 if kind in (12,13) else 2
            vals=data[i:i+length]; i+=length
            if len(vals)!=length or any(v>=128 for v in vals): raise ValueError("invalid MIDI message")
            if kind in (8,9):
                on=kind==9 and vals[1]!=0
                events.append((tick,1 if on else 0,track,"on" if on else "off",channel,vals[0],kind))
    tempo=500000; last=0; seconds=Fraction(0); active={}; notes=[]
    for tick,_,track,kind,channel,value,status_kind in sorted(events,key=lambda e:(e[0],e[1],e[2],str(e[3]))):
        seconds += Fraction((tick-last)*tempo,division*1_000_000); last=tick
        if kind=="tempo": tempo=value; continue
        key=(track,channel,value)
        if kind=="on":
            if key in active: raise ValueError("overlapping equal-pitch attacks")
            active[key]=seconds
        else:
            if key not in active: raise ValueError("note-off lacks preceding attack")
            start=active.pop(key)
            if seconds<=start: raise ValueError("nonpositive MIDI note")
            notes.append({"midi":value,"start":float(start),"duration":float(seconds-start),"track":track,"channel":channel})
    if active: raise ValueError("unterminated MIDI notes")
    return sorted(notes,key=lambda x:(x["start"],x["midi"],x["track"]))

def compare_midi(expected:list[dict],actual:list[dict],bpm:str)->dict:
    tempo=Fraction(60,1)/Fraction(bpm)
    wanted=sorted(({"midi":e["midi"],"start":float(Fraction(e["onset"])*tempo)} for e in expected if e["midi"] is not None),key=lambda x:(x["start"],x["midi"]))
    got=sorted(actual,key=lambda x:(x["start"],x["midi"]))
    onset_errors=[]; pitch_errors=[]
    for i,(a,b) in enumerate(zip(wanted,got)):
        onset_errors.append(abs(a["start"]-b["start"])*1000)
        if a["midi"]!=b["midi"]: pitch_errors.append(i)
    ok=len(wanted)==len(got) and not pitch_errors and max(onset_errors,default=0)<=2
    return {"state":"passed" if ok else "failed","expected_attacks":len(wanted),"midi_attacks":len(got),"pitch_mismatch_indices":pitch_errors,"max_onset_error_ms":max(onset_errors,default=0)}
