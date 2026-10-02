"""Research benchmark execution at the routing-contract layer only.

The 50 research examples need teacher adjudication for musical answer quality.
These assertions test that each case can enter the new router without media,
privacy or onboarding side effects; they do not claim 50/50 expert answers.
"""
import json
import unittest
from pathlib import Path

from tutor_framework.domains.music.global_theory import LearnerContext, route


RESEARCH = Path(__file__).resolve().parents[2] / "docs/research/2026-10-01-global-music-theory/08-BENCHMARK-AND-EVALUATION.json"


@unittest.skipUnless(RESEARCH.is_file(), "excluded local research benchmark unavailable")
class ResearchRoutingContracts(unittest.TestCase):
    def test_all_fifty_cases_enforce_routing_and_media_invariants(self):
        cases = json.loads(RESEARCH.read_text(encoding="utf-8"))["cases"]
        self.assertEqual(len(cases), 50)
        for case in cases:
            with self.subTest(case=case["case_id"]):
                result = route(case["user_question"], LearnerContext(text_only=True, no_save=True))
                self.assertIn(result["mode"], {"direct", "guided"})
                self.assertLessEqual(len(result["questions"]), 5)
                self.assertNotIn("video", result["deliverables"])
                self.assertNotIn("audio", result["deliverables"])
                self.assertNotIn("grade_equivalence", result)
                if result["mode"] == "direct":
                    self.assertEqual(result["questions"], [])
                    self.assertEqual(result["deliverables"], ["text"])


if __name__ == "__main__":
    unittest.main()
