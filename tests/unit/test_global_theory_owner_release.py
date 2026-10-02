"""Second-pass independent release gates after the read-only review."""
import copy
import tempfile
import unittest
from pathlib import Path

from tutor_framework.domains.music.global_theory.exam import ExamStore, PurposeGrant
from tests.unit.test_global_theory_owner_exam import original_pdf, resource, parsed_paper


class ReleaseSafetyAcceptance(unittest.TestCase):
    def setup_store(self, storage_root=None, **kwargs):
        source = resource()
        store = ExamStore({source["resource_id"]: source}, tenant_id="release-test", storage_root=storage_root, **kwargs)
        grant = PurposeGrant("release-fixture", (source["resource_id"],), "internal_evaluation", "release-test", True)
        payload = parsed_paper()
        second = copy.deepcopy(payload["questions"][0]); second["original_number"] = "2"
        payload["questions"].append(second)
        paper = store.ingest(source["resource_id"], original_pdf(), grant, lambda _: copy.deepcopy(payload))
        return store, grant, paper

    def test_exam_session_withholds_other_questions_of_the_same_paper(self):
        store, _, paper = self.setup_store()
        first, second = [q["question_id"] for q in paper["questions"]]
        store.add_layer(second, "ai_derived_answer", "SECRET-SECOND-ANSWER", source_id="model")
        store.tutor(first, "exam_simulation", session_id="exam-one")
        with self.assertRaises((ValueError, PermissionError)):
            store.tutor(second, "worked", confirmed_question_id=second)

    def test_derived_provenance_cannot_name_a_different_paper_revision(self):
        store, _, paper = self.setup_store()
        with self.assertRaises(ValueError):
            store.add_layer(paper["questions"][0]["question_id"], "ai_derived_answer", "Quaver",
                            source_id="model", source_paper_revision_id="ANOTHER-PAPER-REVISION")

    def test_retrieve_is_a_detached_public_snapshot(self):
        store, _, paper = self.setup_store()
        retrieved = store.retrieve(number="1")
        retrieved[0]["regions"][0]["bbox"][0] = -100
        self.assertGreaterEqual(store.retrieve(number="1")[0]["regions"][0]["bbox"][0], 0)

    def test_question_hierarchy_cannot_contain_a_longer_cycle(self):
        source = resource()
        store = ExamStore({source["resource_id"]: source}, tenant_id="release-test")
        grant = PurposeGrant("release-fixture", (source["resource_id"],), "internal_evaluation", "release-test", False)
        payload = parsed_paper()
        second = copy.deepcopy(payload["questions"][0]); second["original_number"] = "2"
        payload["questions"][0]["parent_number"] = "2"; second["parent_number"] = "1"
        payload["questions"].append(second)
        with self.assertRaises(ValueError):
            store.ingest(source["resource_id"], original_pdf(), grant, lambda _: payload)

    def test_parser_success_does_not_create_document_identity_evidence(self):
        source = resource(document_verified=False)
        store = ExamStore({source["resource_id"]: source}, tenant_id="release-test")
        grant = PurposeGrant("release-fixture", (source["resource_id"],), "internal_evaluation", "release-test", False)
        paper = store.ingest(source["resource_id"], original_pdf(), grant, lambda _: parsed_paper())
        self.assertFalse(paper["flags"]["document_verified"])
        self.assertTrue(paper["flags"]["parsed"])
        self.assertFalse(paper["flags"]["musically_verified"])

    def test_persisted_bank_can_be_reopened_without_losing_answer_origin(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, _, paper = self.setup_store(storage_root=Path(tmp))
            qid = paper["questions"][0]["question_id"]
            store.add_layer(qid, "ai_derived_answer", "Quaver", source_id="model")
            source = resource()
            reopened = ExamStore({source["resource_id"]: source}, tenant_id="release-test", storage_root=Path(tmp))
            self.assertEqual(len(reopened.retrieve()), 2)
            answer = reopened.tutor(qid, "worked", confirmed_question_id=qid)
            self.assertEqual(answer["answer_origin"], "ai_derived_answer")
            self.assertEqual(answer["answer"], "Quaver")

    def test_reopened_active_exam_still_withholds_answers(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, _, paper = self.setup_store(storage_root=Path(tmp))
            qid = paper["questions"][0]["question_id"]
            store.add_layer(qid, "ai_derived_answer", "Quaver", source_id="model")
            store.tutor(qid, "exam_simulation", session_id="exam-one")
            source = resource()
            reopened = ExamStore({source["resource_id"]: source}, tenant_id="release-test", storage_root=Path(tmp))
            with self.assertRaises((ValueError, PermissionError)):
                reopened.tutor(qid, "worked", confirmed_question_id=qid)

    def test_persistent_tenant_isolation(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.setup_store(storage_root=Path(tmp))
            source = resource()
            other = ExamStore({source["resource_id"]: source}, tenant_id="other-learner", storage_root=Path(tmp))
            self.assertEqual(other.retrieve(), [])

    def test_learner_answer_is_retained_in_its_own_layer(self):
        store, _, paper = self.setup_store()
        qid = paper["questions"][0]["question_id"]
        store.add_layer(qid, "ai_derived_answer", "Quaver", source_id="model")
        result = store.tutor(qid, "check", confirmed_question_id=qid, attempt="Crotchet")
        self.assertEqual(result.get("learner_answer"), "Crotchet")
        self.assertEqual(result.get("learner_answer_origin"), "learner_answer")

    def test_unknown_answer_does_not_mark_the_learner_wrong(self):
        store, _, paper = self.setup_store()
        qid = paper["questions"][0]["question_id"]
        result = store.tutor(qid, "check", confirmed_question_id=qid, attempt="Maybe C4")
        self.assertEqual(result["state"], "review_required")
        self.assertNotIn("differs", result["feedback"].casefold())
        self.assertNotIn("incorrect", result["feedback"].casefold())


if __name__ == "__main__":
    unittest.main()
