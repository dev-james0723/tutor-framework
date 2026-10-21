# Caplin Form Tutor v3.6 Evidence-Driven Assignment Engine — isolated candidate closeout

**Date:** 2026-10-21 (EDT)
**Scope:** isolated local candidate; no installation, Push, Merge, deployment, external API or paid service.
**Worktree:** `/Users/ouxianxing/Projects/tutor-framework-caplin-v36-20261021`
**Branch:** `feat/caplin-evidence-driven-v36-20261021`
**Clean baseline commit:** `aa5bcb4a096ff8538d581b514d1480cc8671a54d`
**Original runtime:** `/Users/ouxianxing/.agents/skills/caplin-form-tutor/SKILL.md` at v3.5.0, untouched.
**Status:** **LOCAL CANDIDATE GO; INSTALLED / REAL-ASSIGNMENT PRODUCTION NO-GO**.

## Preflight and isolation

The main `tutor-framework` worktree had pre-existing tracked/untracked modifications. A new branch/worktree was created directly from its clean HEAD, not from the main dirty files. macOS was under `warn` memory pressure, with roughly 30.6 GB swap, ~21 GB available disk, 19 Kynlo-tracked heavy jobs and 15 pending launches. Only sequential lightweight Python commands and local PDF tests were used. No active agents, apps, existing worktrees, production settings, or private knowledge database were stopped or changed.

## Source changes (candidate only)

- `integrations/caplin-form-tutor-v36/SKILL.md`: staged v3.6.0-rc1 instructions, preserving all original 12 hard rules including exactly **1–3 deliberate mistakes per applicable assignment deliverable**; Challenge Mode remains a separate proposal. The staged instruction does not activate the skill.
- `integrations/caplin-form-tutor-v36/scripts/learning_models.py`: eliminates global fallback from off-topic instructor claims, requires 2 verified concept-specific independently anchored sources/locators, scopes counterexamples, and removes stale derived patterns. The installed `learning_models.py` was not touched.
- `src/tutor_framework/domains/music/lesson/learning_pack/assignment_engine.py`: typed `ScoreFact`, `ScoreMark`, `AnnotationProof`, `IntentionalError`, `CadenceCheck`, `PassageCorrespondence`, `SymbolicCadenceSnapshot`; exact span/notation/cadence/error register/Crux coverage gates; independent symbolic pitch-class contradiction checks. Reports source review as incomplete even if evidence structure is consistent.
- `src/tutor_framework/domains/music/lesson/learning_pack/assignment_pdf.py`: source-SHA-bound local renderer preserving original score pages, placing blue/teal/red overlays only in clear source corridors and routing blocked marks into colored margin lanes; main PDF score first then essay, standalone self-proof containing every mark, alternatives, intentional-error corrections, and the provided Crux correspondence.
- `tests/unit/test_caplin_v36_professor.py` and `tests/integration/test_caplin_v36_assignment.py`: TDD red/green regression fixtures for all new behavior. All fake score facts and professor citations are marked synthetic.
- `tools/smoke_caplin_v36.py`: reproducible offline visual smoke; writes to ignored `artifacts/caplin-v36-candidate-20261021/`.

## Tests and observed evidence

1. **Before fix (red):** 3 Professor Evidence tests failed because unrelated claims counted, duplicate same-recording claims counted, and off-topic counterexamples leaked. Assignment Engine initially failed import as intended. A later test exposed a multi-concept claim indexing bug, and a Crux test caught a missing standalone audit section.
2. **After fix (green):** all candidate tests pass. Existing Learning Pack unit contracts **21/21**, CLI **6/6**, install/deploy contract **8/8**, and PDF integration **13/13** remain green (**48 existing tests**). The new Professor and assignment tests pass (**13 new tests**).
3. **Synthetic visual smoke:** main **3 pages** (two score pages + essay) and self-proof **1 page**. Original score vectors were copied at native scale; all word boxes stayed within page bounds. PNG previews of score pages 1 and 2 were reviewed; the essay/self-proof PNGs initially hit Kynlo `MIME_MISMATCH`, then their converted JPEG previews were successfully inspected. **All four sample pages received human-model visual inspection.** No overlapping visible sample labels, clipped content or invented extra measure counters were observed.
4. **No true score review:** synthetic staff/notes are a rendering fixture, **not** a reliable Caplin example. No professor transcript, assigned sonata notation, live audio, factual source-note alignment, or score-harmony-analyzer precision baseline was independently reviewed. The PDF smoke's proven correctness is layout/order/integrity, **not** musical correctness.

## Release decision

**GO — isolated engineering candidate:** source changes compile; targeted TDD and backwards-compatible Learning Pack tests pass; synthetic PDFs render, are reviewed and remain separated.

**NO-GO — installed v3.6 production skill or real submission:** this is a staged candidate, **not deployed**, and the following are still required before any installation:

1. Build human-verified source-score fixtures with real notes, accidentals, bass, harmonic context, repeats and multiple systems, and verify the original editions are authorized for local analysis.
2. Read and cite actual professor lesson transcripts/feedback for each asserted phrase-function term. Independently inspect linked concept/locator correctness in live data before promoting claims to `verified`.
3. Validate score-aware placement on dense real pages, nested brackets and multiple cadence arrivals; verify no music is covered after all-page visual review.
4. Wire new assignment export into existing `Learning Pack` selection/reveal mode, including explicit assignment requirements; the candidate currently exposes a Python API rather than a fully deployed skill workflow.
5. Run a full integration E2E with score-harmony-analyzer input and real per-mark self-proof verification. Maintain distinct `structural_gate`, `symbolic_consistency_only`, `content_accuracy=review_required`, and `visual_review` statuses.
6. Review the staged skill packaging and reconcile it with the installed `references/` and `scripts/` without overwriting personal course data, original skill settings or undocumented user edits.

## Rollback and safety

- **Fast rollback:** no change to installed skill or original framework worktree was made; simply continue using v3.5.0. No restore action is necessary.
- **Candidate rollback:** retain this branch/commit as evidence; to abandon, remove only this dedicated worktree after checking for uncommitted changes and then delete its branch if explicitly desired. Never delete `~/Projects/tutor-framework` or `~/.local/share/caplin-form-tutor`.
- **Candidate QA artifacts:** `artifacts/caplin-v36-candidate-20261021/receipt.json` and its two PDF outputs, source fixture, 4 PNG images and the optional converted JPEGs. The `artifacts/` tree is Git-ignored.
- **Standing rule:** mandatory deliberate-error rule was **preserved**. Challenge Mode was **not activated**. Disclosures appear only in standalone self-proof or a plain response if no audit is delivered.

**Required future approval:** separate install/release approval only after independent musical and visual GO gates. No Push, Merge, deployment, cost or external sending is authorized by this receipt.
