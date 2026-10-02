import importlib
import json
import unittest
from tutor_framework.domains.music.global_theory import LearnerContext


def musicxml(two_measures=True):
    measures=[]
    for number,steps in enumerate(('CDEG','AFED') if two_measures else ('CDEG',),1):
        notes=''.join(f'<note id="m{number}-n{i}"><pitch><step>{step}</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><type>quarter</type></note>' for i,step in enumerate(steps,1))
        attributes='<attributes><divisions>1</divisions><key><fifths>0</fifths></key><time><beats>4</beats><beat-type>4</beat-type></time><clef><sign>G</sign><line>2</line></clef></attributes>' if number==1 else ''
        measures.append(f'<measure number="{number}">{attributes}{notes}</measure>')
    return '<score-partwise version="4.0"><part-list><score-part id="P1"><part-name>Original fixture</part-name></score-part></part-list><part id="P1">'+''.join(measures)+'</part></score-partwise>'


class SourceBoundWorkflow(unittest.TestCase):
    def setUp(self):
        try:self.module=importlib.import_module('tutor_framework.domains.music.global_theory.score_workflow')
        except ModuleNotFoundError:self.fail('The source-bound score workflow is not implemented')

    def test_two_measures_keep_global_timing_and_exact_note_anchors(self):
        result=self.module.analyze_score(musicxml(),source_id='user-score',context=LearnerContext(response_language='zh-Hant'))
        self.assertEqual(result['event_count'],8)
        self.assertEqual(result['events'][4]['absolute_onset'],'4')
        self.assertEqual(result['events'][4]['measure'],'2')
        self.assertEqual(result['events'][4]['notation_ids'],['m2-n1'])
        self.assertEqual(result['events'][4]['written_pitch'],'A4')
        self.assertEqual(result['source_id'],'user-score')
        self.assertFalse(result['omr_verified'])
        self.assertEqual(result['formal_analysis']['state'],'review_required')
        self.assertRegex(result['summary'],'[\u4e00-\u9fff]')
        self.assertTrue(result['claim_ids'])

    def test_pdf_bytes_do_not_become_invented_notation(self):
        result=self.module.analyze_score(b'%PDF-1.4 not parsed',source_id='source-pdf',context=LearnerContext())
        self.assertEqual(result['state'],'review_required')
        self.assertEqual(result['event_count'],0)
        self.assertEqual(result['required_pipeline'],'MinerU + existing score/OMR review')

    def test_invalid_xml_does_not_produce_a_successful_analysis(self):
        with self.assertRaises(ValueError):self.module.analyze_score('<broken>',source_id='score',context=LearnerContext())

    def test_form_labels_need_explicit_framework_and_valid_passages(self):
        boundaries=[{'start_measure':'1','end_measure':'2','label':'presentation candidate','framework':'Caplin'}]
        result=self.module.analyze_score(musicxml(),source_id='score',context=LearnerContext(analysis_framework='Caplin'),formal_annotations=boundaries)
        self.assertEqual(result['formal_analysis']['annotations'][0]['origin'],'caller_analytical_interpretation')
        self.assertNotEqual(result['formal_analysis']['state'],'verified')
        boundaries[0]['end_measure']='9'
        with self.assertRaises(ValueError):self.module.analyze_score(musicxml(),source_id='score',context=LearnerContext(),formal_annotations=boundaries)

    def test_lecture_score_disagreement_is_retained_not_resolved_by_guessing(self):
        records=[{'claim_id':'lecture-c','source_id':'lecture','subject':'m2.final_pitch','value':'F4','kind':'source_statement','revision':'v1'},
                 {'claim_id':'score-c','source_id':'score','subject':'m2.final_pitch','value':'D4','kind':'notation_observation','revision':'v1'}]
        before=json.dumps(records,sort_keys=True)
        result=self.module.reconcile_claims(records)
        self.assertEqual(result['state'],'review_required')
        self.assertEqual(len(result['conflicts']),1)
        self.assertEqual(set(result['conflicts'][0]['claim_ids']),{'lecture-c','score-c'})
        self.assertEqual(json.dumps(records,sort_keys=True),before)

    def test_enharmonic_notation_changes_have_distinct_claim_revisions(self):
        source=musicxml(False)
        sharp=source.replace('<step>C</step><octave>4</octave>','<step>C</step><alter>1</alter><octave>4</octave>',1)
        flat=source.replace('<step>C</step><octave>4</octave>','<step>D</step><alter>-1</alter><octave>4</octave>',1)
        first=self.module.analyze_score(sharp,source_id='same-score')
        second=self.module.analyze_score(flat,source_id='same-score')
        self.assertNotEqual(first['events'][0]['claim_id'],second['events'][0]['claim_id'])
        self.assertNotEqual(first['notation_revision'],second['notation_revision'])

    def test_chord_members_are_not_chosen_as_an_automatic_melody(self):
        source=musicxml(False)
        chord='<note id="chord-member"><chord/><pitch><step>E</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice></note>'
        source=source.replace('</note>','</note>'+chord,1)
        result=self.module.analyze_score(source,source_id='polyphonic-source')
        pairs=[(v['from_event'],v['to_event']) for v in result['melodic_intervals']]
        self.assertNotIn(('chord-member','m1-n2'),pairs)
        self.assertNotIn(('m1-n1','m1-n2'),pairs)
        self.assertEqual(result['event_count'],5)

    def test_tie_continuation_is_not_a_new_melodic_unison(self):
        source=musicxml(False).replace('<step>D</step>','<step>C</step>',1)
        source=source.replace('</note>','<tie type="start"/></note>',1)
        source=source.replace('<note id="m1-n2">','<note id="m1-n2"><tie type="stop"/>',1)
        result=self.module.analyze_score(source,source_id='tied-source')
        self.assertNotIn(('m1-n1','m1-n2'),[(v['from_event'],v['to_event']) for v in result['melodic_intervals']])
        self.assertEqual(result['event_count'],4)

    def test_optional_interval_limits_do_not_discard_valid_high_score_events(self):
        source=musicxml(False).replace('<octave>4</octave>','<octave>9</octave>')
        result=self.module.analyze_score(source,source_id='high-register-source')
        self.assertEqual(result['event_count'],4)
        self.assertEqual(result['events'][0]['midi'],120)
        self.assertTrue(result['melodic_interval_warnings'])

    def test_curriculum_comparison_returns_competencies_not_grade_equivalence(self):
        from tutor_framework.domains.music.global_theory.curriculum import packs
        ids=[p['curriculum_id'] for p in packs()]
        result=self.module.compare_curricula(ids[0],ids[1])
        self.assertEqual(result['grade_equivalences'],[])
        self.assertIn('transferable_competencies',result)
        self.assertIn('requires_confirmation',result)
        unknown=self.module.compare_curricula('not-a-course',ids[0])
        self.assertEqual(unknown['state'],'unsupported')


if __name__=='__main__':unittest.main()
