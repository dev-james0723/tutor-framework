"""Original open-response exercises under explicit, non-official practice rubrics.

These extend the existing five-artifact practice contract. They are NOT a
verified ABRSM Grades 6–8 exam blueprint, even when requested in that context.
"""
from __future__ import annotations

import copy
import hashlib
import json
import random
from pathlib import Path
from .context import LearnerContext
from .operations import scale, evaluate
from .practice import DISCLAIMER
from .mini_exam import _score

TOPICS={'voice_leading','composition','form_comparison'}
ARTIFACTS={'student_paper','answer_key','worked_solutions','marking_rubric','competency_map'}


def build_open_practice(*, topic, seed, context=None):
    context=context or LearnerContext()
    if topic not in TOPICS:return {'state':'unsupported','topic':topic,'reason':'No source-reviewed original template for this domain.'}
    if type(seed) is not int:raise ValueError('An integer seed is required')
    rng=random.Random(seed);key=rng.choice(('C','D','F','G'))
    notes=scale(key+'3','major')['notes']
    identity=hashlib.sha256(f'open-practice-v1:{topic}:{seed}'.encode()).hexdigest()[:20]
    paper_id='original-open:'+identity;question_id=paper_id+':q1'
    shared={'paper_id':paper_id,'question_id':question_id,'claim_id':question_id+':claim',
            'passage_id':question_id+':passage','concept_id':'music:'+topic,'version':'1.0','disclaimer':DISCLAIMER,'no_save':context.no_save}
    if topic=='voice_leading':
        before={'bass':notes[0],'soprano':notes[4]};after={'bass':notes[1],'soprano':notes[5]}
        given={'before':before,'after':after,'style':'common_practice_two_voice_exercise'}
        prompt='Describe the motion between these two sonorities. For a common-practice exercise, propose one change to the upper voice that removes the parallel perfect interval while keeping the bass. Then explain why this exercise rule is not a universal ban in jazz/pop.'
        alternate={'bass':notes[1],'soprano':notes[3]}
        check=evaluate({'operation':'voice_leading','before':before,'after':after,'style':'common_practice'},context)
        fixed=evaluate({'operation':'voice_leading','before':before,'after':alternate,'style':'common_practice'},context)
        assert check['data']['parallels'] and not fixed['data']['parallels']
        model=f"The two voices move upwards in parallel perfect fifths. One alternative keeps bass {notes[1]} and moves the upper voice from {notes[4]} to {notes[3]}, giving contrary motion. This addresses the observed parallel, not every counterpoint or dissonance rule. Jazz/pop judgment needs its own voicing and stylistic context."
        criteria=[('evidence','Read both named voices and written pitches accurately.'),('motion','Identify similar motion and the specific perfect interval.'),('revision','Give a concrete alternative with the prescribed bass and demonstrate removal of the parallel.'),('scope','Distinguish common-practice exercise expectations from jazz/pop usage.'),('limits','Avoid claiming complete contrapuntal correctness from a single motion check.')]
    elif topic=='composition':
        upper=scale(key+'4','major')['notes'];pattern=rng.choice(((0,2,1,4),(0,1,3,2),(2,1,4,3)))
        opening=[upper[i] for i in pattern]
        given={'key':key+' major','opening_quarter_notes':opening,'meter':'4/4',
               'musicxml':_score(opening,key),'task_length':'add two complete bars'}
        prompt='Continue the original one-bar idea with two complete bars in 4/4. Keep a recognizable motivic link, show a deliberate contour change, and explain one performance choice. Supply exact notes and durations. Harmonic closure must be justified rather than inferred from the final melody note alone.'
        continuation=[upper[3],upper[2],upper[1],upper[2],upper[4],upper[2],upper[1],upper[0]]
        model='One possible continuation uses quarter notes '+', '.join(continuation)+'. The two four-note groups fill two 4/4 bars. This example returns to the tonic pitch, but no authentic cadence is claimed without a harmonic realization. Other original responses can satisfy the rubric.'
        criteria=[('duration','Complete both bars with valid durations and explicit notation.'),('motive','Retain an identifiable feature of the opening without mere duplication.'),('contour','Create an intentional contour or register contrast.'),('explanation','Explain the musical choices and one performance implication.'),('evidence','Distinguish melodic arrival from harmonically verified cadence.')]
    else:
        given={'abstract_design':['four-bar basic idea','four-bar varied repetition','fragmentation and harmonic acceleration','proposed cadential unit'],
               'missing_evidence':['complete score','exact cadence','tonal plan'],
               'comparison':'Caplin formal functions versus descriptive phrase grouping'}
        prompt='Discuss what this abstract design suggests under Caplin and under a descriptive phrase-grouping approach. Identify what cannot be concluded without the score, and specify the evidence needed to confirm or reject each reading. Do not label a sentence or period solely from bar counts.'
        model='Repetition followed by fragmentation can motivate a sentence-like hypothesis, but a Caplin reading needs harmonic and cadential evidence for presentation and continuation functions. Descriptive grouping may report repeated and contrasting units without establishing those functions. Neither an eight-bar pattern nor the word cadence proves a formal category.'
        criteria=[('framework','State both analytical frameworks explicitly.'),('hypothesis','Offer a qualified formal hypothesis rather than a bar-count formula.'),('cadence','Explain what harmonic and cadential evidence is missing.'),('comparison','Separate descriptive grouping from functional interpretation.'),('falsifiability','Name evidence that could change or defeat the proposed reading.')]
    rubric=[{'criterion_id':name,'max_marks':2,'description':description,
             'levels':{'0':'not demonstrated','1':'partly supported','2':'clearly supported by the response and evidence'}} for name,description in criteria]
    student={**shared,'topic':topic,'response_type':'open_response','prompt':prompt,'given':given,
             'instructions':'This is original formative practice. Several responses may be valid. The separate rubric, not literal answer matching, governs feedback.'}
    bundle={'student_paper':student,
            'answer_key':{**shared,'origin':'system_created_example_not_official','model_response':model,'multiple_valid_answers':True},
            'worked_solutions':{**shared,'steps':[c[1] for c in criteria],'model_response':model,'origin':'system_created_example_not_official'},
            'marking_rubric':{**shared,'criteria':rubric,'maximum_marks':sum(c['max_marks'] for c in rubric),
                              'practice_feedback_only':True,'official_prediction':False,'marking_authority':'original_pedagogical_rubric_not_exam_board'},
            'competency_map':{**shared,'competencies':[name for name,_ in criteria],'topic':topic,
                              'difficulty':'estimated','teacher_calibrated':False,'full_exam_blueprint_verified':False,
                              'requested_context':dict(context.curriculum_context),
                              'curriculum_alignment':'review_required' if context.curriculum_context else 'not_claimed',
                              'grade_equivalences':[],'generation_origin':'original_template_and_new_symbolic_material_no_source_paper_mutation'}}
    validate_open_practice(bundle)
    return bundle


