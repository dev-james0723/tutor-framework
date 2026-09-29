"""Evidence-grounded lecture-audio to score contracts.

Heavy signal-processing and ML runtimes stay behind adapter protocols. This
module models timestamps, note hypotheses, score alignment, and provisional
reconstruction without claiming arbitrary polyphonic audio is exact.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Protocol, runtime_checkable

from .score import MeasureIR, NoteIR, PitchIR, ScoreIR


class AudioRegionKind(str, Enum):
    SPEECH = "speech"
    MUSIC = "music"
    SPEECH_OVER_MUSIC = "speech_over_music"
    SILENCE_NOISE = "silence_noise"
    UNKNOWN = "unknown"


class EvidenceConfidence(str, Enum):
    CONFIRMED = "confirmed"
    PROBABLE = "probable"
    AMBIGUOUS = "ambiguous"
    REQUIRES_HUMAN_REVIEW = "requires_human_review"


class PieceIdentificationMethod(str, Enum):
    CONTEXT = "context"
    FINGERPRINT = "fingerprint"
    SEMANTIC = "semantic"


@dataclass(frozen=True)
class TimedAudioRegion:
    region_id: str
    start_seconds: float
    end_seconds: float
    kind: AudioRegionKind
    detector_confidence: float
    source_uri: str

    def __post_init__(self) -> None:
        _require_text("region_id", self.region_id)
        _require_text("source_uri", self.source_uri)
        _require_seconds(self.start_seconds, "start_seconds")
        _require_seconds(self.end_seconds, "end_seconds")
        if self.end_seconds <= self.start_seconds:
            raise ValueError("end_seconds must be greater than start_seconds")
        _require_probability(self.detector_confidence, "detector_confidence")
        if not isinstance(self.kind, AudioRegionKind):
            raise TypeError("kind must be an AudioRegionKind")

    @property
    def source_locator(self) -> str:
        return f"{self.source_uri}#t={self.start_seconds:.3f},{self.end_seconds:.3f}"

    @property
    def contains_music(self) -> bool:
        return self.kind in {AudioRegionKind.MUSIC, AudioRegionKind.SPEECH_OVER_MUSIC}


@dataclass(frozen=True)
class PieceIdentificationCandidate:
    title: str
    confidence: float
    provider: str
    method: PieceIdentificationMethod
    composer: str | None = None
    movement: str | None = None
    recording: str | None = None
    external_id: str | None = None

    def __post_init__(self) -> None:
        _require_text("title", self.title)
        _require_probability(self.confidence, "confidence")
        _require_text("provider", self.provider)
        if not isinstance(self.method, PieceIdentificationMethod):
            raise TypeError("method must be a PieceIdentificationMethod")
        for name in ("composer", "movement", "recording", "external_id"):
            value = getattr(self, name)
            if value is not None:
                _require_text(name, value)


@dataclass(frozen=True)
class PieceIdentificationResult:
    available: bool
    candidates: tuple[PieceIdentificationCandidate, ...] = ()
    confidence: EvidenceConfidence = EvidenceConfidence.REQUIRES_HUMAN_REVIEW
    backend: str = ""
    reason: str = ""
    corroborated: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "candidates", tuple(self.candidates))
        if not all(isinstance(item, PieceIdentificationCandidate) for item in self.candidates):
            raise TypeError("candidates must contain PieceIdentificationCandidate models")
        if not isinstance(self.confidence, EvidenceConfidence):
            raise TypeError("confidence must be an EvidenceConfidence")
        if not isinstance(self.corroborated, bool):
            raise TypeError("corroborated must be a bool")
        if self.available and not self.candidates:
            raise ValueError("available piece identification must contain candidates")
        if self.confidence is EvidenceConfidence.CONFIRMED and not self.corroborated:
            raise ValueError("confirmed piece identification requires corroboration")

    @property
    def semantic_only(self) -> bool:
        return bool(self.candidates) and all(
            item.method is PieceIdentificationMethod.SEMANTIC for item in self.candidates
        )

    @property
    def promotable(self) -> bool:
        return (
            self.available
            and self.corroborated
            and self.confidence
            in {EvidenceConfidence.CONFIRMED, EvidenceConfidence.PROBABLE}
        )


@dataclass(frozen=True)
class AudioNoteEvent:
    midi_note: int
    start_seconds: float
    end_seconds: float
    confidence: float
    voice: str | None = None

    def __post_init__(self) -> None:
        if (
            not isinstance(self.midi_note, int)
            or isinstance(self.midi_note, bool)
            or not 0 <= self.midi_note <= 127
        ):
            raise ValueError("midi_note must be an integer from 0 to 127")
        _require_seconds(self.start_seconds, "start_seconds")
        _require_seconds(self.end_seconds, "end_seconds")
        if self.end_seconds <= self.start_seconds:
            raise ValueError("end_seconds must be greater than start_seconds")
        _require_probability(self.confidence, "confidence")
        if self.voice is not None and not self.voice.strip():
            raise ValueError("voice cannot be blank")


@dataclass(frozen=True)
class QuantizedAudioNote:
    event: AudioNoteEvent
    measure_number: str
    beat: float
    duration_divisions: int

    def __post_init__(self) -> None:
        if not isinstance(self.event, AudioNoteEvent):
            raise TypeError("event must be an AudioNoteEvent")
        _require_text("measure_number", self.measure_number)
        if not isinstance(self.beat, (int, float)) or isinstance(self.beat, bool) or self.beat <= 0:
            raise ValueError("beat must be positive")
        if (
            not isinstance(self.duration_divisions, int)
            or isinstance(self.duration_divisions, bool)
            or self.duration_divisions < 1
        ):
            raise ValueError("duration_divisions must be a positive integer")


@dataclass(frozen=True)
class ScoreTimeAnchor:
    audio_seconds: float
    measure_number: str
    beat: float
    confidence: float

    def __post_init__(self) -> None:
        _require_seconds(self.audio_seconds, "audio_seconds")
        _require_text("measure_number", self.measure_number)
        if not isinstance(self.beat, (int, float)) or isinstance(self.beat, bool) or self.beat <= 0:
            raise ValueError("beat must be positive")
        _require_probability(self.confidence, "confidence")


@dataclass(frozen=True)
class AudioTranscriptionResult:
    available: bool
    notes: tuple[AudioNoteEvent, ...] = ()
    quantized_notes: tuple[QuantizedAudioNote, ...] = ()
    confidence: EvidenceConfidence = EvidenceConfidence.REQUIRES_HUMAN_REVIEW
    backend: str = ""
    reason: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "notes", tuple(self.notes))
        object.__setattr__(self, "quantized_notes", tuple(self.quantized_notes))
        if not all(isinstance(note, AudioNoteEvent) for note in self.notes):
            raise TypeError("notes must contain AudioNoteEvent models")
        if not all(isinstance(note, QuantizedAudioNote) for note in self.quantized_notes):
            raise TypeError("quantized_notes must contain QuantizedAudioNote models")
        if not isinstance(self.confidence, EvidenceConfidence):
            raise TypeError("confidence must be an EvidenceConfidence")
        if self.available and not (self.notes or self.quantized_notes):
            raise ValueError("available transcription must contain note evidence")


@dataclass(frozen=True)
class ScoreAlignmentResult:
    available: bool
    anchors: tuple[ScoreTimeAnchor, ...] = ()
    confidence: EvidenceConfidence = EvidenceConfidence.REQUIRES_HUMAN_REVIEW
    backend: str = ""
    reason: str = ""
    match_score: float | None = None
    promotion_threshold: float | None = None
    corroborated: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "anchors", tuple(self.anchors))
        if not all(isinstance(anchor, ScoreTimeAnchor) for anchor in self.anchors):
            raise TypeError("anchors must contain ScoreTimeAnchor models")
        if not isinstance(self.confidence, EvidenceConfidence):
            raise TypeError("confidence must be an EvidenceConfidence")
        if not isinstance(self.corroborated, bool):
            raise TypeError("corroborated must be a bool")
        if self.available and not self.anchors:
            raise ValueError("available alignment must contain anchors")
        if self.match_score is not None:
            _require_probability(self.match_score, "match_score")
        if self.promotion_threshold is not None:
            _require_probability(self.promotion_threshold, "promotion_threshold")
        if self.promotion_threshold is not None and self.match_score is None:
            raise ValueError("promotion_threshold requires match_score")
        if self.confidence is EvidenceConfidence.CONFIRMED and not self.corroborated:
            raise ValueError("confirmed score alignment requires corroboration")

    @property
    def promotable(self) -> bool:
        if not self.available or not self.corroborated:
            return False
        if self.confidence not in {
            EvidenceConfidence.CONFIRMED,
            EvidenceConfidence.PROBABLE,
        }:
            return False
        if (
            self.promotion_threshold is not None
            and self.match_score is not None
            and self.match_score < self.promotion_threshold
        ):
            return False
        return True


@dataclass(frozen=True)
class ScoreReconstructionResult:
    available: bool
    score: ScoreIR | None = None
    confidence: EvidenceConfidence = EvidenceConfidence.REQUIRES_HUMAN_REVIEW
    reason: str = ""

    def __post_init__(self) -> None:
        if self.score is not None and not isinstance(self.score, ScoreIR):
            raise TypeError("score must be a ScoreIR")
        if self.available != (self.score is not None):
            raise ValueError("available reconstruction must contain exactly one ScoreIR")
        if not isinstance(self.confidence, EvidenceConfidence):
            raise TypeError("confidence must be an EvidenceConfidence")
        if self.confidence is EvidenceConfidence.CONFIRMED:
            raise ValueError("audio reconstruction cannot be marked confirmed")


@dataclass(frozen=True)
class MusicRegionAnalysis:
    region: TimedAudioRegion
    piece_identification: PieceIdentificationResult | None = None
    transcription: AudioTranscriptionResult | None = None
    alignment: ScoreAlignmentResult | None = None
    reconstruction: ScoreReconstructionResult | None = None
    review_state: EvidenceConfidence = EvidenceConfidence.REQUIRES_HUMAN_REVIEW
    unresolved: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.region.contains_music:
            raise ValueError("MusicRegionAnalysis requires a music-containing region")
        if self.piece_identification is not None and not isinstance(
            self.piece_identification, PieceIdentificationResult
        ):
            raise TypeError("piece_identification must be a PieceIdentificationResult")
        object.__setattr__(self, "unresolved", tuple(self.unresolved))
        if not isinstance(self.review_state, EvidenceConfidence):
            raise TypeError("review_state must be an EvidenceConfidence")

    @property
    def provisional_score(self) -> ScoreIR | None:
        return self.reconstruction.score if self.reconstruction is not None else None


@dataclass(frozen=True)
class LectureAudioAnalysis:
    artifact_id: str
    source_uri: str
    regions: tuple[TimedAudioRegion, ...] = ()
    music_regions: tuple[MusicRegionAnalysis, ...] = ()
    unresolved_gaps: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_text("artifact_id", self.artifact_id)
        _require_text("source_uri", self.source_uri)
        object.__setattr__(self, "regions", tuple(self.regions))
        object.__setattr__(self, "music_regions", tuple(self.music_regions))
        object.__setattr__(self, "unresolved_gaps", tuple(self.unresolved_gaps))
        if not all(isinstance(region, TimedAudioRegion) for region in self.regions):
            raise TypeError("regions must contain TimedAudioRegion models")
        if not all(isinstance(region, MusicRegionAnalysis) for region in self.music_regions):
            raise TypeError("music_regions must contain MusicRegionAnalysis models")


@runtime_checkable
class AudioSegmenter(Protocol):
    def segment(self, audio_ref: str) -> tuple[TimedAudioRegion, ...]: ...


@runtime_checkable
class PieceIdentifier(Protocol):
    def identify(
        self,
        audio_ref: str,
        region: TimedAudioRegion,
        context: Mapping[str, str] | None = None,
    ) -> PieceIdentificationResult: ...


@runtime_checkable
class AudioTranscriber(Protocol):
    def transcribe(self, audio_ref: str, region: TimedAudioRegion) -> AudioTranscriptionResult: ...


@runtime_checkable
class ScoreAligner(Protocol):
    def align(
        self,
        audio_ref: str,
        region: TimedAudioRegion,
        score: ScoreIR,
    ) -> ScoreAlignmentResult: ...


@runtime_checkable
class ScoreReconstructor(Protocol):
    def reconstruct(
        self,
        transcription: AudioTranscriptionResult,
        *,
        artifact_id: str,
    ) -> ScoreReconstructionResult: ...


def reconstruct_score_from_quantized(
    transcription: AudioTranscriptionResult,
    *,
    artifact_id: str,
    divisions: int = 480,
) -> ScoreReconstructionResult:
    """Build only the score explicitly supported by quantized note hypotheses."""

    _require_text("artifact_id", artifact_id)
    if not isinstance(transcription, AudioTranscriptionResult):
        raise TypeError("transcription must be an AudioTranscriptionResult")
    if not isinstance(divisions, int) or isinstance(divisions, bool) or divisions < 1:
        raise ValueError("divisions must be a positive integer")
    if not transcription.available:
        return ScoreReconstructionResult(
            False,
            confidence=EvidenceConfidence.REQUIRES_HUMAN_REVIEW,
            reason="transcription is unavailable",
        )
    if not transcription.quantized_notes:
        return ScoreReconstructionResult(
            False,
            confidence=EvidenceConfidence.REQUIRES_HUMAN_REVIEW,
            reason="quantized note/measure evidence is required for reconstruction",
        )

    grouped: dict[str, list[QuantizedAudioNote]] = {}
    order: list[str] = []
    for note in transcription.quantized_notes:
        if note.measure_number not in grouped:
            grouped[note.measure_number] = []
            order.append(note.measure_number)
        grouped[note.measure_number].append(note)

    measures: list[MeasureIR] = []
    lowest_confidence = 1.0
    for measure_number in order:
        notes: list[NoteIR] = []
        quantized = sorted(
            grouped[measure_number],
            key=lambda item: (float(item.beat), item.event.start_seconds, item.event.midi_note),
        )
        for index, item in enumerate(quantized, start=1):
            lowest_confidence = min(lowest_confidence, item.event.confidence)
            notes.append(
                NoteIR(
                    measure_number=measure_number,
                    index=index,
                    duration=item.duration_divisions,
                    pitch=_midi_to_pitch(item.event.midi_note),
                    voice=item.event.voice,
                )
            )
        measures.append(MeasureIR(measure_number, tuple(notes)))

    review_state = (
        EvidenceConfidence.PROBABLE
        if lowest_confidence >= 0.80
        else EvidenceConfidence.REQUIRES_HUMAN_REVIEW
    )
    return ScoreReconstructionResult(
        True,
        score=ScoreIR(
            artifact_id=artifact_id,
            title="Audio reconstruction (provisional)",
            part_id="audio-derived",
            divisions=divisions,
            measures=tuple(measures),
        ),
        confidence=review_state,
        reason="reconstructed only from explicitly quantized audio-note hypotheses",
    )


def analyze_lecture_audio(
    audio_ref: str,
    *,
    artifact_id: str,
    segmenter: AudioSegmenter,
    context: Mapping[str, str] | None = None,
    piece_identifier: PieceIdentifier | None = None,
    known_score: ScoreIR | None = None,
    aligner: ScoreAligner | None = None,
    transcriber: AudioTranscriber | None = None,
    reconstructor: ScoreReconstructor | None = None,
    max_music_region_seconds: float | None = None,
) -> LectureAudioAnalysis:
    """Analyze lecture audio without silently converting hypotheses into facts."""

    _require_text("audio_ref", audio_ref)
    _require_text("artifact_id", artifact_id)
    if known_score is not None and not isinstance(known_score, ScoreIR):
        raise TypeError("known_score must be a ScoreIR")
    if max_music_region_seconds is not None:
        if (
            not isinstance(max_music_region_seconds, (int, float))
            or isinstance(max_music_region_seconds, bool)
            or max_music_region_seconds <= 0
        ):
            raise ValueError("max_music_region_seconds must be a positive number")

    try:
        raw_regions = tuple(segmenter.segment(audio_ref))
    except Exception as exc:
        return LectureAudioAnalysis(
            artifact_id,
            audio_ref,
            unresolved_gaps=(f"audio segmentation unavailable: {type(exc).__name__}",),
        )

    try:
        _validate_regions(raw_regions, audio_ref)
    except (TypeError, ValueError) as exc:
        return LectureAudioAnalysis(
            artifact_id,
            audio_ref,
            unresolved_gaps=(f"invalid segmentation evidence: {exc}",),
        )

    music_analyses: list[MusicRegionAnalysis] = []
    global_gaps: list[str] = []
    for region in raw_regions:
        if not region.contains_music:
            continue

        unresolved: list[str] = []
        if (
            max_music_region_seconds is not None
            and region.end_seconds - region.start_seconds > max_music_region_seconds
        ):
            unresolved.append(
                "music region exceeds review duration; possible merged examples require split/override review"
            )
        piece_identification: PieceIdentificationResult | None = None
        alignment: ScoreAlignmentResult | None = None
        transcription: AudioTranscriptionResult | None = None
        reconstruction: ScoreReconstructionResult | None = None

        # When no authoritative score is already known, identify the work before
        # asking AMT to infer individual notes. This lets callers retrieve a score
        # and run a stronger alignment path on a subsequent pass.
        if known_score is None and piece_identifier is not None:
            piece_identification = _safe_identify(
                piece_identifier, audio_ref, region, context
            )
            if not piece_identification.available:
                unresolved.append(
                    piece_identification.reason or "piece identification unavailable"
                )
            elif not piece_identification.promotable:
                unresolved.append(
                    piece_identification.reason
                    or "piece identification requires independent corroboration"
                )

        if known_score is not None:
            if aligner is None:
                unresolved.append("known score supplied but no score aligner is configured")
            else:
                alignment = _safe_align(aligner, audio_ref, region, known_score)
                if not alignment.available:
                    unresolved.append(alignment.reason or "known-score alignment unavailable")
                elif not alignment.promotable:
                    unresolved.append(
                        alignment.reason
                        or "known-score alignment has candidate anchors but is not promotable"
                    )

        if transcriber is not None:
            transcription = _safe_transcribe(transcriber, audio_ref, region)
            if not transcription.available:
                unresolved.append(transcription.reason or "audio transcription unavailable")
        elif alignment is None or not alignment.available:
            unresolved.append("no audio transcription adapter is configured")

        aligned = alignment is not None and alignment.promotable
        if not aligned and transcription is not None and transcription.available:
            if reconstructor is not None:
                reconstruction = _safe_reconstruct(
                    reconstructor,
                    transcription,
                    artifact_id=f"{artifact_id}-{region.region_id}-provisional",
                )
            elif transcription.quantized_notes:
                reconstruction = reconstruct_score_from_quantized(
                    transcription,
                    artifact_id=f"{artifact_id}-{region.region_id}-provisional",
                )
            if reconstruction is not None and not reconstruction.available:
                unresolved.append(reconstruction.reason or "score reconstruction unavailable")

        review_state = _derive_review_state(
            region,
            alignment=alignment,
            transcription=transcription,
            reconstruction=reconstruction,
            unresolved=unresolved,
        )
        music_analyses.append(
            MusicRegionAnalysis(
                region=region,
                piece_identification=piece_identification,
                transcription=transcription,
                alignment=alignment,
                reconstruction=reconstruction,
                review_state=review_state,
                unresolved=tuple(unresolved),
            )
        )

    if not music_analyses:
        global_gaps.append("no music-containing regions were detected")

    return LectureAudioAnalysis(
        artifact_id=artifact_id,
        source_uri=audio_ref,
        regions=raw_regions,
        music_regions=tuple(music_analyses),
        unresolved_gaps=tuple(global_gaps),
    )


def _safe_identify(
    identifier: PieceIdentifier,
    audio_ref: str,
    region: TimedAudioRegion,
    context: Mapping[str, str] | None,
) -> PieceIdentificationResult:
    try:
        result = identifier.identify(audio_ref, region, context)
    except Exception as exc:
        return PieceIdentificationResult(
            False,
            reason=f"piece identification adapter unavailable: {type(exc).__name__}",
        )
    if not isinstance(result, PieceIdentificationResult):
        return PieceIdentificationResult(
            False, reason="piece identifier returned an invalid result"
        )
    return result


def _safe_align(
    aligner: ScoreAligner,
    audio_ref: str,
    region: TimedAudioRegion,
    score: ScoreIR,
) -> ScoreAlignmentResult:
    try:
        result = aligner.align(audio_ref, region, score)
    except Exception as exc:
        return ScoreAlignmentResult(
            False,
            reason=f"score alignment adapter unavailable: {type(exc).__name__}",
        )
    if not isinstance(result, ScoreAlignmentResult):
        return ScoreAlignmentResult(False, reason="score aligner returned an invalid result")
    return result


def _safe_transcribe(
    transcriber: AudioTranscriber,
    audio_ref: str,
    region: TimedAudioRegion,
) -> AudioTranscriptionResult:
    try:
        result = transcriber.transcribe(audio_ref, region)
    except Exception as exc:
        return AudioTranscriptionResult(
            False,
            reason=f"audio transcription adapter unavailable: {type(exc).__name__}",
        )
    if not isinstance(result, AudioTranscriptionResult):
        return AudioTranscriptionResult(False, reason="audio transcriber returned an invalid result")
    return result


def _safe_reconstruct(
    reconstructor: ScoreReconstructor,
    transcription: AudioTranscriptionResult,
    *,
    artifact_id: str,
) -> ScoreReconstructionResult:
    try:
        result = reconstructor.reconstruct(transcription, artifact_id=artifact_id)
    except Exception as exc:
        return ScoreReconstructionResult(
            False,
            reason=f"score reconstruction adapter unavailable: {type(exc).__name__}",
        )
    if not isinstance(result, ScoreReconstructionResult):
        return ScoreReconstructionResult(False, reason="score reconstructor returned an invalid result")
    return result


def _derive_review_state(
    region: TimedAudioRegion,
    *,
    alignment: ScoreAlignmentResult | None,
    transcription: AudioTranscriptionResult | None,
    reconstruction: ScoreReconstructionResult | None,
    unresolved: list[str],
) -> EvidenceConfidence:
    if region.detector_confidence < 0.65 or unresolved:
        return EvidenceConfidence.REQUIRES_HUMAN_REVIEW
    if alignment is not None and alignment.available:
        return alignment.confidence
    if reconstruction is not None and reconstruction.available:
        return reconstruction.confidence
    if transcription is not None and transcription.available:
        return transcription.confidence
    return EvidenceConfidence.REQUIRES_HUMAN_REVIEW


def _validate_regions(regions: tuple[TimedAudioRegion, ...], audio_ref: str) -> None:
    previous_start = -1.0
    for region in regions:
        if not isinstance(region, TimedAudioRegion):
            raise TypeError("segmenter must return TimedAudioRegion models")
        if region.source_uri != audio_ref:
            raise ValueError("region source_uri must match the analyzed audio_ref")
        if region.start_seconds < previous_start:
            raise ValueError("regions must remain in source-time order")
        previous_start = region.start_seconds


def _midi_to_pitch(midi_note: int) -> PitchIR:
    names = (
        ("C", 0), ("C", 1), ("D", 0), ("D", 1), ("E", 0), ("F", 0),
        ("F", 1), ("G", 0), ("G", 1), ("A", 0), ("A", 1), ("B", 0),
    )
    step, alter = names[midi_note % 12]
    octave = midi_note // 12 - 1
    return PitchIR(step, octave, alter)


def _require_text(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


def _require_seconds(value: float, name: str) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{name} must be a non-negative number")


def _require_probability(value: float, name: str) -> None:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not 0.0 <= float(value) <= 1.0
    ):
        raise ValueError(f"{name} must be between 0 and 1")
