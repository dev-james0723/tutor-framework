"""Public authoring contract for occupation packs."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from tutor_framework.protocol.models import ProtocolModel


@dataclass
class OccupationPackManifest(ProtocolModel):
    pack_id: str
    version: str
    family: str
    display_name: str
    occupations: tuple[str, ...]
    capabilities: tuple[str, ...]
    supported_tasks: tuple[str, ...]
    safety_notes: tuple[str, ...]
    required_connectors: tuple[str, ...] = field(default_factory=tuple)
    supported_locales: tuple[str, ...] = ("en",)
    external_writes: bool = False
    execution_mode: str = "draft_only"
    status: str = "reference"

    def __post_init__(self) -> None:
        super().__post_init__()
        for name in ("pack_id", "version", "family", "display_name", "status"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
        self.occupations = _text_tuple(self.occupations, "occupations")
        self.capabilities = _text_tuple(self.capabilities, "capabilities")
        self.supported_tasks = _text_tuple(self.supported_tasks, "supported_tasks")
        self.safety_notes = _text_tuple(self.safety_notes, "safety_notes")
        self.required_connectors = _text_tuple(
            self.required_connectors, "required_connectors", allow_empty=True
        )
        self.supported_locales = _text_tuple(
            self.supported_locales, "supported_locales"
        )
        if len(set(self.occupations)) != len(self.occupations):
            raise ValueError("occupations must be unique within a pack")
        if not isinstance(self.external_writes, bool):
            raise TypeError("external_writes must be a boolean")
        if self.external_writes:
            raise ValueError("public occupation packs cannot enable external writes")
        if self.execution_mode not in {"draft_only", "proposal_only"}:
            raise ValueError(
                "execution_mode must be draft_only or proposal_only"
            )


@dataclass(frozen=True)
class ManifestValidation:
    valid: bool
    errors: tuple[str, ...] = ()


def validate_manifest(manifest: OccupationPackManifest) -> ManifestValidation:
    if not isinstance(manifest, OccupationPackManifest):
        return ManifestValidation(False, ("value is not an occupation pack manifest",))
    errors: list[str] = []
    if not manifest.occupations:
        errors.append("at least one occupation is required")
    if not manifest.capabilities:
        errors.append("at least one capability is required")
    if not manifest.safety_notes:
        errors.append("at least one safety note is required")
    if manifest.external_writes:
        errors.append("external writes must remain disabled")
    return ManifestValidation(not errors, tuple(errors))


def load_manifest(path: str | Path) -> OccupationPackManifest:
    manifest_path = Path(path)
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"unable to load manifest {manifest_path}") from exc
    manifest = OccupationPackManifest.from_dict(payload)
    validation = validate_manifest(manifest)
    if not validation.valid:
        raise ValueError("invalid occupation pack: " + "; ".join(validation.errors))
    return manifest


def _text_tuple(
    value: object, field_name: str, *, allow_empty: bool = False
) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise TypeError(f"{field_name} must be an array of strings")
    result = tuple(value)
    if (not result and not allow_empty) or not all(
        isinstance(item, str) and item.strip() for item in result
    ):
        raise ValueError(f"{field_name} must contain non-empty strings")
    return result
