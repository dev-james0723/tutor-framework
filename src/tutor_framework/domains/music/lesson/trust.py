"""Fail-closed evidence, alignment, rights and external-operation policies."""
from __future__ import annotations

import math
from datetime import datetime, timezone
from .models import CheckState, ReviewRecord, RightsRecord, ProductionGrant, sha256


def effective_review(review: ReviewRecord | None, current_hashes: dict[str, str]) -> str:
    if review is None:
        return CheckState.UNAVAILABLE.value
    if review.input_hashes != current_hashes:
        return CheckState.REVIEW_REQUIRED.value
    return review.state.value


def can_promote_music_evidence(*, method: str, similarity: float | None,
                               corroborated: bool, score_review: ReviewRecord | None,
                               current_hashes: dict[str, str] | None = None) -> bool:
    """AMT/model similarity is never a substitute for reviewed source notation.

    A corroborated identity can be promoted only with a current, independent
    score review. Basic Pitch note events remain derived hypotheses even then.
    """
    if method == "basic_pitch" or not corroborated or not current_hashes:
        return False
    return effective_review(score_review, current_hashes) == CheckState.PASSED.value


def highlight_level(source_type: str, *, independent_errors_ms: tuple[float, ...],
                    phrase_verified: bool, fps: int = 24, measure_verified: bool = False) -> str:
    fallback = "measure" if measure_verified else "phrase" if phrase_verified else "static"
    if source_type not in {"symbolic", "human_performance"} or type(fps) is not int or fps <= 0:
        return "static"
    if len(independent_errors_ms) < 4:
        return fallback
    if any(not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) or v < 0 for v in independent_errors_ms):
        return fallback
    # Conservative nearest-rank 95th percentile. Precision requires actual
    # independent anchors distributed across the passage (verified by the caller).
    errors = sorted(independent_errors_ms)
    p95 = errors[math.ceil(0.95 * len(errors)) - 1]
    limit = 1000 / fps if source_type == "symbolic" else 150
    return "note" if p95 <= limit and phrase_verified else fallback


def authorized(*, provider: str, asset_hashes: tuple[str, ...], private: bool,
               estimated_usd: float, grants: tuple[ProductionGrant, ...],
               now: datetime | None = None) -> bool:
    """Check a trusted out-of-band approval; lesson JSON cannot supply grants.

    This predicate does not spend funds. Remote adapters must also reserve a
    remaining budget transactionally; none are enabled by this local compiler.
    """
    if isinstance(estimated_usd, bool) or not isinstance(estimated_usd, (int, float)) or not math.isfinite(estimated_usd) or estimated_usd < 0:
        raise ValueError("invalid estimated provider cost")
    for digest in asset_hashes:
        sha256(digest)
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("authorization time must include timezone")
    return any(g.provider == provider and set(g.asset_hashes) == set(asset_hashes)
               and (not private or g.private_transfer) and estimated_usd <= g.max_usd
               and datetime.fromisoformat(g.expires_at) > now for g in grants)


def rights_allow_public(rights: RightsRecord) -> bool:
    return all(getattr(rights, key) in {"public_domain", "licensed", "original", "not_applicable"}
               for key in ("composition", "edition", "recording"))


def release_ready(checks: dict[str, str]) -> bool:
    # Caller supplies the complete required-check inventory, not only checks run.
    return bool(checks) and all(value == CheckState.PASSED.value for value in checks.values())
