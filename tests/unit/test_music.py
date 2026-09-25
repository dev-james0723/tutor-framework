import json
import unittest
from dataclasses import replace
from pathlib import Path

from tutor_framework.domains.music import (
    OMRResult,
    ScoreIR,
    analyze_score,
    generate_practice,
    read_musicxml,
    read_with_optional_omr,
    teach_score,
    verify_score,
)
from tutor_framework.protocol.models import ClaimStatus


SYNTHETIC_MUSICXML = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <work><work-title>Public Synthetic Scale</work-title></work>
  <part-list><score-part id="P1"><part-name>Piano</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>1</divisions>
        <key><fifths>0</fifths></key>
        <time><beats>4</beats><beat-type>4</beat-type></time>
      </attributes>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><type>quarter</type></note>
      <note><pitch><step>D</step><octave>4</octave></pitch><duration>1</duration><type>quarter</type></note>
    </measure>
    <measure number="2">
      <note><rest/><duration>2</duration><type>half</type></note>
      <note><pitch><step>E</step><alter>1</alter><octave>4</octave></pitch><duration>2</duration><type>half</type></note>
    </measure>
  </part>
</score-partwise>
"""


class MusicSliceTests(unittest.TestCase):
    def test_musicxml_flows_into_score_ir(self):
        score = read_musicxml(SYNTHETIC_MUSICXML, artifact_id="synthetic-score")
        self.assertIsInstance(score, ScoreIR)
        self.assertEqual(score.title, "Public Synthetic Scale")
        self.assertEqual(len(score.measures), 2)
        self.assertEqual(score.note_count, 4)
        self.assertEqual(score.measures[0].notes[0].pitch.step, "C")
        self.assertTrue(score.measures[1].notes[0].rest)
        self.assertEqual(score.measures[1].notes[1].pitch.alter, 1)

    def test_reader_rejects_external_entity_payloads(self):
        hostile = "<!DOCTYPE score-partwise [<!ENTITY xxe SYSTEM 'file:///etc/passwd'>]>" + SYNTHETIC_MUSICXML
        with self.assertRaises(ValueError):
            read_musicxml(hostile)

    def test_verification_and_grounded_analysis(self):
        score = read_musicxml(SYNTHETIC_MUSICXML, artifact_id="synthetic-score")
        verification = verify_score(score)
        self.assertTrue(verification.valid)
        claims = analyze_score(score)
        self.assertGreaterEqual(len(claims), 3)
        self.assertTrue(all(claim.evidence for claim in claims))
        self.assertTrue(all(claim.status.value == "supported" for claim in claims))
        self.assertTrue(all(claim.evidence[0].anchors for claim in claims))

    def test_teaching_and_practice_are_bounded(self):
        score = read_musicxml(SYNTHETIC_MUSICXML, artifact_id="synthetic-score")
        decision = teach_score(score, "Help me practise the opening")
        self.assertIn("C", decision.response)
        self.assertTrue(decision.claims)
        tasks = generate_practice(score, max_tasks=2)
        self.assertEqual(len(tasks), 2)
        self.assertTrue(all(not task.external_write for task in tasks))
        with self.assertRaises(ValueError):
            generate_practice(score, max_tasks=6)

    def test_omr_is_optional_and_fail_closed(self):
        result = read_with_optional_omr("photo://score", omr=None)
        self.assertIsInstance(result, OMRResult)
        self.assertFalse(result.available)
        self.assertIsNone(result.score)

    def test_memory_promotion_requires_confirmation_and_review(self):
        score = read_musicxml(SYNTHETIC_MUSICXML, artifact_id="synthetic-score")
        claim = replace(analyze_score(score)[0], status=ClaimStatus.CONFIRMED)
        from tutor_framework.domains.music import memory_candidate

        self.assertIsNone(memory_candidate(claim, reviewed=False))
        self.assertEqual(memory_candidate(claim, reviewed=True), claim)

    def test_public_synthetic_eval_fixture_is_present(self):
        path = Path(__file__).resolve().parents[2] / "evals" / "music" / "synthetic_cases.json"
        cases = json.loads(path.read_text())
        self.assertGreaterEqual(len(cases), 1)
        self.assertTrue(all(case["synthetic"] for case in cases))
        self.assertEqual(cases[0]["expected"]["measure_count"], 2)


if __name__ == "__main__":
    unittest.main()
