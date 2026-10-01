# Caplin lesson compiler implementation plan

**Goal:** Extend the authoritative tutor-framework music domain and installed Caplin skill into a reusable, fail-closed local lesson compiler, then render and review one representative source-based pilot.

**Architecture:** Keep the shared ProtocolModel/EvidenceRef/ConsentRecord contracts. Add a music-domain lesson package with typed records, trust gates, an integer-sample timeline, content-addressed assets, optional local symbolic/media adapters, and a thin existing-whiteboard renderer adapter. A pilot is data consumed by this compiler, not a second pipeline. Preserve original use-x20 outputs byte-for-byte.

**Stack:** Python standard library core; existing local music21/Verovio/Kokoro/MuseScore/Playwright/FFmpeg adapters. No new dependencies, credentials, paid calls, uploads, background services, or public release.

**Spec:** ~/Downloads/Caplin_Tutor_Video_PRD_2026-09-30.zh-Hant.md (abridged local handoff); full same-named Library PRD read in this execution; current user execution brief is binding.

## Constraints and rulings
- Work in the authoritative repo on feat/caplin-video-compiler-20260930. No second repository/worktree. Clean main baseline 96749093f0fb8f11ad97ff0d20cb07010ca471c2.
- Private media/evidence live only in ignored artifacts/caplin-upgrade-20260930. Existing lesson is read-only and hash-registered.
- Unknown/review-required/unavailable are never passed. Reviews bind exact input hashes.
- 48,000 Hz integer sample clock; frame-exact scene boundaries at 24 fps. Rational musical time; explicit measure occurrence and pickup contracts.
- Listening windows contain no speech or BGM. Captions use final measured phrases; no fake word precision.
- Source notation remains faithful. Generated original/rewrite material is labelled and uses a single symbolic revision for engraving, MIDI, WAV and overlays.
- Preserve analytical ambiguity and source-level provenance; no promotion of AMT or weak alignment.
- Private local preview permission is distinct from publishing/recording-rights clearance.
- Ruling: perform requested inline execution on a new branch in the existing checkout, not another worktree; user explicitly scoped the authoritative repo and limited disk space favors no duplicate runtime.

## Review focus
1. Stale/corrupted output despite identical names: content hash, tool version, source revision and corruption recovery tests.
2. Pickups, simultaneous voices, ties and repeat visits: rational parsing and fail-closed unsupported/ambiguous entry tests.
3. Changed speech affects timing/captions/render but not music: dependency isolation tests and real incremental rebuild.
4. Answer leakage and mixed listening: explicit reveal ordering plus digital-zero speech/BGM during music and decoded-output checks.
5. Unavailable perceptual/alignment/rights evidence: current-hash review checks; release blocks, never a fabricated pass.

## Tasks (execute sequentially with red/green evidence)
- [ ] 1. Baseline audit and architecture reconciliation; preserve hashes, current tests, regression fixtures and exact renderer provenance. Read representative score/video images.
- [ ] 2. Typed manifest, provenance/context/authorization and release gates. Files: lesson/models.py, lesson/trust.py; tests/unit/test_lesson_contracts.py. Reuse protocol models. Tests: unknown fields, enum errors, missing source locators, stale review, false-identification regression, consent/cost/private scope, unavailable != passed.
- [ ] 3. Rational symbolic and Music Example Lab. Files: lesson/symbolic.py, lesson/examples.py; tests/unit/test_lesson_symbolic.py. Tests: pickup, chord/backup/voice, ties, explicit repeat visits, transpose, allowed controlled diffs, no automatic historical/form truth. Existing optional music21/Verovio adapters only.
- [ ] 4. Dependency cache, timeline and local speech/music assets. Files: lesson/cache.py, lesson/timeline.py, lesson/adapters.py; tests/unit/test_lesson_build.py. Tests: corrupted output, dependency changes, time rounding, caption phrase consistency, protected windows, deterministic plans, manifest path boundaries.
- [ ] 5. Reusable existing-whiteboard components and compiler/CLI. Files: lesson/compiler.py, lesson/whiteboard.cjs, lesson/__main__.py, lesson/legacy.py. Tests/integration/test_lesson_pipeline.py. Reuse audited renderer and canonical Mochi, no wb build or automatic remote TTS.
- [ ] 6. Real pilot data, source note comparison, Context Card, different-material transfer, local render and rigorous media QA. Files: lesson/pilot.py, lesson/mediaqa.py; private artifacts. Test full decode, post-codec loudness/peak, exact music windows, captions, layouts, repeat traversal, finale gates and real content-hash reuse. Inspect frame sets and motion. Perceptual listening requires a listening-capable tool or human sign-off; do not manufacture it.
- [ ] 7. Full regressions, installed skill thin wrapper/documentation, change review, baseline hash recheck, local commit and final evidence handoff with exact reproduction commands. No push/merge/deploy.

## Baseline evidence
- Framework: 51/51 pass. Skill: 40/40 pass from correct skill cwd; initial wrong-cwd import error preserved.
- Original 20:07 lesson: full FFmpeg decode success, recorded SHA-256 ce2249a3307be19cf7824b6d81894489ccccae52a744293045e0eaf9f0f38969 matches; existing one/four-worker frame hashes equal.
- Current saved v3.2 fixture: K504 similarity 0.5803, promotion_allowed false; merged region 325 AMT events remains requires_human_review.
- Existing shortcomings: filename-only caches, hardcoded QA statements, no reusable typed compiler, no actual different-material transfer, no perceptual listening approval, recording rights unresolved.
