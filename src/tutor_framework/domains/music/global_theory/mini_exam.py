"""Original source-scoped mini-papers with independent symbolic verification."""
from __future__ import annotations
import difflib
import hashlib
import json
import random
import re
import xml.etree.ElementTree as ET
from fractions import Fraction
from pathlib import Path
from tutor_framework.domains.music.lesson.symbolic import parse_score
from .practice import DISCLAIMER
from .syllabus import syllabus_for

VALUES = {"semibreve": Fraction(4), "minim": Fraction(2), "crotchet": Fraction(1), "quaver": Fraction(1, 2), "semiquaver": Fraction(1, 4)}
US = {"whole note": "semibreve", "half note": "minim", "quarter note": "crotchet", "eighth note": "quaver", "sixteenth note": "semiquaver"}
LETTERS = "CDEFGAB"
NATURAL = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
FIFTHS = {"C": 0, "G": 1, "D": 2, "A": 3, "E": 4, "B": 5, "F#": 6, "F": -1, "Bb": -2, "Eb": -3, "Ab": -4, "Db": -5, "Gb": -6}


def _pitch(name):
    match = re.fullmatch(r"([A-G])([#b]*)([0-8])", name)
    if not match:
        raise ValueError("written pitch and octave required")
    step, accidental, octave = match.groups()
    alter = accidental.count('#') - accidental.count('b')
    return step, alter, int(octave), (int(octave) + 1) * 12 + NATURAL[step] + alter


def _scale(key):
    root = _pitch(key + '4'); start = LETTERS.index(root[0]); result = []
    for i, semitones in enumerate((0, 2, 4, 5, 7, 9, 11)):
        step = LETTERS[(start+i) % 7]; octave = 4 + (start+i)//7
        alter = root[3] + semitones - (12*(octave+1)+NATURAL[step])
        result.append(step + ('#'*alter if alter > 0 else 'b'*(-alter)) + str(octave))
    return result


def _score(names, key, chord=False):
    if len(names) not in (1, 2, 3, 4) or (len(names) == 3 and not chord):
        raise ValueError('bounded complete measure required')
    root=ET.Element('score-partwise',version='4.0'); pl=ET.SubElement(root,'part-list')
    sp=ET.SubElement(pl,'score-part',id='P1'); ET.SubElement(sp,'part-name').text='Original practice'
    part=ET.SubElement(root,'part',id='P1'); measure=ET.SubElement(part,'measure',number='1')
    attr=ET.SubElement(measure,'attributes'); ET.SubElement(attr,'divisions').text='1'
    signature=ET.SubElement(attr,'key'); ET.SubElement(signature,'fifths').text=str(FIFTHS[key])
    meter=ET.SubElement(attr,'time'); ET.SubElement(meter,'beats').text='4'; ET.SubElement(meter,'beat-type').text='4'
    clef=ET.SubElement(attr,'clef'); ET.SubElement(clef,'sign').text='G'; ET.SubElement(clef,'line').text='2'
    duration=4 if chord else 4//len(names)
    for i,name in enumerate(names):
        step,alter,octave,_=_pitch(name); note=ET.SubElement(measure,'note',id=f'n{i+1}')
        if chord and i: ET.SubElement(note,'chord')
        pitch=ET.SubElement(note,'pitch'); ET.SubElement(pitch,'step').text=step
        ET.SubElement(pitch,'alter').text=str(alter); ET.SubElement(pitch,'octave').text=str(octave)
        ET.SubElement(note,'duration').text=str(duration); ET.SubElement(note,'voice').text='1'
        ET.SubElement(note,'type').text={1:'quarter',2:'half',4:'whole'}[duration]
    return ET.tostring(root,encoding='unicode')


