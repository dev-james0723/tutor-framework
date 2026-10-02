import importlib
import json
import tempfile
import unittest
from pathlib import Path
from tutor_framework.domains.music.global_theory import LearnerContext


class OpenPracticeAcceptance(unittest.TestCase):
    def setUp(self):
        try:self.module=importlib.import_module('tutor_framework.domains.music.global_theory.open_practice')
        except ModuleNotFoundError:self.fail('Open-response practice is not implemented')

    def build(self,topic='voice_leading',seed=12,context=None):
        return self.module.build_open_practice(topic=topic,seed=seed,context=context or LearnerContext())

    def test_open_tasks_have_five_separate_outputs_not_mcq_assumptions(self):
        for topic in ('voice_leading','composition','form_comparison'):
            with self.subTest(topic=topic):
                bundle=self.build(topic)
                self.assertEqual(set(bundle),{'student_paper','answer_key','worked_solutions','marking_rubric','competency_map'})
                student=bundle['student_paper']
                self.assertEqual(student['response_type'],'open_response')
                self.assertNotIn('options',student)
                self.assertIn('Unofficial original practice material. Not endorsed by ABRSM.',student['disclaimer'])
                self.assertFalse(bundle['competency_map']['full_exam_blueprint_verified'])
                self.assertEqual(bundle['competency_map']['difficulty'],'estimated')
                self.assertEqual(bundle['answer_key']['origin'],'system_created_example_not_official')

    def test_advanced_board_request_is_not_mistaken_for_verified_alignment(self):
        for grade in ('6','7','8'):
            context=LearnerContext(curriculum_context={'id':'ABRSM','version':'unknown','grade':grade})
            bundle=self.build(context=context)
            self.assertEqual(bundle['competency_map']['curriculum_alignment'],'review_required')
            self.assertEqual(bundle['competency_map']['requested_context']['grade'],grade)
            self.assertFalse(bundle['marking_rubric']['official_prediction'])

    def test_unreviewed_free_response_does_not_receive_a_fake_grade(self):
        result=self.module.assess_open_response(self.build(), 'I kept both voices moving in similar motion.')
        self.assertEqual(result['state'],'review_required')
        self.assertIsNone(result['score'])
        self.assertEqual(result['learner_answer_origin'],'learner_answer')
        self.assertTrue(result['review_checklist'])
        self.assertFalse(result['official_prediction'])

    def test_rubric_awards_support_partial_credit_and_reviewer_attribution(self):
        bundle=self.build();criteria=bundle['marking_rubric']['criteria']
        awards={c['criterion_id']:1 for c in criteria}
        result=self.module.assess_open_response(bundle,'Original response',criterion_awards=awards,reviewer_id='teacher-supplied-review')
        self.assertEqual(result['score'],len(criteria))
        self.assertEqual(result['score_origin'],'caller_supplied_reviewer_result')
        self.assertTrue(result['practice_feedback_only'])
        self.assertFalse(result['official_prediction'])

    def test_invalid_or_incomplete_rubric_marks_are_not_silently_accepted(self):
        bundle=self.build();criteria=bundle['marking_rubric']['criteria'];awards={c['criterion_id']:1 for c in criteria}
        with self.assertRaises(ValueError):self.module.assess_open_response(bundle,'response',criterion_awards=awards)
        awards[criteria[0]['criterion_id']]=True
        with self.assertRaises(ValueError):self.module.assess_open_response(bundle,'response',criterion_awards=awards,reviewer_id='teacher')
        with self.assertRaises(ValueError):self.module.assess_open_response(bundle,'response',criterion_awards={},reviewer_id='teacher')

    def test_student_and_teacher_exports_are_separate_and_no_save_blocks_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'open';bundle=self.build('composition')
            result=self.module.export_open_practice(bundle,path)
            self.assertTrue((path/'student'/'paper.md').is_file())
            self.assertTrue((path/'teacher'/'answer_key.json').is_file())
            self.assertNotIn('model_response',(path/'student'/'paper.json').read_text())
            self.assertNotIn('correct_option_id',json.dumps(bundle['student_paper']))
            self.assertEqual(result['state'],'original_open_practice_for_review')
            with self.assertRaises(ValueError):self.module.export_open_practice(bundle,Path(tmp)/'blocked',no_save=True)
            self.assertFalse((Path(tmp)/'blocked').exists())

    def test_student_only_export_never_writes_teacher_answers(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'student-only'
            result=self.module.export_open_practice(self.build('composition'),path,student_only=True)
            self.assertTrue((path/'student'/'paper.md').is_file())
            self.assertFalse((path/'teacher').exists())
            self.assertTrue(all(not name.startswith('teacher/') for name in result['artifact_hashes']))

    def test_no_save_follows_the_bundle_into_a_later_export_call(self):
        bundle=self.build(context=LearnerContext(no_save=True))
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'forbidden'
            with self.assertRaises(ValueError):self.module.export_open_practice(bundle,path)
            self.assertFalse(path.exists())
            with self.assertRaises(ValueError):self.module.export_open_practice(bundle,path,no_save=False)
            self.assertFalse(path.exists())

    def test_generated_material_is_deterministic_and_explicitly_original(self):
        self.assertEqual(self.build(seed=4),self.build(seed=4))
        self.assertNotEqual(self.build(seed=4),self.build(seed=5))
        for artifact in self.build().values():
            self.assertTrue(artifact['paper_id'])
            self.assertTrue(artifact['question_id'])
            self.assertTrue(artifact['claim_id'])

    def test_unknown_domain_is_not_fabricated_as_classical_expertise(self):
        result=self.build('unverified_gamelan_counterpoint')
        self.assertEqual(result['state'],'unsupported')


if __name__=='__main__':unittest.main()
