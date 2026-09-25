import json
import unittest
from pathlib import Path

from tutor_framework.release_gate import run_release_gate


ROOT = Path(__file__).resolve().parents[2]


class ReleaseGateTests(unittest.TestCase):
    def test_release_gate_has_no_findings(self):
        report = run_release_gate(ROOT)
        self.assertEqual(report, ())

    def test_multilingual_fixture_covers_three_locales(self):
        fixture = json.loads(
            (ROOT / "evals" / "fixtures" / "multilingual.json").read_text()
        )
        self.assertEqual({case["locale"] for case in fixture}, {"en-US", "zh-Hant-HK", "es-ES"})


if __name__ == "__main__":
    unittest.main()
