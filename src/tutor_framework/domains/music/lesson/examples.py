"""Music Example Lab: explicit symbolic derivatives, not recognition guesses."""
from __future__ import annotations
import copy
import hashlib
import xml.etree.ElementTree as ET
from dataclasses import replace
from fractions import Fraction as F
from .models import ExampleSpec,Passage,MeasureVisit
from .symbolic import Event,parse_score,traverse,controlled_diff,playback_notes


def _pitch(element: ET.Element,midi: int) -> None:
    pitch=element.find('pitch')
    if pitch is None:raise ValueError('controlled pitch edit addresses a rest')
    names=[('C',0),('C',1),('D',0),('E',-1),('E',0),('F',0),('F',1),('G',0),('A',-1),('A',0),('B',-1),('B',0)]
    step,alter=names[midi%12];pitch.clear()
    ET.SubElement(pitch,'step').text=step
    if alter:ET.SubElement(pitch,'alter').text=str(alter)
    ET.SubElement(pitch,'octave').text=str(midi//12-1)
    for old in list(element.findall('accidental')):element.remove(old)
    if alter:ET.SubElement(element,'accidental').text='sharp' if alter==1 else 'flat'


def prepare_example(payload: str | bytes,spec: ExampleSpec,passage: Passage) -> tuple[bytes,dict]:
    source=parse_score(payload);source_events=traverse(source,passage)
    if any(v.start_beat!='1' or v.end_beat is not None for v in passage.visits):
        raise ValueError('engraving partial-beat extraction needs an explicit MusicXML rewrite; traversal alone is not engraving')
    selected=spec.part_ids or passage.part_ids
    if set(selected)-set(passage.part_ids):raise ValueError('example part outside verified passage')
    if spec.transformation in {'melody','bass'}:
        for part in selected:
            if len({e.voice for e in source_events if e.part==part and e.midi is not None})>1:
                raise ValueError('focused line has multiple voices; supply an explicit reviewed single-line rewrite')
    root=ET.fromstring(payload)
    for e in root.iter():e.tag=e.tag.rsplit('}',1)[-1]
    for tag in ('work','movement-title','identification','credit','defaults'):
        for e in list(root.findall(tag)):root.remove(e)
    by_id={e.event_id:e for e in source.events};changed=0;mapping=[];expanded=len({v.label for v in passage.visits})!=len(passage.visits)
    for part in list(root.findall('part')):
        pid=part.get('id')
        if pid not in selected:root.remove(part);continue
        measures={m.get('number'):m for m in part.findall('measure')}
        inherited={};attrs_before={}
        for label,m in measures.items():
            for attrs in m.findall('attributes'):
                for child in attrs:inherited[(child.tag,child.get('number',''))]=copy.deepcopy(child)
            attrs_before[label]=copy.deepcopy(inherited)
        for m in list(part.findall('measure')):part.remove(m)
        for visit_index,visit in enumerate(passage.visits):
            original=measures[visit.label];m=copy.deepcopy(original)
            playback_label=str(visit_index+1) if expanded else visit.label
            m.set('number',playback_label)
            for attrs in list(m.findall('attributes')):m.remove(attrs)
            attrs=ET.Element('attributes')
            for item in attrs_before[visit.label].values():attrs.append(copy.deepcopy(item))
            m.insert(0,attrs)
            for print_node in list(m.findall('print')):m.remove(print_node)
            for barline in m.findall('barline'):
                for child in list(barline):
                    if child.tag in {'repeat','ending'}:barline.remove(child)
            notes=m.findall('note')
            for i,n in enumerate(notes,1):
                old_id=n.get('id') or f'{pid}:{visit.label}:n{i}'
                if spec.transformation=='rewrite' and old_id==spec.changed_note_id:
                    ev=by_id[old_id]
                    if ev.tie_start or ev.tie_stop:raise ValueError('pitch change would break tie identity; provide a complete tied rewrite')
                    tr=attrs.find('transpose')
                    if tr is not None:raise ValueError('pitch rewriting a transposing instrument needs written-pitch mapping')
                    _pitch(n,spec.changed_midi);changed+=1
                n.set('id','n'+hashlib.sha256(f'{old_id}@{visit.occurrence}'.encode()).hexdigest()[:20])
                n.set('data-source-id',old_id) # removed after controlled group selection below
            if spec.transformation in {'bass','lowest','highest'}:
                groups=[]
                for n in list(m.findall('note')):
                    if n.find('chord') is not None:
                        if not groups:raise ValueError('orphan chord')
                        groups[-1].append(n)
                    else:groups.append([n])
                for group in groups:
                    pitched=[n for n in group if n.find('pitch') is not None]
                    if len(pitched)<2:continue
                    if len({n.findtext('duration') for n in pitched})!=1:raise ValueError('unequal-duration chord reduction needs explicit rewrite')
                    chooser=max if spec.transformation=='highest' else min
                    keep=chooser(pitched,key=lambda n:by_id[n.get('data-source-id')].midi)
                    for n in group:
                        if n is not keep:m.remove(n)
                    chord_node=keep.find('chord')
                    if chord_node is not None:keep.remove(chord_node)
            for n in m.findall('note'):n.attrib.pop('data-source-id',None)
            for direction in list(m.findall('direction')):
                for sound in direction.findall('sound'):sound.attrib.pop('tempo',None)
                for dt in direction.findall('direction-type'):
                    for mt in list(dt.findall('metronome')):dt.remove(mt)
            if visit_index==0:
                direction=ET.Element('direction');dt=ET.SubElement(direction,'direction-type');metro=ET.SubElement(dt,'metronome')
                ET.SubElement(metro,'beat-unit').text='quarter';ET.SubElement(metro,'per-minute').text=str(float(F(spec.bpm)))
                ET.SubElement(direction,'sound',tempo=str(float(F(spec.bpm))))
                m.insert(1,direction)
            part.append(m)
            if pid==selected[0]:mapping.append({'playback_label':playback_label,'source_label':visit.label,'source_occurrence':visit.occurrence,'edition_id':passage.edition_id})
    part_list=root.find('part-list')
    if part_list is not None:
        for child in list(part_list):
            if child.tag=='score-part' and child.get('id') not in selected:part_list.remove(child)
    if spec.transformation=='rewrite' and changed!=1:raise ValueError('controlled rewrite note missing or repeated; exactly one change required')
    xml=ET.tostring(root,encoding='utf-8',xml_declaration=True)
    compiled=parse_score(xml)
    compiled_passage=Passage(spec.passage_id,passage.edition_id,tuple(MeasureVisit(m['playback_label'],1) for m in mapping),tuple(selected),passage.real_measure_mapping)
    rendered_events=traverse(compiled,compiled_passage)
    changes=[]
    if spec.transformation=='rewrite':
        baseline=tuple(e for e in source_events if e.part in selected)
        changes=list(controlled_diff(baseline,rendered_events,allowed_fields=('midi',)))
    return xml,{'symbolic_revision':compiled.revision,'source_revision':source.revision,'bpm':spec.bpm,'transformation':spec.transformation,'traversal':mapping,'controlled_changes':changes,'source_warnings':source.warnings,'events':[e.record() for e in rendered_events],'playback_attacks':[e.record() for e in playback_notes(rendered_events)],'precision':'symbolic timestamps; audio alignment must be independently measured','status':'pedagogical_derivative' if spec.transformation!='identity' else 'source_symbolic_derivative'}


def extract_motive(events: tuple[Event,...],start: F,end: F) -> tuple[Event,...]:
    if not 0<=start<end:raise ValueError('invalid motive range')
    selected=tuple(e for e in events if e.onset<end and e.onset+e.duration>start)
    if not selected or any(e.onset<start or e.onset+e.duration>end for e in selected):raise ValueError('motive cuts a sustained note or is empty')
    result=tuple(replace(e,onset=e.onset-start) for e in selected);playback_notes(result);return result


def transpose_example(events: tuple[Event,...],semitones: int) -> tuple[Event,...]:
    if type(semitones) is not int or not -48<=semitones<=48:raise ValueError('invalid pedagogical transposition')
    if any(e.midi is not None and not 0<=e.midi+semitones<=127 for e in events):raise ValueError('transposition exceeds MIDI range')
    return tuple(replace(e,midi=None if e.midi is None else e.midi+semitones) for e in events)


def repeat_fragment(events: tuple[Event,...],start: F,end: F,count: int) -> tuple[Event,...]:
    if type(count) is not int or not 1<=count<=16:raise ValueError('bounded positive fragment repetitions required')
    fragment=extract_motive(events,start,end)
    return tuple(replace(e,event_id=f'{e.event_id}:rewrite-repeat-{i+1}',onset=e.onset+i*(end-start),occurrence=i+1) for i in range(count) for e in fragment)


def harmonic_reduction(events: tuple[Event,...],grid: tuple[F,...]) -> tuple[dict,...]:
    if len(grid)<2 or any(a>=b for a,b in zip(grid,grid[1:])) or grid[0]<0:raise ValueError('explicit increasing harmonic sampling grid required')
    notes=playback_notes(events)
    return tuple({'onset':a,'duration':b-a,'pitches':tuple(sorted({e.midi for e in notes if e.onset<=a<e.onset+e.duration})),'status':'pedagogical_sampling_not_functional_harmony','source_ids':tuple(e.event_id for e in notes if e.onset<=a<e.onset+e.duration)} for a,b in zip(grid,grid[1:]))


def _template_xml(bars: list[tuple[list[tuple[int,int]],tuple[int,...]]]) -> str:
    root=ET.Element('score-partwise',version='4.0');pl=ET.SubElement(root,'part-list')
    for pid in ('RH','LH'):
        sp=ET.SubElement(pl,'score-part',id=pid);ET.SubElement(sp,'part-name').text='Pedagogical piano '+pid
        part=ET.SubElement(root,'part',id=pid)
        for i,(melody,bass) in enumerate(bars,1):
            m=ET.SubElement(part,'measure',number=str(i));attrs=ET.SubElement(m,'attributes');ET.SubElement(attrs,'divisions').text='1'
            ts=ET.SubElement(attrs,'time');ET.SubElement(ts,'beats').text='4';ET.SubElement(ts,'beat-type').text='4'
            clef=ET.SubElement(attrs,'clef');ET.SubElement(clef,'sign').text='G' if pid=='RH' else 'F';ET.SubElement(clef,'line').text='2' if pid=='RH' else '4'
            entries=melody if pid=='RH' else [(p,4) for p in bass]
            if sum(d for _,d in melody)!=4:raise ValueError('template bar is not complete')
            for j,(pitch,duration) in enumerate(entries):
                n=ET.SubElement(m,'note')
                if pid=='LH' and j:ET.SubElement(n,'chord')
                ET.SubElement(n,'pitch');_pitch(n,pitch);ET.SubElement(n,'duration').text=str(duration);ET.SubElement(n,'voice').text='1'
                ET.SubElement(n,'type').text={1:'quarter',2:'half',4:'whole'}[duration]
    return ET.tostring(root,encoding='unicode')


def teaching_catalog() -> dict[str,dict]:
    """Actual editable, original notated prototypes with explicit review status.

    These are pedagogical models, not quotations or algorithmically certified
    Caplin analyses. An instructor can replace any bar with a reviewed model.
    """
    I=(48,52,55);IV=(41,45,48);V=(43,47,50)
    bi=[([(72,1),(76,1),(79,2)],I), ([(79,1),(77,1),(76,1),(74,1)],V)]
    contrast=([(69,1),(72,1),(77,2)],IV);hc=([(71,4)],V);cad=[([(74,1),(71,1),(74,2)],V), ([(72,4)],I)]
    cont=[([(72,1),(76,1),(79,2)],I),contrast]+cad
    sentence=bi+bi+cont;period=bi+[contrast,hc]+bi+cad;hybrid=bi+[contrast,hc]+cont
    def moved(bars,shift):return [([(p+shift,d) for p,d in melody],tuple(p+shift for p in bass)) for melody,bass in bars]
    plans={'sentence':sentence,'period':period,'hybrid':hybrid,'cadence':[contrast]+cad,'non_cadence':[hc,hc], 'fragmentation':cont,'tonal_return':bi+moved([contrast,hc],7)+[contrast]+cad,'thematic_return':bi+moved([contrast,hc]+bi,7),'expansion':sentence[:5]+[sentence[5]]+sentence[5:],'extension':sentence+[sentence[-1]]}
    purposes={'sentence':'Compare a repeated two-bar basic idea with the following fragmentation and cadence.','period':'Compare a weaker antecedent close with a stronger consequent close.','hybrid':'Compare an antecedent opening with a continuation ending.','cadence':'Track predominant, dominant and tonic closure.','non_cadence':'A reiterated dominant is not automatically a new cadence.','fragmentation':'Compare the two-bar idea with one-bar fragments.','tonal_return':'Tonic can return without the opening thematic idea.','thematic_return':'The opening idea can return while remaining in another key.','expansion':'An inserted internal unit lengthens the route to the first final cadence.','extension':'A post-cadential addition follows an already completed final cadence.'}
    return {name:{'musicxml':_template_xml(bars),'status':'pedagogical_model_requires_analytical_review','purpose':purposes[name],'claim_kind':'tutor_analytical_judgment'} for name,bars in plans.items()}
