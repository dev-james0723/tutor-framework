import unittest
import hashlib

from tutor_framework.domains.music.global_theory import LearnerContext, route, terminology
from tutor_framework.domains.music.global_theory.exam import ExamStore, PurposeGrant
from tutor_framework.domains.music.global_theory.practice import build_original_practice


class GlobalTheoryTest(unittest.TestCase):
    def test_simple_mixed_context_is_immediate_and_keeps_preferences_separate(self):
        context = LearnerContext(
            response_language="zh-Hant",
            terminology_preference={"note_names": "en-GB", "cadences": "US-AP"},
            curriculum_context={"id": "AP-Music-Theory", "version": "unknown"},
        )
        result = route("What is a crotchet?", context)
        self.assertEqual(result["mode"], "direct")
        self.assertEqual(result["questions"], [])
        self.assertEqual(result["deliverables"], ["text"])
        self.assertIn("四分音符", result["answer"])
        self.assertEqual(terminology("imperfect cadence", context)["relation"], "not-equivalent")

    def test_exam_intake_requires_rights_identity_and_independent_review(self):
        pdf = b"%PDF-1.4\nsynthetic test bytes"
        digest = hashlib.sha256(pdf).hexdigest()
        catalogue = {"SYN-G1-Q": {"resource_id": "SYN-G1-Q", "board": "ABRSM", "grade": 1,
                                    "year": "synthetic", "paper": "sample", "language": "en",
                                    "syllabus_id": "synthetic-v1", "sha256": digest, "rights": "test-only"}}
        store = ExamStore(catalogue, tenant_id="alice", no_save=True)
        with self.assertRaises(ValueError):
            store.ingest("SYN-G1-Q", pdf, None, lambda _: {})
        grant = PurposeGrant("G1", ("SYN-G1-Q",), "private_study", "alice", False)
        with self.assertRaises(ValueError):
            store.ingest("SYN-G1-Q", pdf+b"x", grant, lambda _: {})
        parsed = {"page_map": [{"pdf_page_index": 0, "printed_page_label": "1"}],
                  "questions": [{"original_number": "1", "parent_number": None,
                                 "stem": "Which rest completes the bar?", "pages": [0],
                                 "regions": [{"page": 0, "bbox": [0.1, 0.1, 0.5, 0.4]}],
                                 "options": [{"label": "A", "text": "crotchet rest"},
                                             {"label": "B", "text": "minim rest"}],
                                 "marks": 1, "response_type": "single_select",
                                 "concept_ids": ["rhythm.duration"]}]}
        paper = store.ingest("SYN-G1-Q", pdf, grant, lambda _: parsed)
        self.assertEqual(paper["flags"]["parsed"], True)
        self.assertEqual(paper["flags"]["musically_verified"], False)
        self.assertEqual(paper["flags"]["reviewed_usable"], False)
        self.assertEqual(store.retrieve(grade=1, paper="sample")[0]["original_number"], "1")

    def test_original_practice_has_separate_student_and_answer_artifacts(self):
        bundle = build_original_practice(grade=1, syllabus_id="abrsm-theory-from-2020",
                                         competency_id="rhythm.duration", seed=37)
        self.assertEqual(set(bundle), {"student_paper", "answer_key", "worked_solutions",
                                       "marking_rubric", "competency_map"})
        self.assertIn("Unofficial original practice material. Not endorsed by ABRSM.", bundle["student_paper"]["disclaimer"])
        self.assertNotIn("correct_option_id", str(bundle["student_paper"]))
        self.assertEqual(bundle["competency_map"]["difficulty"], "estimated")
        self.assertEqual(build_original_practice(grade=7, syllabus_id="unknown",
                                                competency_id="harmony", seed=37)["state"], "review_required")


if __name__ == "__main__":
    unittest.main()
