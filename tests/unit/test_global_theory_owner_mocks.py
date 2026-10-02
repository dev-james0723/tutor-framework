"""Original mini-paper content, notation, answer and export acceptance."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from tutor_framework.domains.music.global_theory.mini_exam import (
    build_mini_exam, export_mini_exam, solve_item, validate_mini_exam,
)
from tutor_framework.domains.music.global_theory.syllabus import SYLLABUS_ID, syllabus_for


class OriginalMiniPaperAcceptance(unittest.TestCase):
    def build(self, grade=1, seed=57):
        return build_mini_exam(grade=grade, syllabus_id=SYLLABUS_ID, seed=seed)

    def test_five_separate_deliverables_and_no_full_exam_claim(self):
        bundle = self.build()
        self.assertEqual(set(bundle), {"student_paper", "answer_key", "worked_solutions", "marking_rubric", "competency_map"})
        student = bundle["student_paper"]
        self.assertEqual(len(student["questions"]), 5)
        self.assertEqual(student["kind"], "original_targeted_mini_paper")
        self.assertFalse(student["full_exam_blueprint_verified"])
        self.assertIn("Unofficial original practice material. Not endorsed by ABRSM.", student["disclaimer"])
        self.assertNotIn("correct_option_id", json.dumps(student))
        self.assertNotIn("worked_solution", json.dumps(student))

    def test_all_grades_seeds_and_notation_are_independently_consistent(self):
        for grade in range(1, 6):
            for seed in range(20):
                with self.subTest(grade=grade, seed=seed):
                    bundle = self.build(grade, seed)
                    self.assertEqual(validate_mini_exam(bundle)["state"], "passed")
                    answer_map = {a["question_id"]: a for a in bundle["answer_key"]["answers"]}
                    for question in bundle["student_paper"]["questions"]:
                        self.assertEqual(solve_item(question), answer_map[question["question_id"]]["answer_text"])

    def test_no_syllabus_leakage_or_fake_grade_equivalence(self):
        for grade in range(1, 6):
            bundle = self.build(grade)
            allowed = syllabus_for(SYLLABUS_ID, grade)
            for question in bundle["student_paper"]["questions"]:
                self.assertIn(question["competency"], allowed["generator_competencies"])
                if "key" in question["given"]:
                    self.assertIn(question["given"]["key"], allowed["major_keys"])
            self.assertEqual(bundle["competency_map"]["grade_equivalences"], [])
            self.assertEqual(bundle["competency_map"]["difficulty"], "estimated")

    def test_corrupt_answer_key_is_rejected(self):
        bundle = self.build()
        bundle["answer_key"]["answers"][0]["answer_text"] = "WRONG"
        with self.assertRaises(ValueError):
            validate_mini_exam(bundle)

    def test_corrupt_notation_is_rejected(self):
        bundle = self.build()
        question = next(q for q in bundle["student_paper"]["questions"] if q.get("musicxml"))
        question["musicxml"] = question["musicxml"].replace("<octave>4</octave>", "<octave>9</octave>", 1)
        with self.assertRaises(ValueError):
            validate_mini_exam(bundle)

    def test_duplicate_question_ids_and_invalid_distractors_are_rejected(self):
        bundle = self.build()
        questions = bundle["student_paper"]["questions"]
        questions[1]["question_id"] = questions[0]["question_id"]
        with self.assertRaises(ValueError):
            validate_mini_exam(bundle)
        bundle = self.build()
        question = bundle["student_paper"]["questions"][0]
        question["options"][1]["text"] = question["options"][0]["text"]
        with self.assertRaises(ValueError):
            validate_mini_exam(bundle)

    def test_source_duplicate_is_not_silently_published(self):
        bundle = self.build()
        source = bundle["student_paper"]["questions"][0]["prompt"]
        result = build_mini_exam(grade=1, syllabus_id=SYLLABUS_ID, seed=57, source_questions=(source,))
        self.assertEqual(result["state"], "review_required")
        self.assertIn("duplicate", result["reason"])

    def test_persistence_separates_student_from_teacher_files(self):
        bundle = self.build()
        with tempfile.TemporaryDirectory() as tmp:
            result = export_mini_exam(bundle, Path(tmp) / "mini-paper")
            root = Path(result["directory"])
            self.assertTrue((root / "student" / "paper.md").is_file())
            self.assertTrue((root / "teacher" / "answer_key.json").is_file())
            for path in (root / "student").rglob("*"):
                if path.is_file():
                    self.assertNotIn("correct_option_id", path.read_text())
            self.assertGreater(len(list((root / "student" / "scores").glob("*.musicxml"))), 0)

    def test_no_save_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "forbidden"
            with self.assertRaises((ValueError, PermissionError)):
                export_mini_exam(self.build(), target, no_save=True)
            self.assertFalse(target.exists())

    def test_advanced_or_unknown_scope_returns_honest_review_gate(self):
        for grade in (6, 7, 8):
            self.assertEqual(self.build(grade)["state"], "review_required")
        self.assertEqual(build_mini_exam(grade=1, syllabus_id="2099-unknown", seed=1)["state"], "review_required")

    def test_one_item_per_distinct_competency_not_inflated_variants(self):
        bundle = self.build()
        self.assertEqual(len({q["competency"] for q in bundle["student_paper"]["questions"]}), 5)

    def test_notated_key_signature_agrees_with_question_key(self):
        import xml.etree.ElementTree as ET
        fifths = {"C": 0, "G": 1, "D": 2, "A": 3, "E": 4, "B": 5, "F#": 6,
                  "F": -1, "Bb": -2, "Eb": -3, "Ab": -4, "Db": -5, "Gb": -6}
        checked = 0
        for grade in range(1, 6):
            for seed in range(10):
                for question in self.build(grade, seed)["student_paper"]["questions"]:
                    key = question["given"].get("key")
                    if key and question.get("musicxml"):
                        root = ET.fromstring(question["musicxml"])
                        self.assertEqual(root.findtext(".//attributes/key/fifths"), str(fifths[key]))
                        checked += 1
        self.assertGreater(checked, 20)

    def test_content_is_deterministic_without_global_random_state(self):
        self.assertEqual(self.build(), self.build())
        self.assertNotEqual(self.build(seed=58), self.build(seed=57))


if __name__ == "__main__":
    unittest.main()
