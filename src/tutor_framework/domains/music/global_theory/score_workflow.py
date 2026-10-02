"""Source-bound score observations using the existing validated MusicXML reader.

A symbolic observation is not OMR verification and a proposed formal function is
not automatically established by local note patterns. This module writes nothing.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from fractions import Fraction
from .context import LearnerContext
from .curriculum import curriculum
from .operations import interval
from tutor_framework.domains.music.lesson.symbolic import parse_score


def _identity(value, field):
    if not isinstance(value,str) or not value.strip() or len(value)>240:
        raise ValueError(f'{field} must be a bounded explicit identity')
    return value


def _melodic_observations(events):
    voices={};observations=[];warnings=[]
    for event in events:
        key=(event['part'],event['voice'],event['staff'])
        voices.setdefault(key,{}).setdefault(Fraction(event['absolute_onset']),[]).append(event)
    for voice,groups in voices.items():
        prior=None;prior_end=None;open_tie=False;attack_claims=[]
        for onset,group in sorted(groups.items()):
            if len(group)!=1:
                warnings.append({'events':[e['event_id'] for e in group],'reason':'Simultaneous chord members are not an automatically selected melody.'})
                prior=None;prior_end=None;open_tie=False;attack_claims=[]
                continue
            current=group[0]
            if current['written_pitch'] is None:
                prior=None;prior_end=None;open_tie=False;attack_claims=[]
                continue
            if current['tie_stop']:
                if prior is not None and open_tie and current['written_pitch']==prior['written_pitch'] and onset==prior_end:
                    prior_end=onset+Fraction(current['duration'])
                    open_tie=current['tie_start'];attack_claims.append(current['claim_id'])
                else:
                    warnings.append({'events':[current['event_id']],'reason':'Tie continuation lacks a unique contiguous attack context.'})
                    prior=None;prior_end=None;open_tie=False;attack_claims=[]
                continue
            if prior is not None:
                if open_tie or onset<prior_end:
                    warnings.append({'events':[prior['event_id'],current['event_id']],'reason':'Unresolved tie or overlapping attacks prevent a monophonic interval claim.'})
                else:
                    try:
                        observed=interval(prior['written_pitch'],current['written_pitch'])
                    except ValueError as error:
                        warnings.append({'events':[prior['event_id'],current['event_id']],
                                         'reason':'Optional interval operation is outside its supported pitch scope: '+str(error)})
                    else:
                        observations.append({'from_event':prior['event_id'],'to_event':current['event_id'],
                                             'observation':observed,'source_id':current['source_id'],
                                             'claim_ids':attack_claims+[current['claim_id']]})
            prior=current;prior_end=onset+Fraction(current['duration']);open_tie=current['tie_start']
            attack_claims=[current['claim_id']]
        if open_tie:
            warnings.append({'events':[prior['event_id']] if prior else [],'reason':'Open tie at source exit requires additional source context.'})
    return observations,warnings


def analyze_score(payload, *, source_id, context=None, formal_annotations=()):
    """Return exactly anchored symbolic observations, never inferred unread notation."""
    _identity(source_id,'source_id')
    context=context or LearnerContext()
    raw=payload.encode() if isinstance(payload,str) else payload
    if not isinstance(raw,bytes):raise ValueError('MusicXML text or PDF bytes required')
    if raw.startswith(b'%PDF-'):
        return {'state':'review_required','source_id':source_id,'event_count':0,'events':[],
                'required_pipeline':'MinerU + existing score/OMR review', 'omr_verified':False,
                'reason':'PDF notation must first have source crops, structured parsing and reviewed notation recognition.',
                'persisted':False}
    score=parse_score(raw)
    # parse_score has already validated and rejected internal/external entities.
    normalized=re.sub(rb'<!DOCTYPE\s+score-partwise\s+PUBLIC\s+"[^"<>\[\]]*"\s+"[^"<>\[\]]*"\s*>',b'',raw)
    root=ET.fromstring(normalized)
    for element in root.iter():element.tag=element.tag.rsplit('}',1)[-1]
    written={}
    for part in root.findall('part'):
        for measure in part.findall('measure'):
            for index,note in enumerate(measure.findall('note'),1):
                note_id=note.get('id') or f"{part.get('id')}:{measure.get('number')}:n{index}"
                pitch_node=note.find('pitch')
                if pitch_node is None:written[note_id]=None;continue
                alteration=Fraction(pitch_node.findtext('alter','0'))
                if alteration.denominator!=1:raise ValueError('Unsupported microtonal written pitch')
                alter=int(alteration)
                written[note_id]=pitch_node.findtext('step')+('#'*alter if alter>0 else 'b'*(-alter))+pitch_node.findtext('octave')
    offsets={};offset=Fraction(0)
    for label in score.labels:offsets[label]=offset;offset+=score.spans[label]
    notation_revision=hashlib.sha256(raw).hexdigest()
    events=[];claims=[]
    for event in score.events:
        claim='score:'+hashlib.sha256(f'{source_id}:{notation_revision}:{score.revision}:{event.event_id}'.encode()).hexdigest()[:24]
        data=event.record()
        data.update(absolute_onset=str(offsets[event.measure]+event.onset),written_pitch=written[event.event_id],
                    notation_ids=list(event.notation_ids),claim_id=claim,source_id=source_id)
        events.append(data);claims.append(claim)
    melodic,interval_warnings=_melodic_observations(events)
    if not isinstance(formal_annotations,(tuple,list)) or len(formal_annotations)>100:
        raise ValueError('At most 100 explicit formal annotations are supported')
    proposals=[]
    for annotation in formal_annotations:
        if not isinstance(annotation,dict):raise ValueError('Formal annotation must be an object')
        if set(annotation)-{'start_measure','end_measure','label','framework','source_claim_ids'}:
            raise ValueError('Unknown formal annotation field')
        start,end=annotation.get('start_measure'),annotation.get('end_measure')
        if start not in score.labels or end not in score.labels or score.labels.index(start)>score.labels.index(end):
            raise ValueError('Formal passage does not match the source measure traversal')
        _identity(annotation.get('label'),'formal label');_identity(annotation.get('framework'),'analysis framework')
        proposal=copy.deepcopy(annotation)
        proposal.update(origin='caller_analytical_interpretation',state='review_required',source_id=source_id,
                        context_framework_matches=context.analysis_framework in {'unknown',annotation['framework']})
        proposals.append(proposal)
    summary=(f'已讀取 {len(score.parts)} 個聲部、{len(score.labels)} 小節及 {len(events)} 個記譜事件。音高與時值來自明確 MusicXML；形式功能仍須按框架及完整樂句判斷。'
             if context.response_language=='zh-Hant' else
             f'Read {len(score.parts)} parts, {len(score.labels)} measures and {len(events)} notated events from explicit MusicXML. Formal function still needs a selected framework and phrase-level evidence.')
    return {'state':'symbolic_observations_available','source_id':source_id,'source_sha256':hashlib.sha256(raw).hexdigest(),
            'symbolic_revision':score.revision,'notation_revision':notation_revision,'event_count':len(events),'events':events,'claim_ids':claims,
            'measure_order':list(score.labels),'duration_quarters':str(offset),'melodic_intervals':melodic,
            'formal_analysis':{'state':'review_required','framework':context.analysis_framework,'annotations':proposals},
            'melodic_interval_warnings':interval_warnings,'summary':summary,'warnings':list(score.warnings),'omr_verified':False,'persisted':False,
            'interpretation_limits':['no automatic Caplin sentence/period classification','no inferred original score page/crop','written and sounding pitches remain separate']}


def reconcile_claims(records):
    """Retain competing evidence rather than resolving lecture/score conflicts by fiat."""
    if not isinstance(records,list) or len(records)>10000:raise ValueError('Bounded claim list required')
    groups={};seen=set()
    for record in records:
        if not isinstance(record,dict):raise ValueError('Claim record must be an object')
        for field in ('claim_id','source_id','subject','kind','revision'):_identity(record.get(field),field)
        if record['claim_id'] in seen:raise ValueError('Duplicate claim identity')
        if 'value' not in record:raise ValueError('Missing claim value')
        json.dumps(record,allow_nan=False)
        seen.add(record['claim_id']);groups.setdefault(record['subject'],[]).append(copy.deepcopy(record))
    conflicts=[]
    for subject,claims in groups.items():
        values={json.dumps(c['value'],sort_keys=True,ensure_ascii=False) for c in claims}
        if len(values)>1:
            conflicts.append({'subject':subject,'claim_ids':[c['claim_id'] for c in claims],
                              'claims':claims,'resolution':'review_required_no_automatic_source_override'})
    return {'state':'review_required' if conflicts else 'no_explicit_conflict_detected','conflicts':conflicts,
            'records':copy.deepcopy(records),'agreement_is_not_truth_verification':True,'persisted':False}


def compare_curricula(source_id, target_id, *, source_version=None, target_version=None):
    source=curriculum(source_id,version=source_version);target=curriculum(target_id,version=target_version)
    if source.get('state')=='unsupported' or target.get('state')=='unsupported':
        return {'state':'unsupported','source':source_id,'target':target_id,'grade_equivalences':[]}
    a=set(source['explicit_competencies']);b=set(target['explicit_competencies'])
    return {'state':'competency_comparison_requires_version_review','source':source,'target':target,
            'transferable_competencies':sorted(a&b),'target_gaps':sorted(b-a),'source_only_competencies':sorted(a-b),
            'requires_confirmation':sorted(set(source['gaps'])|set(target['gaps'])),
            'grade_equivalences':[],'mapping_kind':'inferred_competency_overlap_not_grade_conversion','persisted':False}
