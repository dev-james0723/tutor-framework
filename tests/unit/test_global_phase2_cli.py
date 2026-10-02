import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from tutor_framework.domains.music.global_theory import LearnerContext, route
from tutor_framework.domains.music.global_theory.__main__ import main
from tests.unit.test_global_score_workflow import musicxml


class PhaseTwoInterface(unittest.TestCase):
    def command(self, arguments):
        output=io.StringIO()
        with contextlib.redirect_stdout(output):
            try:code=main(arguments)
            except SystemExit as error:self.fail(f'Command is not implemented: {arguments[0]} ({error.code})')
        self.assertEqual(code,0)
        return json.loads(output.getvalue())

    def test_theory_request_preserves_composed_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            request=Path(tmp)/'request.json';request.write_text(json.dumps({'operation':'chord','notes':['E4','G4','C5']}))
            context=Path(tmp)/'context.json';context.write_text(json.dumps({'response_language':'zh-Hant','no_save':True,'curriculum_context':{'id':'AP-Music-Theory'},'terminology_preference':{'note_names':'en-GB'}}))
            result=self.command(['theory','--request',str(request),'--context',str(context)])
            self.assertEqual(result['data']['root'],'C')
            self.assertEqual(result['data']['inversion'],1)
            self.assertFalse(result['persisted'])
            self.assertEqual(result['context']['response_language'],'zh-Hant')

    def test_explicit_interval_question_is_executed_not_only_routed(self):
        result=route('What is the interval from C4 to Eb4?',LearnerContext())
        self.assertEqual(result['mode'],'direct')
        self.assertIn('minor',result['answer'])
        self.assertEqual(result['operation_result']['data']['number'],3)
        self.assertEqual(result['questions'],[])

    def test_simple_scale_question_gets_exact_spelling(self):
        result=route('Spell the F#4 major scale.',LearnerContext(response_language='zh-Hant'))
        self.assertIn('E#5',result['operation_result']['data']['notes'])
        self.assertRegex(result['answer'],'[\u4e00-\u9fff]')

    def test_known_course_name_is_not_requested_again(self):
        result=route('Analyze this score and create a Learning Pack.',LearnerContext(curriculum_context={'name':'AP Music Theory'},learning_goal='understand',desired_deliverables=('notes',)))
        self.assertFalse(any('which course' in q.casefold() for q in result['questions']))

    def test_text_only_router_removes_visual_deliverables(self):
        result=route('Create a Learning Pack.',LearnerContext(text_only=True,desired_deliverables=('notes','annotated_score','mindmap','video')))
        self.assertEqual(result['deliverables'],['notes'])

    def test_score_analysis_command_reads_real_input_without_writing_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'original.musicxml';path.write_text(musicxml())
            result=self.command(['analyze-score','--score',str(path),'--source-id','original-user-input'])
            self.assertEqual(result['event_count'],8)
            self.assertFalse(result['persisted'])
            self.assertEqual(list(Path(tmp).iterdir()),[path])

    def test_comparison_command_does_not_invent_equivalence(self):
        result=self.command(['compare-curricula','ABRSM-G1','ABRSM-G2'])
        self.assertEqual(result['grade_equivalences'],[])
        self.assertIn('target_gaps',result)

    def test_open_practice_command_can_return_student_only(self):
        result=self.command(['open-practice','--topic','composition','--seed','17','--student-only'])
        self.assertEqual(result['response_type'],'open_response')
        self.assertNotIn('answer_key',result)
        self.assertNotIn('model_response',json.dumps(result))

    def test_resource_metadata_has_exact_urls_but_does_not_grant_processing(self):
        result=self.command(['resources'])
        records=result['resources']
        self.assertEqual(len(records),51)
        sample=next(r for r in records if r['resource_id']=='ABRSM-G1-2020-SAMPLE-Q')
        self.assertTrue(sample['source_url'].startswith('https://www.abrsm.com.tw/'))
        self.assertIsNone(sample['sha256'])
        self.assertEqual(sample['processing_permission'],'pending_scope_confirmation')

    def test_reconcile_command_preserves_conflict(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'claims.json'
            records=[{'claim_id':'a','source_id':'lecture','subject':'pitch','value':'E4','kind':'source_statement','revision':'v1'},
                     {'claim_id':'b','source_id':'score','subject':'pitch','value':'F4','kind':'notation_observation','revision':'v1'}]
            path.write_text(json.dumps({'claims':records}))
            result=self.command(['reconcile','--request',str(path)])
            self.assertEqual(result['state'],'review_required')
            self.assertEqual(len(result['conflicts']),1)


if __name__=='__main__':unittest.main()
