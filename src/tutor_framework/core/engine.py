"""Generic tutor lifecycle orchestration.

This module deliberately knows nothing about occupation-specific parsing. A
domain reader, teaching profile, and capability registry are injected by the
caller so the same engine can host many occupation packs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from tutor_framework.protocol.models import (
    ArtifactReadResult,
    Claim,
    LocalizationContext,
    TaskIntent,
    ToolManifest,
    TutorDecision,
)


@dataclass
class LearnerState:
    learner_id: str
    locale: LocalizationContext = field(default_factory=LocalizationContext)
    goals: tuple[str, ...] = field(default_factory=tuple)
    preferences: dict[str, Any] = field(default_factory=dict)
    confirmed_memory: tuple[Claim, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not isinstance(self.learner_id, str) or not self.learner_id.strip():
            raise ValueError("learner_id must be a non-empty string")
        if not isinstance(self.locale, LocalizationContext):
            raise TypeError("locale must be a LocalizationContext")
        self.goals = _text_tuple(self.goals, "goals")
        if not isinstance(self.preferences, dict):
            raise TypeError("preferences must be a dictionary")
        if not all(isinstance(key, str) for key in self.preferences):
            raise TypeError("preference keys must be strings")
        if not isinstance(self.confirmed_memory, (list, tuple)) or not all(
            isinstance(item, Claim) for item in self.confirmed_memory
        ):
            raise TypeError("confirmed_memory must contain Claim models")
        self.confirmed_memory = tuple(self.confirmed_memory)


@dataclass(frozen=True)
class TutorTurn:
    intent: TaskIntent
    decision: TutorDecision
    artifact: ArtifactReadResult | None


@dataclass
class TutorSession:
    session_id: str
    learner_state: LearnerState
    turns: list[TutorTurn] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.session_id, str) or not self.session_id.strip():
            raise ValueError("session_id must be a non-empty string")
        if not isinstance(self.learner_state, LearnerState):
            raise TypeError("learner_state must be a LearnerState")
        if not isinstance(self.turns, list) or not all(
            isinstance(turn, TutorTurn) for turn in self.turns
        ):
            raise TypeError("turns must contain TutorTurn models")

    def record_turn(
        self,
        intent: TaskIntent,
        decision: TutorDecision,
        artifact: ArtifactReadResult | None,
    ) -> None:
        if not isinstance(intent, TaskIntent):
            raise TypeError("intent must be a TaskIntent")
        if not isinstance(decision, TutorDecision):
            raise TypeError("decision must be a TutorDecision")
        if artifact is not None and not isinstance(artifact, ArtifactReadResult):
            raise TypeError("artifact must be an ArtifactReadResult or None")
        self.turns.append(TutorTurn(intent, decision, artifact))


class DomainReader(Protocol):
    reader_id: str

    def read(self, intent: TaskIntent) -> ArtifactReadResult | None:
        """Read user-provided material without making a teaching decision."""


class TeachingProfile(Protocol):
    profile_id: str

    def decide(
        self,
        intent: TaskIntent,
        learner_state: LearnerState,
        artifact: ArtifactReadResult | None,
        capabilities: tuple[ToolManifest, ...],
    ) -> TutorDecision:
        """Turn shared context into a grounded tutor decision."""


class CapabilityRegistry(Protocol):
    def available(self, intent: TaskIntent) -> tuple[ToolManifest, ...]:
        """Return capabilities available for this intent without side effects."""


class TutorEngine:
    """Coordinate one turn while keeping domain behavior behind interfaces."""

    def __init__(
        self,
        reader: DomainReader,
        teaching_profile: TeachingProfile,
        capability_registry: CapabilityRegistry,
    ) -> None:
        self.reader = reader
        self.teaching_profile = teaching_profile
        self.capability_registry = capability_registry

    def run_turn(self, intent: TaskIntent, session: TutorSession) -> TutorDecision:
        if not isinstance(intent, TaskIntent):
            raise TypeError("intent must be a TaskIntent")
        if not isinstance(session, TutorSession):
            raise TypeError("session must be a TutorSession")

        artifact = self.reader.read(intent)
        if artifact is not None and not isinstance(artifact, ArtifactReadResult):
            raise TypeError("DomainReader must return ArtifactReadResult or None")

        capabilities = self.capability_registry.available(intent)
        if not isinstance(capabilities, (list, tuple)) or not all(
            isinstance(item, ToolManifest) for item in capabilities
        ):
            raise TypeError("CapabilityRegistry must return ToolManifest models")
        capabilities = tuple(capabilities)

        decision = self.teaching_profile.decide(
            intent, session.learner_state, artifact, capabilities
        )
        if not isinstance(decision, TutorDecision):
            raise TypeError("TeachingProfile must return a TutorDecision")
        session.record_turn(intent, decision, artifact)
        return decision


def _text_tuple(value: Any, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise TypeError(f"{field_name} must be an array of strings")
    result = tuple(value)
    if not all(isinstance(item, str) and item.strip() for item in result):
        raise ValueError(f"{field_name} must contain non-empty strings")
    return result
