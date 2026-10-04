import base64
import io
import json
import zipfile
import pytest

SCORE = b'''<score-partwise version="4.0"><part-list><score-part id="P1"><part-name>Study</part-name></score-part></part-list><part id="P1"><measure number="1"><attributes><divisions>1</divisions><time><beats>4</beats><beat-type>4</beat-type></time><clef><sign>G</sign><line>2</line></clef></attributes><note id="e1"><pitch><step>C</step><octave>4</octave></pitch><duration>2</duration><voice>1</voice><type>half</type></note><note id="e2"><pitch><step>E</step><alter>-1</alter><octave>4</octave></pitch><duration>2</duration><voice>1</voice><type>half</type></note></measure></part></score-partwise>'''

def test_engraving_remains_available_on_new_service_workers():
    from concurrent.futures import ThreadPoolExecutor
    from theory_api.engine import score
    from theory_api.schemas import ScoreRequest
    request = ScoreRequest(filename='worker.musicxml', source_id='synthetic-worker', data_base64=base64.b64encode(SCORE).decode())
    score(request)
    with ThreadPoolExecutor(max_workers=1) as worker:
        assert worker.submit(score,request).result()['event_count'] == 2

def test_oversized_body_is_rejected_before_parsing(client):
    response=client.post('/v1/score/analyze',content=b'X'*3_000_001,headers={'content-type':'application/json'})
    assert response.status_code==413

@pytest.mark.parametrize('operation,inputs,key,value', [
    ('interval', {'first':'C4','second':'Eb4'}, 'quality', 'minor'),
    ('scale', {'tonic':'F#4','mode':'major'}, 'notes', ['F#4','G#4','A#4','B4','C#5','D#5','E#5','F#5']),
    ('chord', {'notes':['B3','D4','F4','G4']}, 'figured_bass', '6/5'),
    ('meter', {'numerator':6,'denominator':8}, 'groups', [3,3]),
    ('solfege', {'system':'fixed_do','notes':['C#4']}, 'system', 'fixed_do'),
    ('voice-leading', {'before':{'soprano':'G4','bass':'C4'},'after':{'soprano':'A4','bass':'D4'},'style':'common_practice'}, 'complete_counterpoint_assessment', False),
])
def test_explicit_operations_wrap_existing_engine(client, operation, inputs, key, value):
    response = client.post('/v1/theory/'+operation, json={'inputs':inputs})
    assert response.status_code == 200, response.text
    data=response.json()
    assert data['payload']['data'][key] == value
    assert data['request_id'] and data['engine_version'] == '0.3.0'
    assert data['claim_ids'] and data['source_ids']
    assert data['status'] == 'computed_from_explicit_input'
    assert data['review_required'] is False

@pytest.mark.parametrize('operation,inputs,status', [
    ('interval', {'first':'C','second':'Eb4'},422),
    ('scale', {'tonic':'C4','mode':'unknown'},422),
    ('chord', {'notes':['C4','Db4','D4']},200),
    ('meter', {'numerator':5,'denominator':8},200),
    ('solfege', {'system':'movable_do','notes':['A3']},200),
    ('voice-leading', {'before':{'bass':'C4','soprano':'G4'},'after':{'bass':'D4','soprano':'A4'},'style':'unknown'},200),
])
def test_ambiguity_and_unsupported_input_never_invent_results(client, operation, inputs, status):
    response=client.post('/v1/theory/'+operation,json={'inputs':inputs})
    assert response.status_code == status
    if status == 200: assert response.json()['review_required'] is True

def test_unknown_operation_is_explicitly_unsupported(client):
    response=client.post('/v1/theory/universal-expert',json={'inputs':{}})
    assert response.status_code == 200
    assert response.json()['status']=='unsupported'

def test_unknown_preferences_are_rejected(client):
    assert client.post('/v1/theory/interval',json={'inputs':{'first':'C4','second':'E4'},'context':{'nationality':'CN'}}).status_code==422

def test_score_preserves_event_identity_and_renders_portable_svg(client):
    response=client.post('/v1/score/analyze',json={'filename':'study.musicxml','data_base64':base64.b64encode(SCORE).decode(),'source_id':'test-score'})
    assert response.status_code==200,response.text
    payload=response.json()['payload']
    assert [(e['event_id'],e['written_pitch'],e['absolute_onset']) for e in payload['events']]==[('e1','C4','0'),('e2','Eb4','2')]
    assert '<svg' in payload['svg_pages'][0]
    assert 'id="e1"' in payload['svg_pages'][0]
    assert 'script' not in payload['svg_pages'][0]
    assert payload['omr_verified'] is False

