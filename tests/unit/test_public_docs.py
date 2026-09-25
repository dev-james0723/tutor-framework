import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class PublicDocumentationTests(unittest.TestCase):
    def test_required_public_documents_exist(self):
        for relative in (
            "README.md",
            "docs/ARCHITECTURE.md",
            "docs/CONTRIBUTING.md",
            "docs/SECURITY.md",
            "docs/LICENSES.md",
            "docs/THIRD_PARTY_SKILL_AUDIT.md",
            "docs/EXECUTION-STATES.md",
            "docs/skill-adoption-registry.json",
        ):
            with self.subTest(relative=relative):
                self.assertTrue((ROOT / relative).is_file())

    def test_skill_registry_is_explicit_about_candidate_status(self):
        registry = json.loads((ROOT / "docs/skill-adoption-registry.json").read_text())
        self.assertGreaterEqual(len(registry["skills"]), 7)
        allowed = {"research_candidate", "candidate", "approved", "not_adopted"}
        for item in registry["skills"]:
            self.assertIn(item["status"], allowed)
            self.assertIn("source", item)
            self.assertIn("external_execution", item)
            self.assertFalse(item["external_execution"])

    def test_docs_distinguish_validation_from_external_execution(self):
        text = (ROOT / "docs/EXECUTION-STATES.md").read_text()
        self.assertIn("local validation", text)
        self.assertIn("candidate integration", text)
        self.assertIn("external execution", text)
        self.assertIn("not equivalent", text)


if __name__ == "__main__":
    unittest.main()
