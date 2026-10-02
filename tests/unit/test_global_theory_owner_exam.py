"""Independent exam safety/usability tests using wholly original PDF fixtures."""
import copy
import hashlib
import json
import math
import tempfile
import unittest
from pathlib import Path

from tutor_framework.domains.music.global_theory.exam import ExamStore, PurposeGrant


def original_pdf(text="Original synthetic music exercise"):
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = b"BT /F1 12 Tf 60 700 Td (" + escaped.encode("ascii") + b") Tj ET"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    blob = b"%PDF-1.4\n"
    offsets = [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(blob))
        blob += str(number).encode() + b" 0 obj\n" + obj + b"\nendobj\n"
    xref = len(blob)
    blob += b"xref\n0 6\n0000000000 65535 f \n"
    blob += b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:])
    return blob + f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()


def resource(resource_id="synthetic-owner-q", syllabus="synthetic-reviewed-v1", **changes):
    result = {
        "resource_id": resource_id, "board": "ABRSM", "grade": 1,
        "year": 2020, "paper": "owner-original", "language": "en",
        "syllabus_id": syllabus, "sha256": hashlib.sha256(original_pdf()).hexdigest(),
        "rights": "independently_authored_exercise", "resource_type": "system_created_exercise",
        "source_url": "https://example.test/original-synthetic-paper",
        "document_verified": True, "synthetic": True,
    }
    result.update(changes)
    return result


def parsed_paper():
    return {
        "page_map": [{"pdf_page_index": 0, "printed_label": "1", "width": 612, "height": 792}],
        "questions": [{
            "original_number": "1", "stem": "Choose the UK name for an eighth note.",
            "instructions": "Choose one option.", "pages": [0], "marks": 1,
            "response_type": "single_select", "concept_ids": ["rhythm.duration"],
            "options": [
                {"id": "A", "text": "Quaver", "is_correct": True, "explanation": "OWNER-ANSWER-SECRET"},
                {"id": "B", "text": "Crotchet", "is_correct": False},
            ],
            "regions": [{"page": 0, "bbox": [0.1, 0.1, 0.8, 0.3], "kind": "question",
                         "metadata": {"answer": "OWNER-ANSWER-SECRET"}}],
        }],
    }


