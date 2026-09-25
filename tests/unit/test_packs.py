import json
import unittest
from pathlib import Path

from tutor_framework.packs.manifest import (
    OccupationPackManifest,
    load_manifest,
    validate_manifest,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
FAMILY_DIR = REPO_ROOT / "packs" / "families"
COMMON_DIR = REPO_ROOT / "packs" / "common"


class PackContractTests(unittest.TestCase):
    def test_manifest_round_trip_and_validation(self):
        manifest = OccupationPackManifest(
            pack_id="example",
            version="0.1.0",
            family="example",
            display_name="Example pack",
            occupations=("example-role",),
            capabilities=("documents",),
            supported_tasks=("draft",),
            safety_notes=("Draft only.",),
        )
        self.assertEqual(
            OccupationPackManifest.from_dict(manifest.to_dict()),
            manifest,
        )
        self.assertTrue(validate_manifest(manifest).valid)

    def test_all_guide_groups_are_covered_once_by_twelve_family_manifests(self):
        manifests = [load_manifest(path) for path in sorted(FAMILY_DIR.glob("*.json"))]
        self.assertEqual(len(manifests), 12)
        occupations = [occupation for item in manifests for occupation in item.occupations]
        self.assertEqual(len(occupations), 27)
        self.assertEqual(len(set(occupations)), 27)
        self.assertTrue(all(validate_manifest(item).valid for item in manifests))

    def test_common_pack_set_is_complete_and_draft_only(self):
        expected = {
            "document-assistant",
            "spreadsheet-assistant",
            "photo-checklist",
            "voice-notes",
            "sop-tutor",
            "customer-conversation-practice",
            "source-backed-research",
        }
        files = {path.stem for path in COMMON_DIR.glob("*.json")}
        self.assertEqual(files, expected)
        for path in sorted(COMMON_DIR.glob("*.json")):
            with self.subTest(path=path.name):
                raw = json.loads(path.read_text())
                self.assertFalse(raw["external_writes"])
                self.assertEqual(raw["execution_mode"], "draft_only")

    def test_template_exposes_public_authoring_fields(self):
        template = json.loads(
            (REPO_ROOT / "packs" / "template" / "manifest.template.json").read_text()
        )
        for key in (
            "schema_version",
            "pack_id",
            "version",
            "family",
            "occupations",
            "capabilities",
            "safety_notes",
            "external_writes",
            "execution_mode",
        ):
            self.assertIn(key, template)

    def test_invalid_manifest_is_rejected(self):
        payload = {
            "schema_version": "1.0",
            "pack_id": "bad",
            "version": "0.1.0",
            "family": "bad",
            "display_name": "Bad",
            "occupations": [],
            "capabilities": [],
            "supported_tasks": [],
            "safety_notes": [],
            "external_writes": True,
            "execution_mode": "autonomous",
        }
        with self.assertRaises(ValueError):
            OccupationPackManifest.from_dict(payload)


if __name__ == "__main__":
    unittest.main()
