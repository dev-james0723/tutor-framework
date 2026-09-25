"""Fail-closed, provider-neutral safety and provenance policies."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from tutor_framework.protocol.models import (
    ActionProposal,
    Claim,
    ClaimStatus,
    ConsentRecord,
    ProposalStatus,
    RiskClass,
)


class PolicyOutcome(str, Enum):
    ALLOW = "allow"
    REVIEW_REQUIRED = "review_required"
    DENY = "deny"


@dataclass(frozen=True)
class PolicyResult:
    outcome: PolicyOutcome
    reason: str
    execution_allowed: bool = False


@dataclass(frozen=True)
class ConflictResolution:
    chosen: Claim | None
    reason: str
    requires_review: bool


MIN_SUPPORTABLE_CONFIDENCE = 0.8
MIN_MEMORY_CONFIDENCE = 0.9
RESTRICTED_ACTION_RISKS = frozenset(
    {
        RiskClass.REGULATED,
        RiskClass.RIGHTS_AFFECTING,
        RiskClass.PHYSICAL_HAZARD,
        RiskClass.EXTERNAL_WRITE,
    }
)


def assess_supportability(claim: Claim) -> PolicyResult:
    """Decide whether a claim can be used as grounded tutor context."""

    if claim.status == ClaimStatus.CONTRADICTED:
        return PolicyResult(PolicyOutcome.REVIEW_REQUIRED, "claim is contradicted")
    if claim.status == ClaimStatus.INFERRED:
        return PolicyResult(PolicyOutcome.REVIEW_REQUIRED, "claim is inferred")
    if claim.confidence < MIN_SUPPORTABLE_CONFIDENCE:
        return PolicyResult(
            PolicyOutcome.REVIEW_REQUIRED,
            "claim confidence is below the supportability threshold",
        )
    if not claim.evidence:
        return PolicyResult(
            PolicyOutcome.REVIEW_REQUIRED,
            "claim has no evidence references",
        )
    if any(not evidence.anchors for evidence in claim.evidence):
        return PolicyResult(
            PolicyOutcome.REVIEW_REQUIRED,
            "claim evidence is missing an anchor",
        )
    return PolicyResult(PolicyOutcome.ALLOW, "claim has sufficient evidence")


def requires_human_review(claim: Claim) -> bool:
    return assess_supportability(claim).outcome != PolicyOutcome.ALLOW


def resolve_conflict(claims: tuple[Claim, ...]) -> ConflictResolution:
    """Resolve only unambiguous claims; otherwise preserve the conflict."""

    if not claims:
        return ConflictResolution(None, "no claims were supplied", True)

    statements = {claim.statement for claim in claims}
    ranked = sorted(claims, key=lambda claim: claim.confidence, reverse=True)
    best = ranked[0]
    if any(requires_human_review(claim) for claim in claims):
        return ConflictResolution(None, "one or more claims require review", True)
    if len(statements) == 1:
        return ConflictResolution(best, "claims agree", False)
    if len(ranked) > 1 and best.confidence - ranked[1].confidence >= 0.2:
        return ConflictResolution(best, "one claim has a clear confidence lead", False)
    return ConflictResolution(None, "conflicting claims are too close to choose", True)


def memory_promotion_allowed(claim: Claim, reviewed: bool) -> bool:
    """Permit durable memory only after explicit human review."""

    return bool(
        reviewed
        and claim.status == ClaimStatus.CONFIRMED
        and claim.confidence >= MIN_MEMORY_CONFIDENCE
        and bool(claim.evidence)
    )


def consent_covers(consent: ConsentRecord | None, requested_scope: str) -> bool:
    if consent is None or not consent.granted or not isinstance(requested_scope, str):
        return False
    return requested_scope in consent.scope


def action_execution_decision(
    proposal: ActionProposal,
    *,
    human_review: bool = False,
    consent: ConsentRecord | None = None,
    consent_scope: str | None = None,
) -> PolicyResult:
    """Gate execution; proposal generation itself is always allowed upstream."""

    if proposal.status != ProposalStatus.APPROVED:
        return PolicyResult(
            PolicyOutcome.REVIEW_REQUIRED,
            "action must be explicitly approved before execution",
        )
    if proposal.external_write or proposal.risk_class in RESTRICTED_ACTION_RISKS:
        return PolicyResult(
            PolicyOutcome.REVIEW_REQUIRED,
            "restricted or externally mutating actions remain proposed",
        )
    if consent_scope is not None and not consent_covers(consent, consent_scope):
        return PolicyResult(
            PolicyOutcome.REVIEW_REQUIRED,
            "consent does not cover the requested action scope",
        )
    if not human_review:
        return PolicyResult(
            PolicyOutcome.REVIEW_REQUIRED,
            "a human review is required before execution",
        )
    return PolicyResult(
        PolicyOutcome.ALLOW,
        "approved low-risk action may execute",
        execution_allowed=True,
    )
