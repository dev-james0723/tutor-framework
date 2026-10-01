"""Fail-closed production QA inventory for Caplin lesson releases."""
from __future__ import annotations
from .models import CheckState

REQUIRED_CHECKS=(
 "decode","timebase","symbolic_midi","source_notation","score_audio_highlight",
 "repeat_traversal","caption_structure","caption_audio_review","protected_listening",
 "loudness_and_clipping","notation_readability","layout_collisions","scene_transitions",
 "context_provenance","finale_identity_completeness","perceptual_listening",
 "baseline_preserved",
)

def release_decision(checks:dict[str,str],*,public_rights:str="validation_unavailable")->dict:
    allowed={x.value for x in CheckState}
    unknown=set(checks)-set(REQUIRED_CHECKS)
    if unknown: raise ValueError("unknown QA checks: "+", ".join(sorted(unknown)))
    complete={name:checks.get(name,CheckState.UNAVAILABLE.value) for name in REQUIRED_CHECKS}
    if any(v not in allowed for v in complete.values()): raise ValueError("invalid QA state")
    blocked=[k for k,v in complete.items() if v!=CheckState.PASSED.value]
    return {
      "verified_lesson":not blocked,
      "public_release_authorized":not blocked and public_rights=="passed",
      "checks":complete,"blocked_checks":blocked,"public_rights":public_rights,
      "render_success_is_not_completion":True,
    }
