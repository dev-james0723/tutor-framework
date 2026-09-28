import json
import unittest
from pathlib import Path

from tutor_framework.domains.music import (
    AudioNoteEvent,
    AudioRegionKind,
    AudioTranscriptionResult,
    EvidenceConfidence,
    PieceIdentificationCandidate,
    PieceIdentificationMethod,
    PieceIdentificationResult,
    QuantizedAudioNote,
    ScoreAlignmentResult,
    ScoreTimeAnchor,
    TimedAudioRegion,
    analyze_lecture_audio,
    read_musicxml,
    reconstruct_score_from_quantized,
)


SCORE = """<?xml version="1.0"?>
<score-partwise version="4.0">
  <work><work-title>Synthetic</work-title></work>
  <part-list><score-part id="P1"><part-name>Piano</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1">
      <attributes><divisions>1</divisions></attributes>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration></note>
    </measure>
  </part>
</score-partwise>
"""


def regions(audio_ref):
    return (
        TimedAudioRegion("speech-1", 0.0, 4.0, AudioRegionKind.SPEECH, 0.99, audio_ref),
        TimedAudioRegion("music-1", 4.0, 8.0, AudioRegionKind.MUSIC, 0.95, audio_ref),
    )


class Segmenter:
    def __init__(self, items=None):
        self.items = items

    def segment(self, audio_ref):
        return self.items if self.items is not None else regions(audio_ref)


class BrokenSegmenter:
    def segment(self, audio_ref):
        raise RuntimeError("backend unavailable")


