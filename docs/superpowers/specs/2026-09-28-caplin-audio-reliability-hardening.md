# CAPLIN Lecture-Audio Reliability Hardening

Date: 2026-09-28
Status: approved by E2E evidence
Source evidence: ~/.local/share/caplin-form-tutor/e2e-tests/2026-09-28-Wcjlm9Q29ec/FINAL_REPORT.md

## Problem

The real Yale Lecture 10 E2E test proved that the pipeline architecture works, but exposed three unsafe promotion paths:

1. Gemini semantic music identification can return confident but wrong work identities.
2. automatic segmentation can merge distinct musical examples into one region.
3. score alignment can emit measure/beat anchors even when similarity is weak or independent alignment routes disagree.

A fourth issue is evidence-state inflation: Basic Pitch note output was marked probable merely because notes existed even though the concrete adapter exposes no per-note confidence.

## Required behavior

### Piece identity
- semantic identification is candidate generation only;
- a semantic-only result is never promotable to verified/confirmed identity;
- downstream review state remains requires_human_review until identity is corroborated by non-semantic evidence such as course-context verification, fingerprint/reference-audio matching, or reviewed score alignment;
- conflicting identities across repeated/replayed excerpts must be preserved as ambiguity, never silently choose one;
- provider/model/fallback/retry history must remain inspectable.

### Google availability
- 429 and 503 are transient provider failures, not evidence about the music;
- retries/fallbacks are bounded;
- Retry-After may be honored only within a small bounded wait;
- exhausted retries fail closed and preserve the HTTP class;
- no whole-lecture upload; only explicitly authorized short excerpts.

### Segmentation
- suspiciously long music regions must be review-gated as possible merged examples;
- explicit timestamp overrides remain available;
- a manual correction never erases provenance of the automatic region that triggered review;
- overrides must preserve exact lecture timestamps.

### Note transcription
- Basic Pitch output without calibrated per-note confidence remains audio-derived hypothesis evidence;
- note count alone must not promote evidence to probable;
- Basic Pitch never becomes verified score evidence.

### Score alignment
- availability of anchors is not the same as promotability;
- alignment exposes a match score/threshold and explicit corroboration/review state;
- below-threshold or uncorroborated anchors remain candidate anchors and keep review_required;
- conflicting alignment routes suppress measure/beat promotion;
- low-confidence alignment must not prevent provisional transcription/reconstruction from remaining available as a separate provenance layer.

### Provenance
Keep these layers separate:
1. verified/public score evidence;
2. audio-derived identification/transcription/alignment;
3. instructor/course interpretation;
4. CAPLIN analytical judgment.

## Acceptance

- framework tests reproduce semantic-only overpromotion and weak-alignment overpromotion before fixes;
- CAPLIN tests reproduce 429/503 bounded fallback, uncorroborated Gemini state, Basic Pitch non-promotion, and suspicious long music-region review;
- all affected tests pass after implementation;
- full Tutor Framework suite, compileall, release gate, and diff check pass;
- CAPLIN package tests and doctor pass;
- the Yale Lecture 10 local fixture is rerun on the focal examples and generated evidence is inspected;
- no result is called complete solely because an adapter returned data.
