"""Shared, JSON-safe protocol models for the tutor framework.

The protocol deliberately uses plain dataclasses and standard-library JSON so
that occupation packs can run without a provider SDK or a network service.
"""

from __future__ import annotations

import json
import math
import types
from dataclasses import MISSING, dataclass, field, fields
from enum import Enum
from typing import Any, Mapping, Union, get_args, get_origin, get_type_hints


class RiskClass(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    REGULATED = "regulated"
    RIGHTS_AFFECTING = "rights_affecting"
    PHYSICAL_HAZARD = "physical_hazard"
    EXTERNAL_WRITE = "external_write"


class SourceKind(str, Enum):
    USER_PROVIDED = "user_provided"
    LOCAL_FILE = "local_file"
    CONNECTOR = "connector"
    WEB = "web"
    SYNTHETIC = "synthetic"
    SYSTEM = "system"


class ClaimStatus(str, Enum):
    INFERRED = "inferred"
    SUPPORTED = "supported"
    CONFIRMED = "confirmed"
    CONTRADICTED = "contradicted"


class DecisionStatus(str, Enum):
    DRAFT = "draft"
    REVIEW_REQUIRED = "review_required"
    READY = "ready"


class ProposalStatus(str, Enum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    EXECUTED = "executed"
    REJECTED = "rejected"


class CapabilityAvailability(str, Enum):
    OPTIONAL = "optional"
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class ProtocolModel:
    """Mixin implementing versioned, deterministic JSON serialization."""

    SCHEMA_VERSION = "1.0"

    def __post_init__(self) -> None:
        for item in fields(self):
            _ensure_json_safe(getattr(self, item.name), item.name)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"schema_version": self.SCHEMA_VERSION}
        for item in fields(self):
            payload[item.name] = _to_json_value(getattr(self, item.name))
        return payload

    def to_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            ensure_ascii=False,
            separators=(",", ":"),
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ProtocolModel":
        if not isinstance(payload, Mapping):
            raise TypeError(f"{cls.__name__} payload must be a mapping")
        if payload.get("schema_version") != cls.SCHEMA_VERSION:
            raise ValueError(
                f"{cls.__name__} requires schema_version {cls.SCHEMA_VERSION!r}"
            )

        model_fields = {item.name: item for item in fields(cls)}
        unknown = set(payload) - {"schema_version", *model_fields}
        if unknown:
            raise ValueError(
                f"{cls.__name__} has unknown fields: {', '.join(sorted(unknown))}"
            )

        hints = get_type_hints(cls)
        values: dict[str, Any] = {}
        for name, item in model_fields.items():
            if name not in payload:
                if item.default is not MISSING or item.default_factory is not MISSING:
                    continue
                raise ValueError(f"{cls.__name__} is missing field: {name}")
            values[name] = _coerce_value(hints.get(name, Any), payload[name], name)
        return cls(**values)


def deserialize_model(
    payload: str | Mapping[str, Any], model_type: type[ProtocolModel]
) -> ProtocolModel:
    """Deserialize JSON text or a decoded mapping into one protocol model."""

    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ValueError("payload is not valid JSON") from exc
    if not isinstance(model_type, type) or not issubclass(model_type, ProtocolModel):
        raise TypeError("model_type must be a ProtocolModel subclass")
    return model_type.from_dict(payload)


def _to_json_value(value: Any) -> Any:
    if isinstance(value, ProtocolModel):
        return value.to_dict()
    if isinstance(value, Enum):
        return value.value
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise TypeError("non-finite floats are not JSON-safe")
        return value
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("JSON object keys must be strings")
        return {
            key: _to_json_value(value[key]) for key in sorted(value)
        }
    if isinstance(value, (list, tuple)):
        return [_to_json_value(item) for item in value]
    raise TypeError(f"value of type {type(value).__name__} is not JSON-safe")


def _ensure_json_safe(value: Any, field_name: str) -> None:
    try:
        _to_json_value(value)
    except TypeError as exc:
        raise TypeError(f"field {field_name!r} is not JSON-safe: {exc}") from exc


def _coerce_value(annotation: Any, value: Any, field_name: str) -> Any:
    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin in (Union, types.UnionType):
        if value is None and type(None) in args:
            return None
        failures: list[Exception] = []
        for option in args:
            if option is type(None):
                continue
            try:
                return _coerce_value(option, value, field_name)
            except (TypeError, ValueError) as exc:
                failures.append(exc)
        raise TypeError(f"field {field_name!r} does not match its type") from failures[-1]

    if annotation is Any:
        _ensure_json_safe(value, field_name)
        return value

    if origin is tuple:
        if not isinstance(value, (list, tuple)):
            raise TypeError(f"field {field_name!r} must be an array")
        if len(args) == 2 and args[1] is Ellipsis:
            return tuple(_coerce_value(args[0], item, field_name) for item in value)
        if len(value) != len(args):
            raise ValueError(f"field {field_name!r} has the wrong tuple length")
        return tuple(
            _coerce_value(item_type, item, field_name)
            for item_type, item in zip(args, value)
        )

    if origin is list:
        if not isinstance(value, list):
            raise TypeError(f"field {field_name!r} must be an array")
        item_type = args[0] if args else Any
        return [_coerce_value(item_type, item, field_name) for item in value]

    if origin in (dict, Mapping):
        if not isinstance(value, dict):
            raise TypeError(f"field {field_name!r} must be an object")
        key_type, value_type = args if len(args) == 2 else (str, Any)
        return {
            _coerce_value(key_type, key, field_name): _coerce_value(
                value_type, item, field_name
            )
            for key, item in value.items()
        }

    if isinstance(annotation, type) and issubclass(annotation, Enum):
        try:
            return annotation(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"field {field_name!r} contains an invalid enum") from exc

    if isinstance(annotation, type) and issubclass(annotation, ProtocolModel):
        if not isinstance(value, Mapping):
            raise TypeError(f"field {field_name!r} must be an object")
        return annotation.from_dict(value)

    if annotation is str:
        if not isinstance(value, str):
            raise TypeError(f"field {field_name!r} must be a string")
        return value
    if annotation is bool:
        if not isinstance(value, bool):
            raise TypeError(f"field {field_name!r} must be a boolean")
        return value
    if annotation is int:
        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError(f"field {field_name!r} must be an integer")
        return value
    if annotation is float:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise TypeError(f"field {field_name!r} must be a number")
        return float(value)

    _ensure_json_safe(value, field_name)
    return value


def _require_text(value: Any, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")


def _require_optional_text(value: Any, field_name: str) -> None:
    if value is not None:
        _require_text(value, field_name)


def _require_enum(value: Any, enum_type: type[Enum], field_name: str) -> None:
    if not isinstance(value, enum_type):
        raise TypeError(f"{field_name} must be a {enum_type.__name__}")


def _require_confidence(value: Any) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("confidence must be a number")
    if not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError("confidence must be between 0 and 1")


def _normalise_text_tuple(value: Any, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise TypeError(f"{field_name} must be an array of strings")
    result = tuple(value)
    for item in result:
        _require_text(item, field_name)
    return result


def _normalise_mapping(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"{field_name} must be an object")
    if not all(isinstance(key, str) for key in value):
        raise TypeError(f"{field_name} keys must be strings")
    _ensure_json_safe(value, field_name)
    return dict(value)


@dataclass
class Anchor(ProtocolModel):
    artifact_id: str
    locator: str
    excerpt: str | None = None
    page: int | None = None
    line_start: int | None = None
    line_end: int | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        _require_text(self.artifact_id, "artifact_id")
        _require_text(self.locator, "locator")
        _require_optional_text(self.excerpt, "excerpt")
        for name in ("page", "line_start", "line_end"):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, int) or isinstance(value, bool) or value < 1):
                raise ValueError(f"{name} must be a positive integer")


@dataclass
class EvidenceRef(ProtocolModel):
    ref_id: str
    source_uri: str
    source_kind: SourceKind = SourceKind.USER_PROVIDED
    anchors: tuple[Anchor, ...] = field(default_factory=tuple)
    retrieved_at: str | None = None
    content_hash: str | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        _require_text(self.ref_id, "ref_id")
        _require_text(self.source_uri, "source_uri")
        _require_enum(self.source_kind, SourceKind, "source_kind")
        if not isinstance(self.anchors, (list, tuple)) or not all(
            isinstance(anchor, Anchor) for anchor in self.anchors
        ):
            raise TypeError("anchors must contain Anchor models")
        self.anchors = tuple(self.anchors)
        _require_optional_text(self.retrieved_at, "retrieved_at")
        _require_optional_text(self.content_hash, "content_hash")


@dataclass
class Claim(ProtocolModel):
    claim_id: str
    statement: str
    confidence: float
    status: ClaimStatus = ClaimStatus.INFERRED
    evidence: tuple[EvidenceRef, ...] = field(default_factory=tuple)
    notes: str | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        _require_text(self.claim_id, "claim_id")
        _require_text(self.statement, "statement")
        _require_confidence(self.confidence)
        self.confidence = float(self.confidence)
        _require_enum(self.status, ClaimStatus, "status")
        if not isinstance(self.evidence, (list, tuple)) or not all(
            isinstance(item, EvidenceRef) for item in self.evidence
        ):
            raise TypeError("evidence must contain EvidenceRef models")
        self.evidence = tuple(self.evidence)
        _require_optional_text(self.notes, "notes")


@dataclass
class ArtifactReadResult(ProtocolModel):
    artifact_id: str
    mime_type: str
    content: str
    confidence: float = 1.0
    anchors: tuple[Anchor, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    reader_id: str = "unknown"

    def __post_init__(self) -> None:
        super().__post_init__()
        _require_text(self.artifact_id, "artifact_id")
        _require_text(self.mime_type, "mime_type")
        if not isinstance(self.content, str):
            raise TypeError("content must be a string")
        _require_confidence(self.confidence)
        self.confidence = float(self.confidence)
        if not isinstance(self.anchors, (list, tuple)) or not all(
            isinstance(item, Anchor) for item in self.anchors
        ):
            raise TypeError("anchors must contain Anchor models")
        self.anchors = tuple(self.anchors)
        self.warnings = _normalise_text_tuple(self.warnings, "warnings")
        _require_text(self.reader_id, "reader_id")


@dataclass
class TutorDecision(ProtocolModel):
    decision_id: str
    response: str
    confidence: float
    claims: tuple[Claim, ...] = field(default_factory=tuple)
    action_proposals: tuple[ActionProposal, ...] = field(default_factory=tuple)
    follow_up_questions: tuple[str, ...] = field(default_factory=tuple)
    status: DecisionStatus = DecisionStatus.DRAFT

    def __post_init__(self) -> None:
        super().__post_init__()
        _require_text(self.decision_id, "decision_id")
        if not isinstance(self.response, str):
            raise TypeError("response must be a string")
        _require_confidence(self.confidence)
        self.confidence = float(self.confidence)
        if not isinstance(self.claims, (list, tuple)) or not all(
            isinstance(item, Claim) for item in self.claims
        ):
            raise TypeError("claims must contain Claim models")
        if not isinstance(self.action_proposals, (list, tuple)) or not all(
            isinstance(item, ActionProposal) for item in self.action_proposals
        ):
            raise TypeError("action_proposals must contain ActionProposal models")
        self.claims = tuple(self.claims)
        self.action_proposals = tuple(self.action_proposals)
        self.follow_up_questions = _normalise_text_tuple(
            self.follow_up_questions, "follow_up_questions"
        )
        _require_enum(self.status, DecisionStatus, "status")


@dataclass
class TaskIntent(ProtocolModel):
    request: str
    task_type: str = "general"
    occupation_hint: str | None = None
    desired_output: str | None = None
    locale: str | None = None
    risk_class: RiskClass = RiskClass.LOW
    context: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        super().__post_init__()
        _require_text(self.request, "request")
        _require_text(self.task_type, "task_type")
        _require_optional_text(self.occupation_hint, "occupation_hint")
        _require_optional_text(self.desired_output, "desired_output")
        _require_optional_text(self.locale, "locale")
        _require_enum(self.risk_class, RiskClass, "risk_class")
        self.context = _normalise_mapping(self.context, "context")


@dataclass
class OccupationProfile(ProtocolModel):
    occupation_id: str
    display_name: str
    family: str
    description: str = ""
    supported_tasks: tuple[str, ...] = field(default_factory=tuple)
    capabilities: tuple[str, ...] = field(default_factory=tuple)
    risk_class: RiskClass = RiskClass.LOW

    def __post_init__(self) -> None:
        super().__post_init__()
        _require_text(self.occupation_id, "occupation_id")
        _require_text(self.display_name, "display_name")
        _require_text(self.family, "family")
        if not isinstance(self.description, str):
            raise TypeError("description must be a string")
        self.supported_tasks = _normalise_text_tuple(
            self.supported_tasks, "supported_tasks"
        )
        self.capabilities = _normalise_text_tuple(self.capabilities, "capabilities")
        _require_enum(self.risk_class, RiskClass, "risk_class")


@dataclass
class ToolManifest(ProtocolModel):
    tool_id: str
    version: str
    description: str
    capabilities: tuple[str, ...] = field(default_factory=tuple)
    side_effects: tuple[str, ...] = field(default_factory=tuple)
    supported_mime_types: tuple[str, ...] = field(default_factory=tuple)
    availability: CapabilityAvailability = CapabilityAvailability.OPTIONAL

    def __post_init__(self) -> None:
        super().__post_init__()
        _require_text(self.tool_id, "tool_id")
        _require_text(self.version, "version")
        if not isinstance(self.description, str):
            raise TypeError("description must be a string")
        self.capabilities = _normalise_text_tuple(self.capabilities, "capabilities")
        self.side_effects = _normalise_text_tuple(self.side_effects, "side_effects")
        self.supported_mime_types = _normalise_text_tuple(
            self.supported_mime_types, "supported_mime_types"
        )
        _require_enum(self.availability, CapabilityAvailability, "availability")


@dataclass
class SkillManifest(ProtocolModel):
    skill_id: str
    version: str
    description: str
    domains: tuple[str, ...] = field(default_factory=tuple)
    capabilities: tuple[str, ...] = field(default_factory=tuple)
    invocation_contract: str = "draft_only"

    def __post_init__(self) -> None:
        super().__post_init__()
        _require_text(self.skill_id, "skill_id")
        _require_text(self.version, "version")
        if not isinstance(self.description, str):
            raise TypeError("description must be a string")
        self.domains = _normalise_text_tuple(self.domains, "domains")
        self.capabilities = _normalise_text_tuple(self.capabilities, "capabilities")
        _require_text(self.invocation_contract, "invocation_contract")


@dataclass
class ConsentRecord(ProtocolModel):
    consent_id: str
    scope: tuple[str, ...]
    granted: bool = False
    subject: str = "learner"
    granted_at: str | None = None
    expires_at: str | None = None
    revocable: bool = True

    def __post_init__(self) -> None:
        super().__post_init__()
        _require_text(self.consent_id, "consent_id")
        self.scope = _normalise_text_tuple(self.scope, "scope")
        if not isinstance(self.granted, bool):
            raise TypeError("granted must be a boolean")
        _require_text(self.subject, "subject")
        _require_optional_text(self.granted_at, "granted_at")
        _require_optional_text(self.expires_at, "expires_at")
        if not isinstance(self.revocable, bool):
            raise TypeError("revocable must be a boolean")


@dataclass
class LocalizationContext(ProtocolModel):
    language: str = "en"
    locale: str = "en-US"
    timezone: str = "UTC"
    units: str = "metric"
    currency: str | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        for name in ("language", "locale", "timezone", "units"):
            _require_text(getattr(self, name), name)
        _require_optional_text(self.currency, "currency")


@dataclass
class ActionProposal(ProtocolModel):
    action_id: str
    action_type: str
    description: str
    risk_class: RiskClass = RiskClass.LOW
    external_write: bool = False
    requires_confirmation: bool = True
    status: ProposalStatus = ProposalStatus.PROPOSED
    payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        super().__post_init__()
        _require_text(self.action_id, "action_id")
        _require_text(self.action_type, "action_type")
        if not isinstance(self.description, str):
            raise TypeError("description must be a string")
        _require_enum(self.risk_class, RiskClass, "risk_class")
        if not isinstance(self.external_write, bool):
            raise TypeError("external_write must be a boolean")
        if not isinstance(self.requires_confirmation, bool):
            raise TypeError("requires_confirmation must be a boolean")
        _require_enum(self.status, ProposalStatus, "status")
        self.payload = _normalise_mapping(self.payload, "payload")
