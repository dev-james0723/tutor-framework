"""Occupation routing and side-effect-free capability/connector contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from tutor_framework.protocol.models import (
    ActionProposal,
    ArtifactReadResult,
    CapabilityAvailability,
    EvidenceRef,
    LocalizationContext,
    OccupationProfile,
    TaskIntent,
    ToolManifest,
)


@dataclass(frozen=True)
class RoutingDecision:
    profile: OccupationProfile | None
    localization: LocalizationContext
    used_correction: bool = False
    requires_user_input: bool = False
    reason: str = ""


class OccupationRegistry:
    def __init__(self, profiles: tuple[OccupationProfile, ...] = ()) -> None:
        self._profiles: dict[str, OccupationProfile] = {}
        for profile in profiles:
            self.register(profile)

    def register(self, profile: OccupationProfile) -> None:
        if not isinstance(profile, OccupationProfile):
            raise TypeError("profile must be an OccupationProfile")
        if profile.occupation_id in self._profiles:
            raise ValueError(f"occupation already registered: {profile.occupation_id}")
        self._profiles[profile.occupation_id] = profile

    def route(
        self,
        intent: TaskIntent,
        *,
        user_correction: str | None = None,
        localization: LocalizationContext | None = None,
    ) -> RoutingDecision:
        if not isinstance(intent, TaskIntent):
            raise TypeError("intent must be a TaskIntent")
        context = localization or LocalizationContext(
            locale=intent.locale or "en-US",
            language=(intent.locale.split("-")[0] if intent.locale else "en"),
        )

        if user_correction is not None:
            profile = self._find(user_correction)
            if profile is None:
                return RoutingDecision(
                    None,
                    context,
                    used_correction=True,
                    requires_user_input=True,
                    reason="explicit occupation correction is not registered",
                )
            return RoutingDecision(
                profile, context, used_correction=True, reason="explicit correction"
            )

        candidates: list[OccupationProfile] = []
        if intent.occupation_hint:
            profile = self._find(intent.occupation_hint)
            if profile is not None:
                candidates.append(profile)
        if not candidates:
            candidates = [
                profile
                for profile in self._profiles.values()
                if intent.task_type in profile.supported_tasks
            ]
        if len(candidates) == 1:
            return RoutingDecision(candidates[0], context, reason="matched intent")
        if len(candidates) > 1:
            return RoutingDecision(
                None,
                context,
                requires_user_input=True,
                reason="multiple occupation profiles match",
            )
        return RoutingDecision(
            None,
            context,
            requires_user_input=True,
            reason="no occupation profile matches",
        )

    def _find(self, value: str) -> OccupationProfile | None:
        if not isinstance(value, str):
            return None
        normalized = value.strip().casefold()
        for profile in self._profiles.values():
            if normalized in {
                profile.occupation_id.casefold(),
                profile.display_name.casefold(),
                profile.family.casefold(),
            }:
                return profile
        return None


@dataclass(frozen=True)
class CapabilityResolution:
    capability_id: str
    available: bool
    manifest: ToolManifest | None = None
    reason: str = ""


class InMemoryCapabilityRegistry:
    """Offline registry used by the core and tests; no provider is contacted."""

    def __init__(self, manifests: tuple[ToolManifest, ...] = ()) -> None:
        self._manifests: dict[str, ToolManifest] = {}
        for manifest in manifests:
            if manifest.tool_id in self._manifests:
                raise ValueError(f"tool already registered: {manifest.tool_id}")
            self._manifests[manifest.tool_id] = manifest

    def resolve(self, capability_id: str) -> CapabilityResolution:
        manifest = self._manifests.get(capability_id)
        if manifest is None:
            return CapabilityResolution(
                capability_id, False, reason="capability is not registered"
            )
        if manifest.availability != CapabilityAvailability.AVAILABLE:
            return CapabilityResolution(
                capability_id,
                False,
                manifest,
                reason="capability is registered but not available in this runtime",
            )
        return CapabilityResolution(capability_id, True, manifest, reason="available")

    def available(self, intent: TaskIntent) -> tuple[ToolManifest, ...]:
        if not isinstance(intent, TaskIntent):
            raise TypeError("intent must be a TaskIntent")
        return tuple(
            manifest
            for manifest in self._manifests.values()
            if manifest.availability == CapabilityAvailability.AVAILABLE
        )


@runtime_checkable
class LocalFileConnector(Protocol):
    connector_id: str

    def read(self, path: str) -> ArtifactReadResult: ...


@runtime_checkable
class ImageConnector(Protocol):
    connector_id: str

    def read(self, image_ref: str) -> ArtifactReadResult: ...


@runtime_checkable
class AudioConnector(Protocol):
    connector_id: str

    def transcribe(self, audio_ref: str) -> ArtifactReadResult: ...


@runtime_checkable
class DocumentConnector(Protocol):
    connector_id: str

    def read(self, document_ref: str) -> ArtifactReadResult: ...


@runtime_checkable
class SpreadsheetConnector(Protocol):
    connector_id: str

    def read(self, spreadsheet_ref: str) -> ArtifactReadResult: ...


@runtime_checkable
class WebSourceConnector(Protocol):
    connector_id: str

    def search(self, query: str) -> tuple[EvidenceRef, ...]: ...


@runtime_checkable
class MapConnector(Protocol):
    connector_id: str

    def lookup(self, place: str) -> ArtifactReadResult: ...


@runtime_checkable
class SchedulingConnector(Protocol):
    connector_id: str

    def propose_event(self, details: dict[str, object]) -> ActionProposal: ...
