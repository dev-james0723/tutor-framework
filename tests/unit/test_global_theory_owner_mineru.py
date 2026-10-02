"""Structural replay tests shaped like real MinerU layout.json, not plain text."""
import copy
import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from tutor_framework.domains.music.global_theory.mineru import (
    normalize_mineru_layout, load_existing_mineru_result, mineru_configuration,
)
from tests.unit.test_global_theory_owner_exam import original_pdf


def layout():
    return {"_backend": "vlm", "_version_name": "fixture-v1", "pdf_info": [{
        "page_idx": 0, "page_size": [612, 792], "discarded_blocks": [],
        "preproc_blocks": [],
        "para_blocks": [
            {"type": "text", "bbox": [61.2, 79.2, 550.8, 158.4], "index": 0,
             "lines": [{"spans": [{"type": "text", "content": "1. Identify the written note. (1 mark)"}]}]},
            {"type": "image", "bbox": [61.2, 158.4, 550.8, 316.8], "index": 1,
             "blocks": [{"type": "image_body", "bbox": [61.2, 158.4, 550.8, 316.8],
                         "lines": [{"spans": [{"type": "image", "image_path": "images/score.png"}]}]}]},
            {"type": "text", "bbox": [61.2, 320, 550.8, 370], "index": 2,
             "lines": [{"spans": [{"type": "text", "content": "A. C4"}]},
                       {"spans": [{"type": "text", "content": "B. D4"}]}]},
        ],
    }]}


class MinerUStructureAcceptance(unittest.TestCase):
    def test_actual_layout_shape_preserves_pages_regions_and_images(self):
        result = normalize_mineru_layout(layout())
        self.assertEqual(len(result["page_map"]), 1)
        self.assertEqual(result["page_map"][0]["pdf_page_index"], 0)
        self.assertEqual(result["page_map"][0]["width"], 612)
        self.assertEqual(result["page_map"][0]["height"], 792)
        self.assertTrue(result["blocks"])
        image = next(block for block in result["blocks"] if block.get("image_path"))
        self.assertEqual(image["image_path"], "images/score.png")
        self.assertEqual(image["page"], 0)
        self.assertAlmostEqual(image["bbox"][0], 0.1)
        self.assertFalse(result["flags"]["musically_verified"])
        self.assertFalse(result["flags"]["reviewed_usable"])

    def test_exam_question_candidate_keeps_original_options_and_crop(self):
        result = normalize_mineru_layout(layout(), extract_questions=True)
        self.assertEqual(result["questions"][0]["original_number"], "1")
        self.assertEqual(len(result["questions"][0]["options"]), 2)
        self.assertGreaterEqual(len(result["questions"][0]["regions"]), 2)
        self.assertEqual(result["questions"][0]["review_status"], "review_required")

    def test_normalization_never_mutates_source_parser_structure(self):
        source = layout()
        before = copy.deepcopy(source)
        normalize_mineru_layout(source)
        self.assertEqual(source, before)

    def test_missing_dimensions_or_page_discontinuity_is_not_success(self):
        broken = layout()
        broken["pdf_info"][0].pop("page_size")
        with self.assertRaises(ValueError):
            normalize_mineru_layout(broken)
        broken = layout()
        broken["pdf_info"][0]["page_idx"] = 4
        with self.assertRaises(ValueError):
            normalize_mineru_layout(broken)

    def test_plain_text_cannot_pretend_to_be_structured_mineru(self):
        with self.assertRaises((ValueError, TypeError)):
            normalize_mineru_layout({"text": "a flattened paper"})

    def test_unsafe_image_reference_is_rejected(self):
        broken = layout()
        broken["pdf_info"][0]["para_blocks"][1]["blocks"][0]["lines"][0]["spans"][0]["image_path"] = "../../private-key"
        with self.assertRaises(ValueError):
            normalize_mineru_layout(broken)

    def result_directory(self, root: Path, *, unsafe=False):
        pdf = original_pdf()
        (root / "source.pdf").write_bytes(pdf)
        with zipfile.ZipFile(root / "mineru.zip", "w") as archive:
            archive.writestr("layout.json", json.dumps(layout()))
            archive.writestr("images/score.png", b"synthetic region bytes, not claimed as a PNG rendering")
            if unsafe:
                archive.writestr("../escape.txt", "no")
        manifest = {"status": "done", "source": "source.pdf",
                    "mineru": {"api": "https://mineru.net/api/v4", "batch_id": "synthetic-fixture", "model_version": "vlm"},
                    "files": {"pdf": "source.pdf", "result_zip": "mineru.zip"}}
        (root / "manifest.json").write_text(json.dumps(manifest))
        return hashlib.sha256(pdf).hexdigest()

    def test_existing_helper_manifest_replay_is_not_counted_as_new_api_parse(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sha = self.result_directory(root)
            result = load_existing_mineru_result(root, expected_pdf_sha256=sha, extract_questions=True)
            self.assertEqual(result["parser_origin"], "existing_mineru_result_replay")
            self.assertFalse(result["new_api_submission"])
            self.assertEqual(result["source_sha256"], sha)
            self.assertEqual(len(result["questions"]), 1)

    def test_replay_checks_original_bytes_not_only_manifest_done(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.result_directory(root)
            with self.assertRaises(ValueError):
                load_existing_mineru_result(root, expected_pdf_sha256="0" * 64)

    def test_result_zip_cannot_extract_outside_its_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sha = self.result_directory(root, unsafe=True)
            with self.assertRaises(ValueError):
                load_existing_mineru_result(root, expected_pdf_sha256=sha)
            self.assertFalse((root.parent / "escape.txt").exists())

    def test_configuration_discovery_does_not_return_credentials(self):
        result = mineru_configuration()
        self.assertIsInstance(result.get("helper_found"), bool)
        self.assertNotIn("token", result)
        self.assertNotIn("authorization", result)
        self.assertEqual(result.get("new_api_submissions"), 0)


if __name__ == "__main__":
    unittest.main()
