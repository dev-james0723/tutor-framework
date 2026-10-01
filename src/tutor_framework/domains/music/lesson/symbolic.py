"""Rational, all-part MusicXML timing and explicit performance traversal.

A deliberately bounded reader: unsupported timing is an error, not a silently
invented note. It never performs recognition or claims source-score verification.
Playback beats are notated beat units; a pickup's local first beat starts at zero.
"""
from __future__ import annotations

import hashlib
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, replace
from fractions import Fraction as F
from .models import Passage


@dataclass(frozen=True)
class Event:
    event_id: str
    part: str
    measure: str
    occurrence: int
    voice: str
    staff: str
    onset: F
    duration: F
    midi: int | None
    tie_start: bool = False
    tie_stop: bool = False
    notation_ids: tuple[str, ...] = ()

    def record(self) -> dict:
        return {k: str(v) if isinstance(v, F) else v for k,v in self.__dict__.items()}


@dataclass(frozen=True)
class SymbolicScore:
    parts: tuple[str, ...]
    labels: tuple[str, ...]
    spans: dict[str, F]
    beat_units: dict[str, F]
    events: tuple[Event, ...]
    revision: str
    warnings: tuple[str, ...]


def parse_score(payload: str | bytes) -> SymbolicScore:
    raw = payload.encode() if isinstance(payload, str) else payload
    if not isinstance(raw, bytes) or len(raw) > 2_000_000:
        raise ValueError('MusicXML must be at most 2 MB')
    if b'<!entity' in raw.lower() or b'<![' in raw.lower():
        raise ValueError('XML entity declarations and internal subsets are forbidden')
    # A normal MusicXML PUBLIC doctype is metadata only. Strip it without ever
    # fetching its external DTD. Everything else is rejected before parsing.
    raw = re.sub(rb'<!DOCTYPE\s+score-partwise\s+PUBLIC\s+"[^"<>\[\]]*"\s+"[^"<>\[\]]*"\s*>', b'', raw)
    if b'<!doctype' in raw.lower():
        raise ValueError('unsupported XML doctype')
    try:root = ET.fromstring(raw)
    except ET.ParseError as exc:raise ValueError('invalid MusicXML') from exc
    for e in root.iter():e.tag=e.tag.rsplit('}',1)[-1]
    if root.tag != 'score-partwise':raise ValueError('only score-partwise MusicXML is supported')
    parts=[]; events=[]; spans={}; units={}; order=None; warnings=set()
    for part in root.findall('part'):
        pid=part.get('id','')
        if not pid or pid in parts:raise ValueError('missing or duplicate part ID')
        parts.append(pid); divisions=F(1); beats=F(4); unit=F(1); transpose=0; labels=[]
        for measure in part.findall('measure'):
            label=measure.get('number','')
            if not label or label in labels:raise ValueError('missing or duplicate printed measure label; disambiguate endings')
            labels.append(label); cursor=F(0); extent=F(0); last=None; index=0
            for child in measure:
                if child.tag=='attributes':
                    d=child.findtext('divisions')
                    if d is not None:
                        divisions=F(d)
                        if divisions<=0:raise ValueError('divisions must be positive')
                    t=child.find('time')
                    if t is not None:
                        try:beats=F(t.findtext('beats'));unit=F(4,int(t.findtext('beat-type')))
                        except (TypeError,ValueError,ZeroDivisionError) as exc:raise ValueError('unsupported meter') from exc
                        if beats<=0 or unit<=0:raise ValueError('invalid meter')
                    tr=child.find('transpose')
                    if tr is not None:
                        transpose=int(tr.findtext('chromatic','0'))+12*int(tr.findtext('octave-change','0'))
                        if tr.find('double') is not None:raise ValueError('double transposition needs explicit notation review')
                elif child.tag in {'backup','forward'}:
                    amount=F(child.findtext('duration','0'))/divisions
                    if amount<=0:raise ValueError('invalid cursor movement')
                    cursor += amount if child.tag=='forward' else -amount
                    if cursor<0:raise ValueError('backup before measure start')
                    extent=max(extent,cursor);last=None
                elif child.tag=='note':
                    index+=1
                    if child.find('grace') is not None or child.find('unpitched') is not None:
                        raise ValueError('grace or unpitched note needs an explicit supported adapter')
                    try:duration=F(child.findtext('duration'))/divisions
                    except (ValueError,TypeError,ZeroDivisionError) as exc:raise ValueError('invalid note duration') from exc
                    if duration<=0:raise ValueError('note duration must be positive')
                    voice=child.findtext('voice','1');staff=child.findtext('staff','1')
                    chord=child.find('chord') is not None
                    if chord:
                        if last is None or last[1:]!=(voice,staff):raise ValueError('orphan or cross-voice chord')
                        onset=last[0]
                    else:
                        onset=cursor;last=(onset,voice,staff);cursor+=duration
                    midi=None
                    if child.find('rest') is None:
                        pitch=child.find('pitch')
                        if pitch is None:raise ValueError('missing pitch or rest')
                        step=pitch.findtext('step');octave=int(pitch.findtext('octave'))
                        alter=F(pitch.findtext('alter','0'))
                        if alter.denominator!=1 or step not in 'CDEFGAB':raise ValueError('unsupported pitch spelling/microtone')
                        midi=12*(octave+1)+{'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}[step]+int(alter)+transpose
                        if not 0<=midi<=127:raise ValueError('sounding MIDI pitch outside range')
                    types={t.get('type') for t in child.findall('tie')}
                    if types-{'start','stop'}:raise ValueError('unsupported tie')
                    if child.find('notations/ornaments') is not None:warnings.add('ornaments require separately reviewed playback realization')
                    if child.get('print-object')=='no':warnings.add('hidden notation present; inspect its musical role')
                    nid=child.get('id') or f'{pid}:{label}:n{index}'
                    events.append(Event(nid,pid,label,1,voice,staff,onset,duration,midi,'start' in types,'stop' in types,(nid,)))
                    extent=max(extent,onset+duration)
            if extent<=0:raise ValueError('empty measure needs explicit timed rests')
            if measure.get('implicit')!='yes' and extent!=beats*unit:
                raise ValueError(f'measure {label} duration differs from meter; explicitly mark a reviewed partial bar')
            if label in spans and spans[label]!=extent:raise ValueError(f'parts disagree on duration of measure {label}')
            if label in units and units[label]!=unit:raise ValueError('polymeter needs an explicit adapter')
            spans[label]=extent;units[label]=unit
        if order is not None and order!=labels:raise ValueError('parts have different printed measure traversal')
        order=labels
    if not parts or not events:raise ValueError('score contains no timed notation')
    if len({e.event_id for e in events})!=len(events):raise ValueError('duplicate notation IDs')
    canonical={'events':[e.record() for e in events],'spans':{k:str(v) for k,v in spans.items()},'units':{k:str(v) for k,v in units.items()}}
    revision=hashlib.sha256(json.dumps(canonical,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return SymbolicScore(tuple(parts),tuple(order),spans,units,tuple(events),revision,tuple(sorted(warnings)))


def traverse(score: SymbolicScore, passage: Passage) -> tuple[Event,...]:
    if set(passage.part_ids)-set(score.parts):raise ValueError('unknown passage part')
    result=[];offset=F(0)
    for visit in passage.visits:
        if visit.label not in score.spans:raise ValueError('unknown passage measure')
        start=(F(visit.start_beat)-1)*score.beat_units[visit.label]
        end=score.spans[visit.label] if visit.end_beat is None else (F(visit.end_beat)-1)*score.beat_units[visit.label]
        if not 0<=start<end<=score.spans[visit.label]:raise ValueError('passage beat outside measure')
        for event in score.events:
            if event.measure!=visit.label or event.part not in passage.part_ids:continue
            if event.onset<end and event.onset+event.duration>start:
                if event.onset<start or event.onset+event.duration>end:
                    raise ValueError('passage cuts a note: include attack/release context instead')
                result.append(replace(event,event_id=f'{event.event_id}@{visit.occurrence}',occurrence=visit.occurrence,onset=offset+event.onset-start))
        offset+=end-start
    result=sorted(result,key=lambda e:(e.onset,passage.part_ids.index(e.part),e.voice,e.event_id))
    playback_notes(tuple(result)) # also checks tied-entry/exit traversal
    return tuple(result)


def playback_notes(events: tuple[Event,...]) -> tuple[Event,...]:
    attacks=[];active={}
    for event in events:
        if event.midi is None:continue
        key=(event.part,event.voice,event.staff,event.midi)
        if event.tie_stop:
            if key not in active:
                candidates=[k for k,idx in active.items() if k[0]==event.part and k[3]==event.midi and attacks[idx].onset+attacks[idx].duration==event.onset]
                if len(candidates)>1:raise ValueError('ambiguous cross-voice tie endpoint')
                if not candidates:raise ValueError('tie continuation lacks preceding attack; include preroll')
                # Explicit equal-pitch tie endpoints may migrate to another
                # notated voice/staff. Never infer among ambiguous unisons.
                old_key=candidates[0];active[key]=active.pop(old_key)
            idx=active[key];prior=attacks[idx]
            if prior.onset+prior.duration!=event.onset:raise ValueError('tie traversal is not contiguous')
            attacks[idx]=replace(prior,duration=prior.duration+event.duration,notation_ids=prior.notation_ids+event.notation_ids,tie_start=event.tie_start)
            if not event.tie_start:del active[key]
        else:
            if key in active:raise ValueError('unresolved tie before new attack')
            attacks.append(event)
            if event.tie_start:active[key]=len(attacks)-1
    if active:raise ValueError('open tie at passage exit: include resolution context')
    return tuple(attacks)


def transform(events: tuple[Event,...], *, kind: str, part_ids: tuple[str,...]=()) -> tuple[Event,...]:
    """Explicit pedagogical reductions, never automatic harmonic truth.

    Lowest/highest chooses among simultaneous attacks. It is NOT a claimed
    contrapuntal bass or melody extractor for arbitrary polyphonic performances.
    Select a verified voice/part first. All results remain symbolic derivatives.
    """
    if kind=='part':
        if not part_ids or set(part_ids)-{e.part for e in events}:raise ValueError('unknown selected part')
        return tuple(e for e in events if e.part in part_ids)
    if kind not in {'lowest','highest'}:raise ValueError('unsupported reduction; provide explicit reviewed symbolic rewrite')
    groups={}
    for e in events:
        if e.midi is not None:groups.setdefault((e.onset,e.part,e.voice),[]).append(e)
    return tuple(sorted(((min if kind=='lowest' else max)(group,key=lambda e:e.midi) for group in groups.values()),key=lambda e:e.onset))


def controlled_diff(a: tuple[Event,...], b: tuple[Event,...], *, allowed_fields: tuple[str,...]) -> tuple[dict,...]:
    fields=('part','measure','voice','staff','onset','duration','midi','tie_start','tie_stop')
    if set(allowed_fields)-set(fields):raise ValueError('unknown controlled comparison field')
    if len(a)!=len(b):raise ValueError('comparison changes event count; supply explicit structural comparison instead')
    changes=[]
    for i,(left,right) in enumerate(zip(a,b)):
        for key in fields:
            if getattr(left,key)!=getattr(right,key):
                if key not in allowed_fields:raise ValueError(f'unapproved change in {key}')
                changes.append({'index':i,'field':key,'before':str(getattr(left,key)),'after':str(getattr(right,key))})
    return tuple(changes)
