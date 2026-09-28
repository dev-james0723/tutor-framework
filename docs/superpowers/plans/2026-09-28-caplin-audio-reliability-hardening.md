# CAPLIN Audio Reliability Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans or subagent-driven-development. Follow TDD: RED before production changes.

**Goal:** prevent semantic recognition, segmentation mistakes, Basic Pitch hypotheses, and weak score alignments from being promoted beyond their evidence.

**Architecture:** strengthen provider-neutral Tutor Framework evidence contracts first, then harden the concrete CAPLIN V3.1 runtime. Keep semantic ID, AMT, score alignment, instructor statements, and CAPLIN judgment as separate evidence channels.

**Tech Stack:** Python 3.11+, unittest, CAPLIN local ffmpeg/inaSpeechSegmenter/Basic Pitch/librosa/music21 runtimes.

**Spec:** docs/superpowers/specs/2026-09-28-caplin-audio-reliability-hardening.md

## Global Constraints

- no whole-lecture external upload;
- semantic Gemini evidence never verifies score identity by itself;
- no measure/beat promotion below the alignment gate;
- preserve exact source timestamps and four provenance layers;
- do not change system Python or silently enable paid/cloud processing.

## Review Focus

- same musical excerpt receives conflicting semantic identities;
- all fallback models return 429/503;
- long detector region contains more than one musical example;
- alignment has anchors but fails threshold/corroboration;
- Basic Pitch returns many notes with no calibrated confidence.

### Task 1: Framework promotion gates

**Files:** src/tutor_framework/domains/music/audio.py, src/tutor_framework/domains/music/__init__.py, tests/unit/test_music_audio.py

- [ ] Add failing tests for semantic-only identity remaining review-required and weak/uncorroborated alignment not being promotable.
- [ ] Run tests and confirm RED for the missing promotion semantics.
- [ ] Add explicit corroboration/promotability state to piece-identification and score-alignment evidence.
- [ ] Include piece identity in region review-state derivation and treat only promotable alignment as aligned.
- [ ] Add an optional suspicious-music-duration review gate.
- [ ] Run targeted and full Tutor Framework tests.

### Task 2: Concrete Gemini reliability

**Files:** CAPLIN release source scripts/audio_score_listener.py, tests/test_google_fallback.py

- [ ] Add failing tests for 429 bounded fallback/retry metadata and semantic output being explicitly uncorroborated/non-promotable.
- [ ] Run RED.
- [ ] Implement bounded 429/503 failover with inspectable attempt history and fail-closed behavior.
- [ ] Tighten semantic response contract so one candidate remains a hypothesis, never score verification.
- [ ] Run targeted tests GREEN.

### Task 3: Concrete pipeline review gating

**Files:** CAPLIN release source scripts/lecture_audio_pipeline.py, tests/test_audio_score_listener_contract.py plus a new focused pipeline test if needed.

- [ ] Add failing tests: Basic Pitch without calibrated confidence -> requires_human_review; suspicious long music region -> segmentation review warning.
- [ ] Run RED.
- [ ] Implement evidence-state downgrade and long-region review metadata without destroying automatic-region provenance.
- [ ] Keep explicit --music-range rerun path.
- [ ] Run CAPLIN suite GREEN.

### Task 4: Documentation, version and deployment target

**Files:** CAPLIN SKILL.md/references as required; installed ~/.agents/skills/caplin-form-tutor deployment copy.

- [ ] Document corroboration and alignment promotion rules.
- [ ] Bump CAPLIN patch/minor version for the behavior change.
- [ ] Copy the verified release source into the installed skill only after tests are green.
- [ ] Run doctor and installed-copy tests/compileall.

### Task 5: Real fixture regression

- [ ] Rerun the Yale Lecture 10 focal window using the preserved local fixture.
- [ ] Confirm semantic misidentifications are retained only as uncorroborated candidates.
- [ ] Confirm long merged region is review-gated and manual split remains supported.
- [ ] Confirm no weak score alignment exposes a promoted measure/beat.
- [ ] Inspect manifests/evidence files before completion.
- [ ] Record a regression receipt and handoff.
