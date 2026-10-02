"""Official-answer authority requires exact verified document evidence, not labels.

All papers here are independently created fixtures, not real ABRSM publications.
"""
import hashlib
import unittest

from tutor_framework.domains.music.global_theory.exam import ExamStore, PurposeGrant
from tests.unit.test_global_theory_owner_exam import original_pdf, resource, parsed_paper


class AnswerAuthorityAcceptance(unittest.TestCase):
    def setup(self, *, authority="official", paper="owner-original"):
        question = resource()
        answer_bytes = original_pdf("1. Quaver")
        answer = resource("synthetic-official-key", resource_type="official_answer" if authority == "official" else "third_party_explanation",
                          authority=authority, answer_for=question["resource_id"], paper=paper,
                          sha256=hashlib.sha256(answer_bytes).hexdigest(),
                          rights="original synthetic fixture; no ABRSM publication copied")
        store = ExamStore({question["resource_id"]: question, answer["resource_id"]: answer}, tenant_id="answer-test")
        grant = PurposeGrant("fixture-grant", (question["resource_id"], answer["resource_id"]), "internal_evaluation", "answer-test", False)
        parsed = store.ingest(question["resource_id"], original_pdf(), grant, lambda _: parsed_paper())
        qid = parsed["questions"][0]["question_id"]
        return store, grant, qid, answer_bytes

    def test_caller_text_is_not_evidence_of_official_answer(self):
        store, grant, qid, answer_bytes = self.setup()
        try:
            store.match_official_answer(qid, answer_resource_id="synthetic-official-key", answer_bytes=answer_bytes,
                                        grant=grant, answer_number="1", answer_text="ARBITRARY WRONG ANSWER")
        except (ValueError, PermissionError):
            return
        result = store.tutor(qid, "worked", confirmed_question_id=qid)
        self.assertNotEqual(result.get("answer"), "ARBITRARY WRONG ANSWER")

    def test_third_party_pdf_cannot_be_relabelled_as_official(self):
        store, grant, qid, answer_bytes = self.setup(authority="third_party")
        with self.assertRaises((ValueError, PermissionError)):
            store.match_official_answer(qid, answer_resource_id="synthetic-official-key", answer_bytes=answer_bytes,
                                        grant=grant, answer_number="1", answer_text="Quaver")

    def test_wrong_set_with_same_grade_year_language_is_not_a_match(self):
        store, grant, qid, answer_bytes = self.setup(paper="different-set")
        with self.assertRaises((ValueError, PermissionError)):
            store.match_official_answer(qid, answer_resource_id="synthetic-official-key", answer_bytes=answer_bytes,
                                        grant=grant, answer_number="1", answer_text="Quaver")

    def test_reviewed_source_region_positive_control(self):
        store, grant, qid, answer_bytes = self.setup()
        result = store.match_official_answer(
            qid, answer_resource_id="synthetic-official-key", answer_bytes=answer_bytes,
            grant=grant, answer_number="1", answer_text="Quaver",
            source_locator={"page": 0, "bbox": [0.0, 0.0, 1.0, 1.0]},
            reviewer_id="synthetic-fixture-reviewer",
        )
        self.assertEqual(result["kind"], "official_answer")
        self.assertTrue(result.get("source_text_verified"))
        answer = store.tutor(qid, "worked", confirmed_question_id=qid)
        self.assertEqual(answer["answer"], "Quaver")
        self.assertEqual(answer["answer_origin"], "official_answer")
        self.assertNotEqual(answer["state"], "musically_verified")

    def test_reviewed_region_cannot_contain_a_different_answer(self):
        store, grant, qid, answer_bytes = self.setup()
        with self.assertRaises((ValueError, PermissionError)):
            store.match_official_answer(
                qid, answer_resource_id="synthetic-official-key", answer_bytes=answer_bytes,
                grant=grant, answer_number="1", answer_text="Crotchet",
                source_locator={"page": 0, "bbox": [0.0, 0.0, 1.0, 1.0]},
                reviewer_id="synthetic-fixture-reviewer",
            )


if __name__ == "__main__":
    unittest.main()
