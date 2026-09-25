"""Small, hardened MusicXML-to-teaching vertical slice.

This is intentionally not a full notation engine. It extracts a conservative
ScoreIR for grounded literacy exercises and leaves image OMR behind an optional
adapter interface.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from tutor_framework.core.policies import memory_promotion_allowed
from tutor_framework.protocol.models import (
    Anchor,
    Claim,
    ClaimStatus,
    DecisionStatus,
    EvidenceRef,
    SourceKind,
    TutorDecision,
)


@dataclass(frozen=True)
class PitchIR:
    step: str
    octave: int
    alter: int = 0

    def __post_init__(self) -> None:
        if self.step not in set("ABCDEFG"):
            raise ValueError("pitch step must be A-G")
        if not isinstance(self.octave, int) or isinstance(self.octave, bool):
            raise TypeError("pitch octave must be an integer")
        if not isinstance(self.alter, int) or isinstance(self.alter, bool):
            raise TypeError("pitch alter must be an integer")


@dataclass(frozen=True)
class NoteIR:
    measure_number: str
    index: int
    duration: int
    pitch: PitchIR | None = None
    rest: bool = False
    voice: str | None = None
    note_type: str | None = None

    def __post_init__(self) -> None:
        if not self.measure_number.strip():
            raise ValueError("measure number is required")
        if self.index < 1 or self.duration < 1:
            raise ValueError("note index and duration must be positive")
        if self.rest == (self.pitch is not None):
            raise ValueError("a note must contain exactly one pitch or rest")
        if self.voice is not None and not self.voice.strip():
            raise ValueError("voice cannot be blank")


@dataclass(frozen=True)
class MeasureIR:
    number: str
    notes: tuple[NoteIR, ...]
    key_fifths: int | None = None
    beats: int | None = None
    beat_type: int | None = None

    def __post_init__(self) -> None:
        if not self.number.strip():
            raise ValueError("measure number is required")
        if not isinstance(self.notes, (list, tuple)):
            raise TypeError("measure notes must be a sequence")
        if not all(isinstance(note, NoteIR) for note in self.notes):
            raise TypeError("measure notes must contain NoteIR models")
        object.__setattr__(self, "notes", tuple(self.notes))
        for name in ("beats", "beat_type"):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, int) or value < 1):
                raise ValueError(f"{name} must be a positive integer")


@dataclass(frozen=True)
class ScoreIR:
    artifact_id: str
    title: str
    part_id: str
    divisions: int
    measures: tuple[MeasureIR, ...]

    def __post_init__(self) -> None:
        for name in ("artifact_id", "title", "part_id"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"{name} must be a non-empty string")
        if not isinstance(self.divisions, int) or self.divisions < 1:
            raise ValueError("divisions must be positive")
        if not isinstance(self.measures, (list, tuple)) or not self.measures:
            raise ValueError("score must contain at least one measure")
        if not all(isinstance(measure, MeasureIR) for measure in self.measures):
            raise TypeError("measures must contain MeasureIR models")
        object.__setattr__(self, "measures", tuple(self.measures))

    @property
    def note_count(self) -> int:
        return sum(len(measure.notes) for measure in self.measures)


@dataclass(frozen=True)
class ScoreVerification:
    valid: bool
    issues: tuple[str, ...] = ()
    checked_measures: int = 0
    checked_notes: int = 0


@dataclass(frozen=True)
class PracticeTask:
    task_id: str
    instruction: str
    anchor: Anchor
    external_write: bool = False


@runtime_checkable
class OMRReader(Protocol):
    def read(self, image_ref: str) -> ScoreIR: ...


@dataclass(frozen=True)
class OMRResult:
    available: bool
    score: ScoreIR | None = None
    reason: str = ""


def read_musicxml(xml: str | bytes, *, artifact_id: str = "musicxml") -> ScoreIR:
    """Read a bounded, non-network MusicXML payload into ScoreIR."""

    raw = xml.encode("utf-8") if isinstance(xml, str) else xml
    if not isinstance(raw, bytes):
        raise TypeError("MusicXML must be text or bytes")
    if len(raw) > 2_000_000:
        raise ValueError("MusicXML exceeds the 2 MB safety limit")
    lowered = raw.lower()
    if b"<!doctype" in lowered or b"<!entity" in lowered or b"<![" in lowered:
        raise ValueError("DOCTYPE, ENTITY and CDATA declarations are not accepted")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise ValueError("MusicXML is not well-formed XML") from exc
    if _local_name(root.tag) != "score-partwise":
        raise ValueError("only score-partwise MusicXML is supported")

    title = _text(_first_descendant(root, "work-title")) or "Untitled score"
    part = _first_child(root, "part")
    if part is None:
        raise ValueError("MusicXML contains no part")
    part_id = part.attrib.get("id", "P1")
    divisions = 1
    measures: list[MeasureIR] = []
    for measure_element in _children(part, "measure"):
        number = measure_element.attrib.get("number")
        if not number:
            raise ValueError("every measure must have a number")
        attributes = _first_child(measure_element, "attributes")
        key_fifths = _int_text(_first_descendant(attributes, "fifths")) if attributes is not None else None
        beats = _int_text(_first_descendant(attributes, "beats")) if attributes is not None else None
        beat_type = _int_text(_first_descendant(attributes, "beat-type")) if attributes is not None else None
        if attributes is not None:
            parsed_divisions = _int_text(_first_child(attributes, "divisions"))
            if parsed_divisions is not None:
                if parsed_divisions < 1:
                    raise ValueError("divisions must be positive")
                divisions = parsed_divisions
        notes: list[NoteIR] = []
        for index, note_element in enumerate(_children(measure_element, "note"), start=1):
            duration = _int_text(_first_child(note_element, "duration"))
            if duration is None or duration < 1:
                raise ValueError("every note must have a positive duration")
            rest = _first_child(note_element, "rest") is not None
            pitch_element = _first_child(note_element, "pitch")
            pitch = None
            if pitch_element is not None:
                step = _text(_first_child(pitch_element, "step"))
                octave = _int_text(_first_child(pitch_element, "octave"))
                alter = _int_text(_first_child(pitch_element, "alter")) or 0
                if step is None or octave is None:
                    raise ValueError("pitch requires step and octave")
                pitch = PitchIR(step, octave, alter)
            if rest == (pitch is not None):
                raise ValueError("note must contain exactly one pitch or rest")
            notes.append(
                NoteIR(
                    measure_number=number,
                    index=index,
                    duration=duration,
                    pitch=pitch,
                    rest=rest,
                    voice=_text(_first_child(note_element, "voice")),
                    note_type=_text(_first_child(note_element, "type")),
                )
            )
        if not notes:
            raise ValueError(f"measure {number} contains no notes")
        measures.append(MeasureIR(number, tuple(notes), key_fifths, beats, beat_type))
    if not measures:
        raise ValueError("MusicXML contains no measures")
    return ScoreIR(artifact_id, title, part_id, divisions, tuple(measures))


def verify_score(score: ScoreIR) -> ScoreVerification:
    if not isinstance(score, ScoreIR):
        raise TypeError("score must be a ScoreIR")
    issues: list[str] = []
    numbers = [measure.number for measure in score.measures]
    if len(numbers) != len(set(numbers)):
        issues.append("measure numbers are not unique")
    for measure in score.measures:
        for note in measure.notes:
            if note.duration < 1:
                issues.append(f"measure {measure.number} has a non-positive duration")
    return ScoreVerification(
        valid=not issues,
        issues=tuple(issues),
        checked_measures=len(score.measures),
        checked_notes=score.note_count,
    )


def analyze_score(score: ScoreIR) -> tuple[Claim, ...]:
    verification = verify_score(score)
    if not verification.valid:
        raise ValueError("cannot analyse an unverified score: " + "; ".join(verification.issues))
    first_measure = score.measures[0]
    first_note = first_measure.notes[0]
    claims = [
        _claim(
            score,
            "measure-count",
            f"The score contains {len(score.measures)} measures.",
            f"score/measure:{first_measure.number}",
        ),
        _claim(
            score,
            "note-count",
            f"The score contains {score.note_count} notes or rests.",
            "score/notes",
        ),
    ]
    if first_note.pitch is not None:
        claims.append(
            _claim(
                score,
                "opening-pitch",
                f"The opening pitched note is {first_note.pitch.step}{first_note.pitch.octave}.",
                f"score/measure:{first_measure.number}/note:{first_note.index}",
            )
        )
    if first_measure.key_fifths is not None:
        claims.append(
            _claim(
                score,
                "key-fifths",
                f"The first measure declares a key signature of {first_measure.key_fifths} fifths.",
                f"score/measure:{first_measure.number}/attributes/key",
            )
        )
    return tuple(claims)


def teach_score(score: ScoreIR, learner_prompt: str) -> TutorDecision:
    if not isinstance(learner_prompt, str) or not learner_prompt.strip():
        raise ValueError("learner_prompt must be a non-empty string")
    claims = analyze_score(score)
    opening = next((claim for claim in claims if claim.claim_id == "opening-pitch"), None)
    opening_text = opening.statement if opening else "The score begins with a rest."
    response = (
        f"For this practice pass, {opening_text} "
        f"We can work through {len(score.measures)} measures and check each rhythm against the score."
    )
    return TutorDecision(
        decision_id=f"music-teaching-{score.artifact_id}",
        response=response,
        confidence=1.0,
        claims=claims,
        status=DecisionStatus.READY,
    )


def generate_practice(score: ScoreIR, *, max_tasks: int = 3) -> tuple[PracticeTask, ...]:
    if not isinstance(score, ScoreIR):
        raise TypeError("score must be a ScoreIR")
    if not isinstance(max_tasks, int) or isinstance(max_tasks, bool) or not 1 <= max_tasks <= 5:
        raise ValueError("max_tasks must be between 1 and 5")
    tasks: list[PracticeTask] = []
    for measure in score.measures:
        for note in measure.notes:
            if len(tasks) >= max_tasks:
                return tuple(tasks)
            if note.rest:
                instruction = f"Clap the rest in measure {measure.number}, note {note.index}."
            else:
                instruction = (
                    f"Name and sing {note.pitch.step}{note.pitch.octave} in "
                    f"measure {measure.number}, note {note.index}."
                )
            tasks.append(
                PracticeTask(
                    task_id=f"{score.artifact_id}-practice-{len(tasks) + 1}",
                    instruction=instruction,
                    anchor=Anchor(
                        score.artifact_id,
                        f"score/measure:{measure.number}/note:{note.index}",
                    ),
                )
            )
    return tuple(tasks)


def memory_candidate(claim: Claim, *, reviewed: bool) -> Claim | None:
    """Return a claim only when the shared evidence-gated policy permits it."""

    return claim if memory_promotion_allowed(claim, reviewed) else None


def read_with_optional_omr(image_ref: str, omr: OMRReader | None) -> OMRResult:
    if not isinstance(image_ref, str) or not image_ref.strip():
        raise ValueError("image_ref must be a non-empty string")
    if omr is None:
        return OMRResult(False, reason="no OMR adapter is configured")
    try:
        score = omr.read(image_ref)
    except Exception as exc:  # adapter boundary: fail closed, never fabricate a score
        return OMRResult(False, reason=f"OMR adapter unavailable: {type(exc).__name__}")
    if not isinstance(score, ScoreIR):
        return OMRResult(False, reason="OMR adapter returned no verified ScoreIR")
    return OMRResult(True, score=score, reason="OMR adapter supplied ScoreIR")


def _claim(score: ScoreIR, claim_id: str, statement: str, locator: str) -> Claim:
    return Claim(
        claim_id=claim_id,
        statement=statement,
        confidence=1.0,
        status=ClaimStatus.SUPPORTED,
        evidence=(
            EvidenceRef(
                ref_id=f"{score.artifact_id}:{claim_id}",
                source_uri=f"musicxml://{score.artifact_id}",
                source_kind=SourceKind.USER_PROVIDED,
                anchors=(Anchor(score.artifact_id, locator),),
            ),
        ),
    )


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _children(element: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in list(element) if _local_name(child.tag) == name]


def _first_child(element: ET.Element | None, name: str) -> ET.Element | None:
    if element is None:
        return None
    return next(iter(_children(element, name)), None)


def _first_descendant(element: ET.Element | None, name: str) -> ET.Element | None:
    if element is None:
        return None
    for child in element.iter():
        if _local_name(child.tag) == name:
            return child
    return None


def _text(element: ET.Element | None) -> str | None:
    if element is None or element.text is None:
        return None
    value = element.text.strip()
    return value or None


def _int_text(element: ET.Element | None) -> int | None:
    value = _text(element)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"expected integer, got {value!r}") from exc