def validate_open_practice(bundle):
    if not isinstance(bundle,dict) or set(bundle)!=ARTIFACTS:raise ValueError('Five separate practice artifacts required')
    student=bundle['student_paper']
    if any(type(part.get('no_save',False)) is not bool for part in bundle.values()):raise ValueError('No-save metadata must be boolean')
    for key in ('paper_id','question_id','claim_id','passage_id','concept_id'):
        if any(part.get(key)!=student.get(key) for part in bundle.values()):raise ValueError('Cross-artifact identity mismatch')
    if student.get('response_type')!='open_response' or 'options' in student:raise ValueError('Open response must not inherit MCQ assumptions')
    if any(key in student for key in ('model_response','answer_key','correct_option_id','worked_solution')):
        raise ValueError('Student artifact contains an answer field')
    criteria=bundle['marking_rubric']['criteria']
    if len({c['criterion_id'] for c in criteria})!=len(criteria) or not criteria:raise ValueError('Rubric criteria need unique identities')
    if any(type(c['max_marks']) is not int or c['max_marks']<=0 for c in criteria):raise ValueError('Invalid rubric maximum')
    if sum(c['max_marks'] for c in criteria)!=bundle['marking_rubric']['maximum_marks']:raise ValueError('Rubric marks disagree')
    if bundle['competency_map']['full_exam_blueprint_verified'] is not False:raise ValueError('No verified official blueprint exists for these templates')
    return {'state':'passed','criteria':len(criteria),'expert_calibration':'review_required'}


