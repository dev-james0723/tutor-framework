"""Map lecture music evidence into Theory Pedagogy retrieval records.

This layer never upgrades semantic identification, AMT, or weak alignment into
verified course evidence. It converts either the shared audio contracts or the
existing Caplin lecture manifest into a conservative retrieval map.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from tutor_framework.domains.music.audio import (
    EvidenceConfidence,
    LectureAudioAnalysis,
)


@dataclass(frozen=True)
class TranscriptSegment:
    segment_id: str
    start_seconds: float
    end_seconds: float
    text: str
    locator: str

    def __post_init__(self) -> None:
        for name in ("segment_id", "text", "locator"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be non-empty text")
        if (
            not isinstance(self.start_seconds, (int, float))
            or isinstance(self.start_seconds, bool)
            or self.start_seconds < 0
        ):
            raise ValueError("start_seconds must be non-negative")
        if (
            not isinstance(self.end_seconds, (int, float))
            or isinstance(self.end_seconds, bool)
            or self.end_seconds <= self.start_seconds
        ):
            raise ValueError("end_seconds must be greater than start_seconds")


def _nearest_segment(
    start: float,
    end: float,
    segments: tuple[TranscriptSegment, ...],
    *,
    preceding_window: float = 60.0,
) -> TranscriptSegment | None:
    overlaps = [
        item
        for item in segments
        if item.start_seconds < end and item.end_seconds > start
    ]
    if overlaps:
        return min(overlaps, key=lambda item: abs(item.start_seconds - start))
    preceding = [
        item
        for item in segments
        if item.end_seconds <= start and start - item.end_seconds <= preceding_window
    ]
    return max(preceding, key=lambda item: item.end_seconds, default=None)


def _identity_from_mapping(value: object) -> dict[str, object] | None:
    if not isinstance(value, Mapping):
        return None
    candidate: Mapping[str, object] | None = None
    raw_candidates = value.get("candidates")
    if isinstance(raw_candidates, (list, tuple)) and raw_candidates:
        first = raw_candidates[0]
        if isinstance(first, Mapping):
            candidate = first
    elif isinstance(value.get("candidate"), Mapping):
        candidate = value["candidate"]
    else:
        candidate = value

    if not candidate:
        return None
    title = candidate.get("title") or candidate.get("work") or candidate.get("piece")
    composer = candidate.get("composer")
    movement = candidate.get("movement")
    if not any(isinstance(x, str) and x.strip() for x in (title, composer, movement)):
        return None
    return {
        "composer": composer if isinstance(composer, str) and composer.strip() else None,
        "work": title if isinstance(title, str) and title.strip() else None,
        "movement": movement if isinstance(movement, str) and movement.strip() else None,
    }


def _collect_measure_values(value: object, found: list[str]) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            lowered = str(key).casefold()
            if lowered in {
                "measure", "measure_number", "measure_label", "start_measure",
                "end_measure", "matched_measure_start", "matched_measure_end",
            } and isinstance(item, (str, int)):
                found.append(str(item))
            else:
                _collect_measure_values(item, found)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _collect_measure_values(item, found)


def _measure_range(value: object) -> tuple[str | None, str | None]:
    values: list[str] = []
    _collect_measure_values(value, values)
    if not values:
        return None, None
    unique: list[str] = []
    for item in values:
        if item not in unique:
            unique.append(item)
    return unique[0], unique[-1]


def _mapping_status(
    alignment: Mapping[str, object] | None,
    *,
    review_state: object = None,
) -> str:
    if not alignment:
        return "unresolved"
    if alignment.get("verified") is True or review_state == "confirmed":
        return "verified"
    if alignment.get("promotion_allowed") is True:
        return "probable"
    return "unresolved"


def map_caplin_manifest(
    manifest: Mapping[str, object],
    *,
    transcript_segments: Iterable[TranscriptSegment] = (),
) -> dict[str, object]:
    """Translate the existing Caplin lecture pipeline manifest for pedagogy use."""

    if not isinstance(manifest, Mapping):
        raise TypeError("manifest must be a mapping")
    segments = tuple(transcript_segments)
    if not all(isinstance(item, TranscriptSegment) for item in segments):
        raise TypeError("transcript_segments must contain TranscriptSegment models")

    mapped: list[dict[str, object]] = []
    music_regions = manifest.get("music_regions", ())
    if not isinstance(music_regions, (list, tuple)):
        raise ValueError("manifest music_regions must be a list")

    for item in music_regions:
        if not isinstance(item, Mapping):
            continue
        start = float(item.get("start_seconds", 0.0))
        end = float(item.get("end_seconds", start))
        alignment = item.get("known_score_alignment")
        alignment_map = alignment if isinstance(alignment, Mapping) else None
        status = _mapping_status(alignment_map, review_state=item.get("review_state"))
        measure_start, measure_end = _measure_range(alignment_map or {})
        identification = item.get("piece_identification")
        identification_map = identification if isinstance(identification, Mapping) else None
        identity = _identity_from_mapping(identification_map)
        promotable_identity = bool(
            identification_map
            and identification_map.get("promotion_allowed") is True
        )
        transcript = _nearest_segment(start, end, segments)
        mapped.append(
            {
                "region_id": str(item.get("region_id") or ""),
                "audio_locator": item.get("source_locator"),
                "start_seconds": start,
                "end_seconds": end,
                "mapping_status": status,
                "measure_start": measure_start if status != "unresolved" else None,
                "measure_end": measure_end if status != "unresolved" else None,
                "piece": identity if promotable_identity else None,
                "piece_candidate": identity,
                "piece_identity_promotable": promotable_identity,
                "transcript_segment": (
                    {
                        "segment_id": transcript.segment_id,
                        "locator": transcript.locator,
                        "text": transcript.text,
                    }
                    if transcript is not None
                    else None
                ),
                "review_required": status == "unresolved",
                "audio_evidence": {
                    "alignment": dict(alignment_map) if alignment_map else None,
                    "identification": dict(identification_map) if identification_map else None,
                    "transcription": item.get("transcription"),
                },
            }
        )

    return {
        "schema_version": 1,
        "source": manifest.get("source"),
        "known_score": manifest.get("known_score"),
        "mappings": mapped,
        "provenance_layers": [
            "verified_or_authoritative_score_evidence",
            "audio_derived_identification_alignment_or_note_evidence",
            "instructor_course_interpretation",
            "assistant_pedagogical_inference",
        ],
        "policy": {
            "semantic_identity_is_verified": False,
            "amt_is_verified_score": False,
            "weak_alignment_creates_measure_mapping": False,
        },
    }


def map_lecture_analysis(
    analysis: LectureAudioAnalysis,
    *,
    transcript_segments: Iterable[TranscriptSegment] = (),
) -> dict[str, object]:
    if not isinstance(analysis, LectureAudioAnalysis):
        raise TypeError("analysis must be a LectureAudioAnalysis")
    segments = tuple(transcript_segments)
    mapped: list[dict[str, object]] = []

    for item in analysis.music_regions:
        alignment = item.alignment
        status = "unresolved"
        measure_start = measure_end = None
        if alignment is not None and alignment.promotable:
            measures = [anchor.measure_number for anchor in alignment.anchors]
            measure_start = measures[0]
            measure_end = measures[-1]
            status = (
                "verified"
                if alignment.confidence is EvidenceConfidence.CONFIRMED
                else "probable"
            )
        identity = None
        candidate = None
        if item.piece_identification is not None and item.piece_identification.candidates:
            first = item.piece_identification.candidates[0]
            candidate = {
                "composer": first.composer,
                "work": first.title,
                "movement": first.movement,
            }
            if item.piece_identification.promotable:
                identity = candidate

        transcript = _nearest_segment(
            item.region.start_seconds,
            item.region.end_seconds,
            segments,
        )
        mapped.append(
            {
                "region_id": item.region.region_id,
                "audio_locator": item.region.source_locator,
                "start_seconds": item.region.start_seconds,
                "end_seconds": item.region.end_seconds,
                "mapping_status": status,
                "measure_start": measure_start,
                "measure_end": measure_end,
                "piece": identity,
                "piece_candidate": candidate,
                "piece_identity_promotable": identity is not None,
                "transcript_segment": (
                    {
                        "segment_id": transcript.segment_id,
                        "locator": transcript.locator,
                        "text": transcript.text,
                    }
                    if transcript is not None
                    else None
                ),
                "review_required": status == "unresolved",
                "unresolved": list(item.unresolved),
            }
        )

    return {
        "schema_version": 1,
        "artifact_id": analysis.artifact_id,
        "source": analysis.source_uri,
        "mappings": mapped,
        "unresolved_gaps": list(analysis.unresolved_gaps),
        "provenance_layers": [
            "verified_or_authoritative_score_evidence",
            "audio_derived_identification_alignment_or_note_evidence",
            "instructor_course_interpretation",
            "assistant_pedagogical_inference",
        ],
    }