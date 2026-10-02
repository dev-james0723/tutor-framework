"""Append-only claim revisions separate statements from interpretations."""
from __future__ import annotations

from dataclasses import dataclass


KINDS = frozenset({"verified_fact", "source_statement", "curriculum_requirement",
                   "interpretation", "inferred_mapping", "pedagogical_example", "uncertain"})
SCOPES = frozenset({"public_catalogue", "private_material", "licensed_content", "system_exercise"})


@dataclass(frozen=True)
class EvidenceSnapshot:
    claim_id: str
    revision: int
    kind: str
    statement: str
    source_id: str
    source_version: str
    scope: str
    tenant_id: str | None = None
    supersedes: int | None = None

    def __post_init__(self):
        if self.kind not in KINDS or self.scope not in SCOPES:
            raise ValueError("unknown evidence kind or scope")
        if not self.claim_id or not self.statement or not self.source_id or not self.source_version:
            raise ValueError("evidence requires identity, content, source and version")
        if type(self.revision) is not int or self.revision < 1 or (self.revision > 1 and self.supersedes != self.revision - 1):
            raise ValueError("claim revision must append to its predecessor")
        if self.scope in {"private_material", "licensed_content"} and not self.tenant_id:
            raise ValueError("private evidence requires tenant")

    def to_framework_claim(self, *, source_uri: str, confidence: float):
        """Project into the existing framework without promoting inference to fact."""
        import json
        from tutor_framework.protocol.models import Claim, ClaimStatus, EvidenceRef, SourceKind
        source_kind = SourceKind.SYNTHETIC if self.scope == "system_exercise" else SourceKind.LOCAL_FILE if self.scope in {"private_material", "licensed_content"} else SourceKind.WEB
        reference = EvidenceRef(self.source_id, source_uri, source_kind)
        metadata = {"kind": self.kind, "revision": self.revision, "source_version": self.source_version,
                    "scope": self.scope, "tenant_id": self.tenant_id, "supersedes": self.supersedes}
        return Claim(self.claim_id, self.statement, confidence, ClaimStatus.INFERRED,
                     (reference,), json.dumps(metadata, sort_keys=True))


class EvidenceLedger:
    def __init__(self, *, tenant_id: str | None = None):
        self.tenant_id = tenant_id
        self._claims: dict[str, list[EvidenceSnapshot]] = {}

    def append(self, snapshot: EvidenceSnapshot) -> None:
        if snapshot.scope in {"private_material", "licensed_content"} and snapshot.tenant_id != self.tenant_id:
            raise ValueError("private evidence tenant mismatch")
        history = self._claims.setdefault(snapshot.claim_id, [])
        if snapshot.revision != len(history) + 1:
            raise ValueError("historical revisions cannot be overwritten or skipped")
        history.append(snapshot)

    def history(self, claim_id: str, *, scope: str) -> tuple[EvidenceSnapshot, ...]:
        return tuple(s for s in self._claims.get(claim_id, ()) if s.scope == scope and
                     (s.tenant_id is None or s.tenant_id == self.tenant_id))