class MusicAudioTests(unittest.TestCase):
    def test_regions_preserve_music_as_timestamped_evidence(self):
        audio_ref = "audio://synthetic-lecture"
        analysis = analyze_lecture_audio(
            audio_ref,
            artifact_id="lecture-1",
            segmenter=Segmenter(),
        )
        self.assertEqual([r.kind.value for r in analysis.regions], ["speech", "music"])
        self.assertEqual(
            analysis.regions[1].source_locator,
            "audio://synthetic-lecture#t=4.000,8.000",
        )
        self.assertEqual(len(analysis.music_regions), 1)
        self.assertEqual(
            analysis.music_regions[0].review_state,
            EvidenceConfidence.REQUIRES_HUMAN_REVIEW,
        )

    def test_segmentation_failure_is_fail_closed(self):
        analysis = analyze_lecture_audio(
            "audio://broken",
            artifact_id="lecture-broken",
            segmenter=BrokenSegmenter(),
        )
        self.assertEqual(analysis.regions, ())
        self.assertIn("RuntimeError", analysis.unresolved_gaps[0])

    def test_unknown_piece_identification_runs_before_amt(self):
        events = []

        class Identifier:
            def identify(self, audio_ref, region, context=None):
                events.append("identify")
                return PieceIdentificationResult(
                    True,
                    candidates=(
                        PieceIdentificationCandidate(
                            title="Synthetic Lecture Piece",
                            composer="Test Composer",
                            movement="I",
                            confidence=0.84,
                            provider="synthetic-identifier",
                            method=PieceIdentificationMethod.SEMANTIC,
                        ),
                    ),
                    confidence=EvidenceConfidence.PROBABLE,
                    backend="synthetic-identifier",
                )

        class Transcriber:
            def transcribe(self, audio_ref, region):
                events.append("transcribe")
                return AudioTranscriptionResult(
                    True,
                    notes=(AudioNoteEvent(60, 4.0, 5.0, 0.90),),
                    confidence=EvidenceConfidence.PROBABLE,
                    backend="synthetic-amt",
                )

        analysis = analyze_lecture_audio(
            "audio://unknown",
            artifact_id="lecture-unknown",
            segmenter=Segmenter(regions("audio://unknown")),
            context={"course": "synthetic"},
            piece_identifier=Identifier(),
            transcriber=Transcriber(),
        )
        music = analysis.music_regions[0]
        self.assertEqual(events, ["identify", "transcribe"])
        self.assertTrue(music.piece_identification.available)
        self.assertEqual(
            music.piece_identification.candidates[0].method,
            PieceIdentificationMethod.SEMANTIC,
        )
        self.assertNotEqual(
            music.piece_identification.confidence,
            EvidenceConfidence.CONFIRMED,
        )

    def test_semantic_identifier_cannot_claim_confirmation_by_itself(self):
        with self.assertRaises(ValueError):
            PieceIdentificationResult(
                True,
                candidates=(
                    PieceIdentificationCandidate(
                        title="Synthetic",
                        confidence=0.99,
                        provider="semantic-fixture",
                        method=PieceIdentificationMethod.SEMANTIC,
                    ),
                ),
                confidence=EvidenceConfidence.CONFIRMED,
            )

    def test_known_score_alignment_runs_before_transcription_and_blocks_reconstruction(self):
        events = []
        score = read_musicxml(SCORE, artifact_id="known-score")

        class Identifier:
            def identify(self, audio_ref, region, context=None):
                events.append("identify")
                return PieceIdentificationResult(
                    False,
                    reason="should not run when known score is supplied",
                )

        class Aligner:
            def align(self, audio_ref, region, known_score):
                events.append("align")
                return ScoreAlignmentResult(
                    True,
                    anchors=(ScoreTimeAnchor(4.0, "1", 1.0, 0.94),),
                    confidence=EvidenceConfidence.PROBABLE,
                    backend="synthetic-aligner",
                )

        class Transcriber:
            def transcribe(self, audio_ref, region):
                events.append("transcribe")
                return AudioTranscriptionResult(
                    True,
                    notes=(AudioNoteEvent(60, 4.0, 5.0, 0.90),),
                    confidence=EvidenceConfidence.PROBABLE,
                    backend="synthetic-amt",
                )

        analysis = analyze_lecture_audio(
            "audio://known",
            artifact_id="lecture-known",
            segmenter=Segmenter(regions("audio://known")),
            piece_identifier=Identifier(),
            known_score=score,
            aligner=Aligner(),
            transcriber=Transcriber(),
        )
        music = analysis.music_regions[0]
        self.assertEqual(events, ["align", "transcribe"])
        self.assertTrue(music.alignment.available)
        self.assertIsNone(music.provisional_score)

    def test_quantized_audio_can_only_create_provisional_score(self):
        high = AudioNoteEvent(60, 10.0, 10.5, 0.92)
        low = AudioNoteEvent(64, 10.5, 11.0, 0.62)
        transcription = AudioTranscriptionResult(
            True,
            notes=(high, low),
            quantized_notes=(
                QuantizedAudioNote(high, "1", 1.0, 480),
                QuantizedAudioNote(low, "1", 2.0, 480),
            ),
            confidence=EvidenceConfidence.AMBIGUOUS,
        )
        result = reconstruct_score_from_quantized(
            transcription,
            artifact_id="audio-provisional",
        )
        self.assertTrue(result.available)
        self.assertEqual(result.score.note_count, 2)
        self.assertEqual(result.score.measures[0].notes[0].pitch.step, "C")
        self.assertEqual(result.score.measures[0].notes[1].pitch.step, "E")
        self.assertEqual(
            result.confidence,
            EvidenceConfidence.REQUIRES_HUMAN_REVIEW,
        )
        self.assertNotEqual(result.confidence, EvidenceConfidence.CONFIRMED)

    def test_unquantized_note_events_do_not_invent_barlines(self):
        transcription = AudioTranscriptionResult(
            True,
            notes=(AudioNoteEvent(60, 0.0, 1.0, 0.98),),
            confidence=EvidenceConfidence.PROBABLE,
        )
        result = reconstruct_score_from_quantized(
            transcription,
            artifact_id="no-bars",
        )
        self.assertFalse(result.available)
        self.assertIsNone(result.score)
        self.assertIn("quantized", result.reason)

    def test_public_eval_has_lecture_audio_case(self):
        path = Path(__file__).resolve().parents[2] / "evals" / "music" / "synthetic_cases.json"
        cases = json.loads(path.read_text())
        lecture = next(case for case in cases if case["case_id"] == "public-synthetic-lecture-audio")
        self.assertTrue(lecture["synthetic"])
        self.assertEqual(lecture["expected"]["music_regions"], 1)
        self.assertEqual(lecture["expected"]["reconstruction_status"], "requires_human_review")

    def test_semantic_only_identity_keeps_region_in_human_review(self):
        class Identifier:
            def identify(self, audio_ref, region, context=None):
                return PieceIdentificationResult(
                    True,
                    candidates=(
                        PieceIdentificationCandidate(
                            title="Wrong but plausible",
                            confidence=0.97,
                            provider="semantic-provider",
                            method=PieceIdentificationMethod.SEMANTIC,
                        ),
                    ),
                    confidence=EvidenceConfidence.PROBABLE,
                    backend="semantic-provider",
                )

        class Transcriber:
            def transcribe(self, audio_ref, region):
                return AudioTranscriptionResult(
                    True,
                    notes=(AudioNoteEvent(60, 4.0, 5.0, 0.95),),
                    confidence=EvidenceConfidence.PROBABLE,
                    backend="synthetic-amt",
                )

        analysis = analyze_lecture_audio(
            "audio://semantic-only",
            artifact_id="semantic-only",
            segmenter=Segmenter(regions("audio://semantic-only")),
            piece_identifier=Identifier(),
            transcriber=Transcriber(),
        )
        music = analysis.music_regions[0]
        self.assertFalse(music.piece_identification.promotable)
        self.assertEqual(
            music.review_state,
            EvidenceConfidence.REQUIRES_HUMAN_REVIEW,
        )

    def test_weak_alignment_with_anchors_does_not_block_provisional_reconstruction(self):
        score = read_musicxml(SCORE, artifact_id="known-score")
        note = AudioNoteEvent(60, 4.0, 5.0, 0.95)

        class Aligner:
            def align(self, audio_ref, region, known_score):
                return ScoreAlignmentResult(
                    True,
                    anchors=(ScoreTimeAnchor(4.0, "1", 1.0, 0.90),),
                    confidence=EvidenceConfidence.PROBABLE,
                    backend="synthetic-aligner",
                    match_score=0.60,
                    promotion_threshold=0.65,
                    corroborated=True,
                )

        class Transcriber:
            def transcribe(self, audio_ref, region):
                return AudioTranscriptionResult(
                    True,
                    notes=(note,),
                    quantized_notes=(QuantizedAudioNote(note, "1", 1.0, 480),),
                    confidence=EvidenceConfidence.PROBABLE,
                    backend="synthetic-amt",
                )

        analysis = analyze_lecture_audio(
            "audio://weak-align",
            artifact_id="weak-align",
            segmenter=Segmenter(regions("audio://weak-align")),
            known_score=score,
            aligner=Aligner(),
            transcriber=Transcriber(),
        )
        music = analysis.music_regions[0]
        self.assertTrue(music.alignment.available)
        self.assertFalse(music.alignment.promotable)
        self.assertIsNotNone(music.provisional_score)
        self.assertEqual(
            music.review_state,
            EvidenceConfidence.REQUIRES_HUMAN_REVIEW,
        )

    def test_overlong_music_region_is_review_gated_as_possible_merge(self):
        audio_ref = "audio://long-region"
        long_regions = (
            TimedAudioRegion(
                "music-long",
                0.0,
                64.0,
                AudioRegionKind.MUSIC,
                0.98,
                audio_ref,
            ),
        )

        class Transcriber:
            def transcribe(self, audio_ref, region):
                return AudioTranscriptionResult(
                    True,
                    notes=(AudioNoteEvent(60, 1.0, 2.0, 0.95),),
                    confidence=EvidenceConfidence.PROBABLE,
                    backend="synthetic-amt",
                )

        analysis = analyze_lecture_audio(
            audio_ref,
            artifact_id="long-region",
            segmenter=Segmenter(long_regions),
            transcriber=Transcriber(),
            max_music_region_seconds=45.0,
        )
        music = analysis.music_regions[0]
        self.assertTrue(
            any("possible merged examples" in item for item in music.unresolved)
        )
        self.assertEqual(
            music.review_state,
            EvidenceConfidence.REQUIRES_HUMAN_REVIEW,
        )


if __name__ == "__main__":
    unittest.main()
