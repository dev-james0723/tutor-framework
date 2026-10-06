import json
import tempfile
import unittest
from pathlib import Path

from tutor_framework.domains.music.lesson.symbolic import parse_score
from tutor_framework.domains.music.theory_pedagogy import (
    TranscriptSegment,
    generate_theory_contrast,
    map_caplin_manifest,
    read_score_source,
    write_contrast_package,
)
from tutor_framework.domains.music.theory_pedagogy.cli import doctor, generate_example


class TheoryPedagogyArtifactTests(unittest.TestCase):
    def test_tonicization_modulation_contrast_is_real_symbolic_notation(self):
        contrast = generate_theory_contrast("modulation to V")
        self.assertEqual(contrast.concept, "tonicization-vs-modulation")
        self.assertEqual(len(contrast.variants), 2)
        revisions = set()
        for variant in contrast.variants:
            score = parse_score(variant.musicxml)
            self.assertGreater(len(score.events), 0)
            self.assertIn("review", variant.status)
            revisions.add(score.revision)
        self.assertEqual(len(revisions), 2)

    def test_contrast_package_keeps_generated_material_out_of_course_evidence(self):
        contrast = generate_theory_contrast("triad inversions")
        with tempfile.TemporaryDirectory() as root:
            destination = Path(root) / "pack"
            manifest = write_contrast_package(contrast, destination)
            self.assertFalse(manifest["course_evidence"])
            self.assertEqual(
                manifest["authority"],
                "assistant_generated_pedagogical_material",
            )
            self.assertTrue((destination / "manifest.json").is_file())
            for item in manifest["variants"]:
                self.assertTrue(Path(item["musicxml"]).is_file())

    def test_direct_musicxml_uses_symbolic_reader_without_omr(self):
        contrast = generate_theory_contrast("cadence")
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "example.musicxml"
            source.write_text(contrast.variants[0].musicxml, encoding="utf-8")
            result = read_score_source(source, source_id="score-1")
            self.assertTrue(result.symbolic_available)
            self.assertEqual(result.input_kind, "symbolic")
            self.assertFalse(result.review_required)
            self.assertGreater(result.observations["event_count"], 0)

    def test_printed_score_without_omr_fails_closed(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "scan.pdf"
            source.write_bytes(b"%PDF-1.7\\nsynthetic")
            result = read_score_source(source, source_id="scan-1")
            self.assertEqual(result.state, "review_required")
            self.assertTrue(result.review_required)
            self.assertIn("adapter", result.reason)

    def test_printed_adapter_cannot_skip_omr_verification(self):
        class Adapter:
            def read(self, source, *, source_id, output_dir=None):
                return {
                    "state": "passed",
                    "omr_verified": False,
                    "source_id": source_id,
                }

        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "scan.png"
            source.write_bytes(b"not-real-pixels")
            result = read_score_source(
                source,
                source_id="scan-2",
                adapter=Adapter(),
            )
            self.assertTrue(result.review_required)

    def test_weak_alignment_never_creates_measure_mapping(self):
        manifest = {
            "source": "lecture.wav",
            "known_score": "score.musicxml",
            "music_regions": [
                {
                    "region_id": "music-1",
                    "source_locator": "audio://lecture.wav#t=10.000,20.000",
                    "start_seconds": 10.0,
                    "end_seconds": 20.0,
                    "review_state": "requires_human_review",
                    "piece_identification": {
                        "promotion_allowed": False,
                        "candidate": {
                            "composer": "Example",
                            "title": "Plausible work",
                        },
                    },
                    "known_score_alignment": {
                        "available": True,
                        "promotion_allowed": False,
                        "anchors": [
                            {"measure_number": "12", "beat": 1.0},
                            {"measure_number": "15", "beat": 3.0},
                        ],
                    },
                    "transcription": {
                        "available": True,
                        "backend": "basic_pitch",
                    },
                }
            ],
        }
        mapped = map_caplin_manifest(manifest)
        item = mapped["mappings"][0]
        self.assertEqual(item["mapping_status"], "unresolved")
        self.assertIsNone(item["measure_start"])
        self.assertIsNone(item["piece"])
        self.assertEqual(item["piece_candidate"]["work"], "Plausible work")
        self.assertTrue(item["review_required"])

    def test_promotable_alignment_maps_measures_and_nearby_transcript(self):
        manifest = {
            "source": "lecture.wav",
            "known_score": "score.musicxml",
            "music_regions": [
                {
                    "region_id": "music-2",
                    "source_locator": "audio://lecture.wav#t=30.000,40.000",
                    "start_seconds": 30.0,
                    "end_seconds": 40.0,
                    "review_state": "probable",
                    "piece_identification": {
                        "promotion_allowed": True,
                        "candidate": {
                            "composer": "Test Composer",
                            "title": "Test Work",
                            "movement": "I",
                        },
                    },
                    "known_score_alignment": {
                        "available": True,
                        "promotion_allowed": True,
                        "anchors": [
                            {"measure_number": "21", "beat": 1.0},
                            {"measure_number": "24", "beat": 4.0},
                        ],
                    },
                }
            ],
        }
        segment = TranscriptSegment(
            "seg-1",
            24.0,
            29.5,
            "Listen for how the dominant becomes a local tonic.",
            "transcript.md#t=24.000,29.500",
        )
        mapped = map_caplin_manifest(manifest, transcript_segments=(segment,))
        item = mapped["mappings"][0]
        self.assertEqual(item["mapping_status"], "probable")
        self.assertEqual((item["measure_start"], item["measure_end"]), ("21", "24"))
        self.assertEqual(item["piece"]["work"], "Test Work")
        self.assertEqual(item["transcript_segment"]["segment_id"], "seg-1")
        self.assertFalse(item["review_required"])

    def test_mapping_policy_is_explicit(self):
        mapped = map_caplin_manifest({"source": "lecture.wav", "music_regions": []})
        self.assertFalse(mapped["policy"]["semantic_identity_is_verified"])
        self.assertFalse(mapped["policy"]["amt_is_verified_score"])
        self.assertFalse(mapped["policy"]["weak_alignment_creates_measure_mapping"])

    def test_shared_cli_doctor_keeps_privacy_defaults(self):
        result = doctor()
        self.assertTrue(result["framework"]["available"])
        self.assertFalse(result["policy"]["external_audio_transfer_default"])
        self.assertTrue(result["policy"]["printed_score_requires_omr_review"])
        self.assertFalse(result["policy"]["generated_examples_are_course_evidence"])

    def test_shared_cli_generates_a_real_package_without_local_media_tools(self):
        with tempfile.TemporaryDirectory() as root:
            destination = Path(root) / "cli-pack"
            result = generate_example("triad inversions", destination, render=False)
            self.assertEqual(result["state"], "generated_review_required")
            self.assertTrue((destination / "manifest.json").is_file())
            self.assertEqual(len(result["manifest"]["variants"]), 3)
            self.assertTrue(
                all(Path(item["musicxml"]).is_file() for item in result["manifest"]["variants"])
            )


if __name__ == "__main__":
    unittest.main()