@pytest.mark.parametrize('filename,data', [
    ('study.pdf',b'%PDF-1.4'),('study.png',b'PNG'),('broken.musicxml',b'<score-partwise>'),
    ('xxe.musicxml',b'<!DOCTYPE score-partwise [<!ENTITY leak SYSTEM "file:///etc/passwd">]><score-partwise>&leak;</score-partwise>'),
])
def test_unsafe_or_unsupported_scores_are_rejected(client,filename,data):
    response=client.post('/v1/score/analyze',json={'filename':filename,'data_base64':base64.b64encode(data).decode(),'source_id':'test-score'})
    assert response.status_code==422

def test_mxl_uses_bounded_container_path(client):
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w') as z:
        z.writestr('META-INF/container.xml','<container><rootfiles><rootfile full-path="score.musicxml"/></rootfiles></container>')
        z.writestr('score.musicxml',SCORE)
    response=client.post('/v1/score/analyze',json={'filename':'study.mxl','data_base64':base64.b64encode(buffer.getvalue()).decode(),'source_id':'mxl-score'})
    assert response.status_code==200,response.text
    assert response.json()['payload']['event_count']==2

def test_mxl_traversal_is_rejected(client):
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w') as z:
        z.writestr('../score.musicxml',SCORE)
    assert client.post('/v1/score/analyze',json={'filename':'study.mxl','data_base64':base64.b64encode(buffer.getvalue()).decode(),'source_id':'bad'}).status_code==422

def test_practice_student_projection_has_no_teacher_payload(client):
    response=client.post('/v1/practice/generate',json={'grade':1,'seed':37,'item_index':0,'mode':'check'})
    assert response.status_code==200,response.text
    data=response.json()['payload']
    assert data['item']['question_id'] and data['item']['options']
    assert all(key not in json.dumps(data) for key in ['answer_key','correct_option_id','worked_solution','marking_rubric'])

def test_practice_check_requires_submission(client):
    response=client.post('/v1/practice/check',json={'grade':1,'seed':37,'item_index':0,'mode':'check','action':'hint'})
    assert response.status_code==409

def test_practice_check_marks_original_choice_and_retains_rubric(client):
    response=client.post('/v1/practice/check',json={'grade':1,'seed':37,'item_index':0,'mode':'check','response':'Z'})
    assert response.status_code==200,response.text
    data=response.json()['payload']
    assert data['result_state']=='incorrect'
    assert data['official_score'] is False
    assert data['rubric_version'] and data['answer_exposed'] is True

def test_advanced_practice_preserves_no_invented_grade(client):
    generated=client.post('/v1/practice/generate',json={'topic':'composition','seed':17}).json()['payload']
    assert generated['open_response'] is True
    response=client.post('/v1/practice/check',json={'topic':'composition','seed':17,'response':'My proposed continuation'})
    assert response.status_code==200,response.text
    assert response.json()['payload']['result_state']=='review_required'

@pytest.mark.parametrize('source,target,state', [('ABRSM-G1','ABRSM-G2','competency_comparison_requires_version_review'),('missing','ABRSM-G2','unsupported')])
def test_curriculum_mapping_never_invents_grade_equivalence(client,source,target,state):
    response=client.post('/v1/curricula/compare',json={'source_id':source,'target_id':target})
    assert response.status_code==200,response.text
    assert response.json()['payload']['grade_equivalences']==[]
    assert response.json()['status']==state

def test_evidence_reconciliation_retains_competing_claims(client):
    records=[{'claim_id':n,'source_id':s,'subject':'note','kind':'source','revision':'v1','value':v} for n,s,v in [('a','lecture','C4'),('b','score','D4')]]
    response=client.post('/v1/evidence/reconcile',json={'records':records})
    assert response.status_code==200,response.text
    assert response.json()['review_required'] is True
    assert response.json()['payload']['records']==records

def test_reconciliation_rejects_unidentified_claims(client):
    assert client.post('/v1/evidence/reconcile',json={'records':[{'value':'C4'}]}).status_code==422
