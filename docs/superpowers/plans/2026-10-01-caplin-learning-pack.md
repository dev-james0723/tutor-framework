# Caplin Learning Pack Implementation Plan

> Execute inline using executing-plans; the user explicitly requested the complete implementation, push and deployment.

**Goal:** A source-grounded PDF-to-learning-material workflow with adaptive intent questions and real local exports.
**Architecture:** New learning_pack package inside the existing music lesson domain, sharing ProtocolModel, content hashes, evidence gates and legacy rendering. Host tutor authors musical analysis; deterministic code validates and exports it.
**Tech stack:** Python 3.11+, existing PyMuPDF, existing Playwright/Chromium for PDF export; no new cloud service.
**Spec:** docs/superpowers/specs/2026-10-01-caplin-learning-pack.md

## Global constraints
- Existing repo and installed Caplin skill only; preserve legacy artifacts and knowledge stores.
- No private/course/media/font data in public GitHub. No paid API or private upload.
- User intent must precede production; explicit no-video wins. Generated questionnaire is not confirmed consent.
- Guided mode withholds answer content across all artifacts, including embedded metadata.
- Unknown/review-required/unavailable never become passed. Reviews bind hashes.

## Review focus
1. Valid files with forged/stale QA: corruption/source-change tests and no hard-coded pilot passes.
2. Prompt injection in PDFs or skills: inert document text and no eval/shell/automatic remote calls.
3. Answer leakage through optional outputs: whole-pack negative string checks in guided mode.
4. Incomplete/scanned/multi-page PDFs: all-page indexing and explicit unresolved coverage, not made-up notes.
5. Deployment drift/public leakage: exact installed-file checksums, backup/rollback, clean release index and remote SHA verification.

## Tasks
- [ ] 1. Audit baseline and recommended skill sources/licenses. Save private snapshots and pinned source records. Baseline 130 framework + 44 installed skill tests. Inspect actual existing audit stubs; do not treat them as video generation.
- [ ] 2. Fix evidence-audit regressions and legal MIDI note-off handling with failing tests first. Files: compiler.py, pilot.py, verify_existing.py, adapters.py, tests/unit/test_lesson_evidence_integrity.py.
- [ ] 3. Implement typed LearningBrief, DocumentDossier, PackContent contracts and adaptive intake. Files: learning_pack/models.py, intake.py, document.py; tests/unit/test_learning_pack_contracts.py. Validate unknown fields, explicit selections, no-video, recommendation acceptance, source hashes, bounded paths and no answer leakage.
- [ ] 4. Implement source-bound notes/annotations/study-aid rendering and incremental orchestration. Files: learning_pack/render.py, export.py, service.py, __main__.py; tests/integration/test_learning_pack_pipeline.py. Real PDF + source-note layout, quiz/flashcards/mindmap/cheat-sheet/essay/listening exports, coverage and QA, pure local execution.
- [ ] 5. Build real use-x20 assignment pilot and a separate text-only example. Agent authors claims/annotations from the source and marks uncertainty. Execute confirmed worked and guided builds, inspect every PDF page, verify cached repeat build, verify no unrequested video, link the existing video without claiming a fresh video renderer.
- [ ] 6. Integrate verified recommended skills narrowly and install an actual Caplin entrypoint. Files: integrations/caplin-learning-pack/, tools/deploy_caplin_learning_pack.py, docs/CAPLIN_LEARNING_PACK.md; preserve existing private skill references and tests. Run entrypoint outside repo cwd.
- [ ] 7. Full tests, review, source-hash comparison, public-data audit, commit/push/PR merge if safe, deploy installed skill and verify it after remote commit. Save release receipt and user-visible artifact paths.

## Verification commands
Framework: PYTHONPATH=src python3 -m unittest discover -s tests
Media integration: existing use-x20/work/venv/bin/python with PYTHONPATH=src, same suite (actual optional dependencies available).
Installed skill: python3 -m unittest discover -s tests from the existing caplin-form-tutor directory.
Run installed learning_pack.py doctor/intake/build/verify outside repository cwd; compare generated file hashes and selected-output inventory, inspect PDF page renders.