class OwnerExamAcceptance(unittest.TestCase):
    def setup_store(self, resources=None, **kwargs):
        resources = resources or [resource()]
        store = ExamStore({r["resource_id"]: r for r in resources}, tenant_id="owner-test", **kwargs)
        grant = PurposeGrant("owner-fixture-grant", tuple(r["resource_id"] for r in resources),
                             "internal_evaluation", "owner-test", True)
        return store, grant

    def ingest(self, store, grant, resource_id="synthetic-owner-q", payload=None):
        return store.ingest(resource_id, original_pdf(), grant,
                            mineru_adapter=lambda _: copy.deepcopy(payload or parsed_paper()))

    def test_student_views_keep_options_without_hidden_answers(self):
        store, grant = self.setup_store()
        paper = self.ingest(store, grant)
        result = store.tutor(paper["questions"][0]["question_id"], "hint")
        self.assertEqual(len(result["question"].get("options", [])), 2)
        self.assertNotIn("OWNER-ANSWER-SECRET", json.dumps(result))
        self.assertNotIn("is_correct", json.dumps(result))

    def test_student_views_keep_source_coordinates(self):
        store, grant = self.setup_store()
        paper = self.ingest(store, grant)
        result = store.tutor(paper["questions"][0]["question_id"], "hint")
        regions = result["question"].get("regions", [])
        self.assertTrue(regions, "A score-based question needs its source regions to remain usable")
        self.assertEqual(regions[0]["bbox"], [0.1, 0.1, 0.8, 0.3])
        self.assertNotIn("OWNER-ANSWER-SECRET", json.dumps(regions))

    def test_ai_source_cannot_be_promoted_to_official_by_matching_question_id(self):
        store, grant = self.setup_store()
        paper = self.ingest(store, grant)
        qid = paper["questions"][0]["question_id"]
        store.add_layer(qid, "ai_derived_answer", "Quaver", source_id="model-generated")
        with self.assertRaises((ValueError, PermissionError)):
            store.add_layer(qid, "official_answer", "Quaver", source_id="model-generated",
                            source_paper_revision_id=paper["paper_revision_id"])

    def test_question_resource_is_not_its_own_official_answer_document(self):
        store, grant = self.setup_store()
        paper = self.ingest(store, grant)
        with self.assertRaises((ValueError, PermissionError)):
            store.add_layer(paper["questions"][0]["question_id"], "official_answer", "Quaver",
                            source_id="synthetic-owner-q", source_paper_revision_id=paper["paper_revision_id"])

    def test_active_exam_cannot_be_bypassed_by_switching_to_worked_mode(self):
        store, grant = self.setup_store()
        paper = self.ingest(store, grant)
        qid = paper["questions"][0]["question_id"]
        store.add_layer(qid, "ai_derived_answer", "Quaver", source_id="model-generated")
        store.tutor(qid, "exam_simulation", session_id="exam-one")
        with self.assertRaises((ValueError, PermissionError)):
            store.tutor(qid, "worked", confirmed_question_id=qid)
        finished = store.finish_exam("exam-one", exit_confirmed=True)
        self.assertEqual(finished.get("answer"), "Quaver")

    def test_text_is_not_exam_exit_consent(self):
        store, grant = self.setup_store()
        paper = self.ingest(store, grant)
        qid = paper["questions"][0]["question_id"]
        store.tutor(qid, "exam_simulation", session_id="exam-one")
        with self.assertRaises((ValueError, TypeError)):
            store.finish_exam("exam-one", exit_confirmed="no")

    def test_returned_records_cannot_mutate_internal_verification(self):
        store, grant = self.setup_store()
        paper = self.ingest(store, grant)
        paper["flags"]["musically_verified"] = True
        paper["questions"][0]["stem"] = "CHANGED OUTSIDE STORE"
        reread = self.ingest(store, grant)
        self.assertFalse(reread["flags"]["musically_verified"])
        self.assertNotEqual(reread["questions"][0]["stem"], "CHANGED OUTSIDE STORE")

    def test_syllabus_bindings_do_not_alias_the_same_pdf_revision(self):
        old = resource()
        new = resource("synthetic-owner-q-v2", "synthetic-reviewed-v2")
        store, grant = self.setup_store([old, new])
        self.ingest(store, grant)
        newer = self.ingest(store, grant, "synthetic-owner-q-v2")
        self.assertEqual(newer["identity"]["syllabus_id"], "synthetic-reviewed-v2")
        self.assertEqual(len(store.retrieve(syllabus_id="synthetic-reviewed-v1")), 1)
        self.assertEqual(len(store.retrieve(syllabus_id="synthetic-reviewed-v2")), 1)

    def test_untrusted_catalogue_labels_cannot_escape_storage_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            allowed = root / "allowed"
            bad = resource(board="../../escaped")
            store, grant = self.setup_store([bad], storage_root=allowed)
            try:
                self.ingest(store, grant)
            except (ValueError, PermissionError):
                pass
            self.assertTrue(all(path.is_relative_to(allowed) for path in root.rglob("original.pdf")))

    def test_nonfinite_marks_are_rejected(self):
        for marks in (math.nan, math.inf):
            with self.subTest(marks=marks):
                store, grant = self.setup_store()
                payload = parsed_paper()
                payload["questions"][0]["marks"] = marks
                with self.assertRaises(ValueError):
                    self.ingest(store, grant, payload=payload)

    def test_question_cannot_be_its_own_parent(self):
        store, grant = self.setup_store()
        payload = parsed_paper()
        payload["questions"][0]["parent_number"] = "1"
        with self.assertRaises(ValueError):
            self.ingest(store, grant, payload=payload)

    def test_original_source_url_is_retained(self):
        store, grant = self.setup_store()
        paper = self.ingest(store, grant)
        source_url = paper.get("source_url") or paper.get("original_source_url")
        self.assertEqual(source_url, resource()["source_url"])

    def test_check_mode_provides_feedback_not_only_an_answer(self):
        store, grant = self.setup_store()
        paper = self.ingest(store, grant)
        qid = paper["questions"][0]["question_id"]
        store.add_layer(qid, "ai_derived_answer", "Quaver", source_id="model-generated")
        result = store.tutor(qid, "check", confirmed_question_id=qid, attempt="Crotchet")
        self.assertTrue(result.get("feedback"), "Checking requires feedback on the learner attempt")
        self.assertEqual(result["answer_origin"], "ai_derived_answer")
        self.assertTrue(result["practice_feedback_only"])

    def test_grant_flags_are_real_booleans(self):
        with self.assertRaises((ValueError, TypeError)):
            PurposeGrant("g", ("r",), "private_study", "owner-test", "yes")


if __name__ == "__main__":
    unittest.main()