def solve_item(question):
    family=question['competency']; g=question['given']
    if family=='duration_ratio': return str(VALUES[g['longer']]/VALUES[g['shorter']])
    if family=='note_name': return US[g['us_name']]
    if family in ('major_scale_degree','tonic_interval_number','tonic_interval_quality'):
        a,b=_pitch(g['tonic']),_pitch(g['target'])
        number=(b[2]-a[2])*7+LETTERS.index(b[0])-LETTERS.index(a[0])+1
        if family!='tonic_interval_quality': return str(number)
        expected={1:0,2:2,3:4,4:5,5:7,6:9,7:11,8:12}
        if expected.get(number)!=b[3]-a[3]: raise ValueError('outside original major-tonic interval template')
        return ('perfect' if number in (1,4,5,8) else 'major')+' '+str(number)
    if family=='tonic_triad': return '-'.join(_scale(g['key'])[i][:-1] for i in (0,2,4))
    if family=='compound_meter': return str(g['numerator']//3)
    if family=='enharmonic_equivalence':
        matches=[n for n in ('Db4','Eb4','Gb4','Ab4','Bb4') if _pitch(n)[3]==_pitch(g['note'])[3]]
        if len(matches)!=1: raise ValueError('no unique flat spelling')
        return matches[0]
    if family=='triad_inversion':
        bass=min(_pitch(n)[3] for n in g['written_notes']); member=(bass-_pitch(g['root'])[3])%12
        return {0:'a',4:'b',7:'c'}[member]
    raise ValueError('unsupported original competency')


def _make_item(qid, family, rng, scope):
    key=rng.choice(scope['major_keys']); scale=_scale(key); given={}; names=[]; chord=False
    if family=='duration_ratio':
        longer,shorter=rng.sample(list(VALUES),2)
        if VALUES[longer]<VALUES[shorter]:longer,shorter=shorter,longer
        given={'longer':longer,'shorter':shorter}; ratio=VALUES[longer]/VALUES[shorter]
        prompt=f'How many {shorter} values equal one {longer} value? Compare written duration, not tempo.'
        alternatives=[str(1/ratio),str(ratio*2),str(ratio/2)]
    elif family=='note_name':
        given={'us_name':rng.choice(list(US))}; prompt=f"Choose the UK note-value name for a {given['us_name']}."
        alternatives=rng.sample(list(VALUES),len(VALUES))
    elif family in ('major_scale_degree','tonic_interval_number','tonic_interval_quality'):
        target=rng.choice(scale[1:]); names=[scale[0],target]
        given={'key':key,'tonic':scale[0],'target':target,'written_notes':names}
        if family=='major_scale_degree': prompt=f'In {key} major, what scale-degree number is {target}, the second written note?'
        elif family=='tonic_interval_number':prompt=f'Count the ascending written interval number from {scale[0]} to {target}, including both letter names.'
        else:prompt=f'Name the quality and number from {scale[0]} up to {target} in {key} major.'
        alternatives=[str(n) for n in rng.sample(range(2,8),6)] if family!='tonic_interval_quality' else ['major 2','major 3','perfect 4','perfect 5','major 6','major 7']
    elif family=='tonic_triad':
        names=[scale[0]];given={'key':key,'written_notes':names}
        prompt=f'The score gives the tonic of {key} major. Which list spells its root-position tonic triad from bottom to top?'
        alternatives=['-'.join(scale[i][:-1] for i in indices) for indices in ((1,3,5),(3,5,0),(4,6,1))]
    elif family=='compound_meter':
        given={'numerator':rng.choice((6,9,12)),'denominator':8}
        prompt=f"Using compound-meter grouping in {given['numerator']}/8, how many dotted-crotchet pulses fill a bar?"
        alternatives=[str(given['numerator']),str(given['numerator']//2),'1','4']
    elif family=='enharmonic_equivalence':
        names=[rng.choice(('C#4','D#4','F#4','G#4','A#4'))];given={'note':names[0],'written_notes':names}
        key='C';prompt=f'In twelve-tone equal temperament, which flat-spelled pitch sounds the same as {names[0]}?'
        alternatives=['Db4','Eb4','Gb4','Ab4','Bb4']
    elif family=='triad_inversion':
        rotation=rng.randrange(3);triad=[scale[i] for i in (0,2,4)]
        names=triad[rotation:]+[n[:-1]+str(int(n[-1])+1) for n in triad[:rotation]];chord=True
        given={'key':key,'root':scale[0],'written_notes':names}
        prompt=f'Identify the inversion of this {key}-major tonic triad using ABRSM a/b/c suffixes. Use the lowest sounding note.'
        alternatives=['a','b','c']
    else:raise ValueError('no verified original template')
    item={'question_id':qid,'competency':family,'prompt':prompt,'given':given,'marks':1,'response_type':'single_select','origin':'system_original',
          'concept_id':'music:'+family,'passage_id':qid+':passage' if names else None,'claim_id':qid+':claim'}
    correct=solve_item(item);options=list(dict.fromkeys([correct]+alternatives))[:4];rng.shuffle(options)
    item['options']=[{'id':chr(65+i),'text':value} for i,value in enumerate(options)]
    if names:item['musicxml']=_score(names,key,chord)
    return item

def _paper_id(grade, syllabus_id, seed):
    return 'original-mini:' + hashlib.sha256(f'v2:{grade}:{syllabus_id}:{seed}'.encode()).hexdigest()[:20]


def build_mini_exam(*, grade, syllabus_id, seed, source_questions=()):
    scope=syllabus_for(syllabus_id,grade)
    if scope['state']=='review_required':return scope
    if type(seed) is not int:raise ValueError('integer seed required')
    rng=random.Random(seed);paper_id=_paper_id(grade,syllabus_id,seed)
    families=rng.sample(scope['generator_competencies'],5)
    questions=[_make_item(paper_id+f':q{i+1}',family,rng,scope) for i,family in enumerate(families)]
    def normalized(value):
        value=' '.join(value.casefold().split())
        value=re.sub(r'\b[a-g](?:#|b)?[0-8]?\b','PITCH',value)
        return re.sub(r'\b\d+(?:/\d+)?\b','NUMBER',value)
    if any(difflib.SequenceMatcher(None,normalized(q['prompt']),normalized(s)).ratio()>=0.84 for q in questions for s in source_questions):
        return {'state':'review_required','reason':'duplicate or near-duplicate source question requires independent redesign'}
    common={'paper_id':paper_id,'version':'1.1','disclaimer':DISCLAIMER}
    methods={
        'duration_ratio':'Measure both note values in crotchet units, then divide the longer by the shorter. This compares duration, not tempo.',
        'note_name':'Keep UK and US note-name conventions separate. Match the duration value, not a literal translation of the word.',
        'major_scale_degree':'Start with the named major-key tonic as degree 1 and count the written letter names upwards.',
        'tonic_interval_number':'Count both starting and ending letter names. Accidentals change interval quality, not its number.',
        'tonic_interval_quality':'Count letter names for the number and semitones for the quality. Within this major scale, 4ths/5ths are perfect and 2nds/3rds/6ths/7ths are major.',
        'tonic_triad':'Build the tonic triad from scale degrees 1, 3 and 5, retaining the key signature spellings.',
        'compound_meter':'Group the quavers in threes. Each group forms one dotted-crotchet pulse; divide the numerator by 3.',
        'enharmonic_equivalence':'Compare sounding semitone positions in twelve-tone equal temperament while retaining different written spellings.',
        'triad_inversion':'Identify the lowest sounding chord member. Root, third and fifth in the bass correspond to a, b and c respectively in this exam convention.'}
    answers=[];worked=[];rubric=[];mapping=[]
    for q in questions:
        answer=solve_item(q);option=next(o['id'] for o in q['options'] if o['text']==answer)
        links={k:q[k] for k in ('question_id','concept_id','passage_id','claim_id')}
        answers.append({**links,'answer_text':answer,'correct_option_id':option,'origin':'ai_derived_answer','derivation':'independent_rule_solver'})
        worked.append({**links,'worked_solution':methods[q['competency']]+f' For these givens, the result is {answer}; choose {option}.','origin':'ai_derived_answer'})
        rubric.append({**links,'marks':1,'criteria':[{'marks':1,'condition':'Choose '+option},{'marks':0,'condition':'Any other response'}],'practice_feedback_only':True,'official_score':False})
        mapping.append({**links,'competency_id':q['competency'],'source_id':scope['source_id'],'source_locator':scope['source_locator']})
    bundle={
        'student_paper':{**common,'kind':'original_targeted_mini_paper','grade':grade,'syllabus_id':syllabus_id,'full_exam_blueprint_verified':False,'questions':questions},
        'answer_key':{**common,'answers':answers},'worked_solutions':{**common,'solutions':worked},
        'marking_rubric':{**common,'criteria':rubric,'practice_feedback_only':True},
        'competency_map':{**common,'items':mapping,'difficulty':'estimated','grade_equivalences':[],
            'source_applicability':scope['current_exam_applicability'],'source_url':scope['source_url'],
            'originality':{'method':'independent_construction','comparison_corpus_size':len(source_questions),'limit':'No universal originality or expert-calibration claim'}}}
    validate_mini_exam(bundle)
    return bundle


def validate_mini_exam(bundle: dict) -> dict:
    expected = {"student_paper", "answer_key", "worked_solutions", "marking_rubric", "competency_map"}
    if set(bundle) != expected:
        raise ValueError("five separate deliverables required")
    student = bundle["student_paper"]
    scope = syllabus_for(student["syllabus_id"], student["grade"])
    if scope["state"] == "review_required" or student.get("full_exam_blueprint_verified") is not False:
        raise ValueError("invalid mini-paper scope")
    questions = student["questions"]
    if len(questions) != 5 or len({q["question_id"] for q in questions}) != 5:
        raise ValueError("five unique question revisions required")
    if any(x in student for x in ("answers", "correct_option_id", "worked_solution")):
        raise ValueError("student bundle contains answer fields")
    answers = {a["question_id"]: a for a in bundle["answer_key"]["answers"]}
    solutions = {a["question_id"]: a for a in bundle["worked_solutions"]["solutions"]}
    rubric = {a["question_id"]: a for a in bundle["marking_rubric"]["criteria"]}
    mapping = {a["question_id"]: a for a in bundle["competency_map"]["items"]}
    ids = {q["question_id"] for q in questions}
    if any(set(group) != ids for group in (answers, solutions, rubric, mapping)):
        raise ValueError("question/key/rubric/competency IDs disagree")
    if len({q["competency"] for q in questions}) != 5:
        raise ValueError("mini-paper requires five distinct competencies")
    if any(part["paper_id"] != student["paper_id"] for part in bundle.values()):
        raise ValueError("cross-paper artifact linkage")
    for q in questions:
        qid = q["question_id"]
        if q["competency"] not in scope["generator_competencies"]:
            raise ValueError("question exceeds source-bound competency scope")
        if q["given"].get("key") and q["given"]["key"] not in scope["major_keys"]:
            raise ValueError("question exceeds grade key scope")
        options = q["options"]
        if len(options) < 3 or len({o["text"] for o in options}) != len(options) or len({o["id"] for o in options}) != len(options):
            raise ValueError("invalid distractors")
        if "musicxml" in q:
            score = parse_score(q["musicxml"])
            expected_pitches = [_pitch(n)[3] for n in q["given"]["written_notes"]]
            if [event.midi for event in score.events] != expected_pitches:
                raise ValueError("notation disagrees with question givens")
            if max(e.onset + e.duration for e in score.events) != Fraction(4):
                raise ValueError("notated duration disagrees with measure")
            if q["given"].get("key") and ET.fromstring(q["musicxml"]).findtext(".//attributes/key/fifths") != str(FIFTHS[q["given"]["key"]]):
                raise ValueError("notation key signature differs from question key")
        answer = solve_item(q)
        if answer != answers[qid]["answer_text"]:
            raise ValueError("answer key disagrees with independent solver")
        matches = [o for o in options if o["text"] == answer]
        if len(matches) != 1 or matches[0]["id"] != answers[qid]["correct_option_id"]:
            raise ValueError("option ID and answer text disagree")
        if mapping[qid]["competency_id"] != q["competency"] or mapping[qid]["source_id"] != scope["source_id"]:
            raise ValueError("competency map mismatch")
    return {"state": "passed", "questions": len(questions), "scope": "original_historical_outline_practice"}


def export_mini_exam(bundle: dict, directory: Path, *, no_save: bool = False) -> dict:
    if type(no_save) is not bool or no_save:
        raise ValueError("no-save forbids paper export")
    validate_mini_exam(bundle)
    directory = Path(directory).resolve()
    if directory.exists():
        raise ValueError("export destination already exists")
    student = directory / "student"
    teacher = directory / "teacher"
    scores = student / "scores"
    scores.mkdir(parents=True)
    teacher.mkdir(parents=True)
    paper = bundle["student_paper"]
    lines = ["# Original targeted mini-paper", "", DISCLAIMER, "",
             f"Grade {paper['grade']} historical scope; current exam equivalence not verified.", ""]
    for index, q in enumerate(paper["questions"], 1):
        lines.extend([f"## {index}. {q['prompt']}", ""])
        for option in q["options"]:
            lines.append(f"- {option['id']}. {option['text']}")
        if q.get("musicxml"):
            score_name = f"q{index}.musicxml"
            (scores / score_name).write_text(q["musicxml"], encoding="utf-8")
            lines.extend(["", f"Score: scores/{score_name}"])
        lines.append("")
    (student / "paper.md").write_text("\n".join(lines), encoding="utf-8")
    (student / "paper.json").write_text(json.dumps(paper, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    for key, filename in (("answer_key", "answer_key.json"), ("worked_solutions", "worked_solutions.json"),
                          ("marking_rubric", "marking_rubric.json"), ("competency_map", "competency_map.json")):
        (teacher / filename).write_text(json.dumps(bundle[key], ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    hashes = {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
              for path in directory.rglob("*") if path.is_file()}
    (directory / "manifest.json").write_text(json.dumps({"paper_id": paper["paper_id"], "files": hashes}, indent=2)+"\n", encoding="utf-8")
    return {"directory": str(directory), "artifact_hashes": hashes, "state": "original_practice_for_review"}
