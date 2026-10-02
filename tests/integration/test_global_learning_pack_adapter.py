"""Global entry reuses the staged Learning Pack service and source identities."""
import importlib.util
import json
import unittest
from pathlib import Path

from tutor_framework.domains.music.global_theory import LearnerContext
from tutor_framework.domains.music.global_theory.learning import build_learning_pack


@unittest.skipUnless(importlib.util.find_spec("pymupdf") or importlib.util.find_spec("fitz"),
                     "PyMuPDF optional; run with existing media interpreter")
class GlobalLearningPackAdapter(unittest.TestCase):
    def setUp(self):
        from tests.integration.test_learning_pack_pipeline import LearningPackPipeline
        self.fixture = LearningPackPipeline()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def test_no_save_build_is_memory_only_and_answer_filtered(self):
        fixture = self.fixture
        context = LearnerContext(no_save=True, desired_deliverables=("notes",))
        result = build_learning_pack(fixture.dossier, fixture.brief(materials=["notes"]), fixture.content(), context)
        self.assertEqual(result["state"], "session_only")
        self.assertFalse(result["persisted"])
        self.assertNotIn("SECRET ANSWER", result["notes"])
        self.assertFalse((fixture.root / "global-output").exists())
        with self.assertRaises(ValueError):
            build_learning_pack(fixture.dossier, fixture.brief(materials=["notes"]), fixture.content(),
                                context, fixture.root / "global-output")

    def test_text_only_does_not_export_an_annotated_score(self):
        fixture = self.fixture
        target = fixture.root / "forbidden-score"
        with self.assertRaises(ValueError):
            build_learning_pack(fixture.dossier, fixture.brief(materials=["notes", "annotated_score"]),
                                fixture.content(), LearnerContext(text_only=True), target)
        self.assertFalse(target.exists())

    @unittest.skipUnless(importlib.util.find_spec("verovio"), "local Verovio engraving required")
    def test_complete_pilot_requests_score_media_without_text_only_conflict(self):
        from tools.global_music_theory_pilot import generate
        destination = self.fixture.root / "complete-global-pilot"
        result = generate(destination)
        self.assertEqual(result["state"], "original_engraved_pilot_for_review")
        self.assertFalse(result["real_abrsm_paper_parsed"])
        self.assertTrue(list(destination.rglob("annotated-score.pdf")))
        self.assertTrue((destination / "original-score.musicxml").is_file())
        self.assertFalse(list(destination.rglob("*.mp4")))

    def test_requested_score_uses_existing_manifest_and_real_pdf_annotation(self):
        fixture = self.fixture
        output = fixture.root / "global-output"
        context = LearnerContext(desired_deliverables=("notes", "annotated_score"))
        result = build_learning_pack(fixture.dossier,
                                     fixture.brief(materials=["notes", "annotated_score"]),
                                     fixture.content(), context, output)
        directory = Path(result["directory"])
        self.assertTrue((directory / "annotated-score.pdf").is_file())
        self.assertFalse((directory / "lesson.mp4").exists())
        manifest = json.loads((directory / "learning-pack.json").read_text())
        self.assertEqual(manifest["schema_version"], "1.0")
        self.assertFalse(manifest["video_generated"])


if __name__ == "__main__":
    unittest.main()