def assess_open_response(bundle, learner_response, *, criterion_awards=None, reviewer_id=None):
    validate_open_practice(bundle)
    if not isinstance(learner_response,str) or not learner_response.strip() or len(learner_response)>20000:
        raise ValueError('A bounded learner response is required')
    criteria=bundle['marking_rubric']['criteria']
    result={'question_id':bundle['student_paper']['question_id'],'state':'review_required','score':None,
            'learner_answer':learner_response,'learner_answer_origin':'learner_answer',
            'review_checklist':copy.deepcopy(criteria),'practice_feedback_only':True,'official_prediction':False,'persisted':False}
    if criterion_awards is None:return result
    if not isinstance(reviewer_id,str) or not reviewer_id.strip() or len(reviewer_id)>200:
        raise ValueError('Reviewer attribution is required for criterion awards')
    if not isinstance(criterion_awards,dict) or set(criterion_awards)!={c['criterion_id'] for c in criteria}:
        raise ValueError('All rubric criteria require explicit awards; missing values cannot be inferred')
    for criterion in criteria:
        value=criterion_awards[criterion['criterion_id']]
        if type(value) is not int or not 0<=value<=criterion['max_marks']:raise ValueError('Rubric award outside its permitted integer range')
    result.update(state='reviewer_recorded_practice_feedback',score=sum(criterion_awards.values()),
                  maximum_marks=bundle['marking_rubric']['maximum_marks'],score_origin='caller_supplied_reviewer_result',
                  reviewer_id=reviewer_id,criterion_awards=copy.deepcopy(criterion_awards))
    return result


def export_open_practice(bundle,directory,*,no_save=False,student_only=False):
    if type(no_save) is not bool or no_save:raise ValueError('No-save forbids practice export')
    if isinstance(bundle,dict) and any(isinstance(part,dict) and part.get('no_save') is True for part in bundle.values()):
        raise ValueError('No-save carried by the original bundle forbids later export')
    if type(student_only) is not bool:raise ValueError('student_only must be a boolean')
    validate_open_practice(bundle)
    directory=Path(directory).expanduser().resolve()
    if directory.exists():raise ValueError('A new export directory is required')
    (directory/'student').mkdir(parents=True)
    if not student_only:(directory/'teacher').mkdir()
    for name,artifact in bundle.items():
        if student_only and name!='student_paper':continue
        path=directory/('student/paper.json' if name=='student_paper' else 'teacher/'+name+'.json')
        path.write_text(json.dumps(artifact,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    student=bundle['student_paper']
    lines=['# Original open-response practice','',DISCLAIMER,'',student['prompt'],'',student['instructions'],'','## Given material','',json.dumps({k:v for k,v in student['given'].items() if k!='musicxml'},ensure_ascii=False,indent=2)]
    (directory/'student/paper.md').write_text('\n'.join(lines),encoding='utf-8')
    if student['given'].get('musicxml'):
        (directory/'student/original.musicxml').write_text(student['given']['musicxml'],encoding='utf-8')
    return {'state':'original_open_practice_for_review','directory':str(directory),
            'artifact_hashes':{str(p.relative_to(directory)):hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.rglob('*') if p.is_file()},
            'official_prediction':False}
