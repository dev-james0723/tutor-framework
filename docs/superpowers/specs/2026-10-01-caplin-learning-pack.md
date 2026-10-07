# Caplin Learning Pack

Approved scope: James explicitly requested implementing the discussed Learning Pack, including recommended skills, tests, push, and deployment into the existing Caplin installation. Execute inline through verification without another proposal-only stop.

## Product
A PDF assignment/handout first becomes a source-indexed document dossier. Ask 3-5 short adaptive questions, omitting answers already given: learning purpose, help/answer-reveal policy, desired materials, depth/prior knowledge/language/deadline only when useful. Accept a clear use-recommendations response. Never auto-render a long video before learning intent is resolved. A later no-video or text-only choice overrides old video defaults.

One learning brief and one evidence-bearing content manifest drive every selected artifact. Core material: assignment decoder, original-score annotations where notation exists, passage analysis, hierarchical formal map, focused concept notes, listening guide, claim/evidence/alternatives, clearly separated course/theory/tutor/historical provenance, original-example references, different-passage transfer, practice, and final takeaway. Optional exports: PDF/Markdown/HTML study notes, annotated score, flashcards, quiz, essay outline, one-page summary, concept map, and video. Do not fabricate score annotation for text-only handouts. All source pages/questions must be mapped to content or explicitly unresolved.

The host Caplin tutor performs musical reasoning from inspected sources and authors validated content data; deterministic local code handles ingestion, questions, contracts, export, QA, and rebuilds. No unsourced automatic musical labels or hidden external model calls. Guided/question-first exports cannot leak answers in notes, diagrams, captions, annotations, flashcards, HTML source, or answer files. A separately requested reveal build is explicit.

## Architecture
Extend tutor_framework.domains.music.lesson with learning_pack modules; reuse the shared typed protocol and existing lesson cache/timebase/trust records. Retain the existing whiteboard/Mochi visual identity and existing Caplin knowledge/lecture stores. Ship a thin entrypoint in the existing installed skill, not a second system. New artifacts go to a new local output folder; the existing use-x20 lesson remains unchanged. Fix inherited unsupported QA passes before relying on them.

PDF ingestion is local and layout-aware: indexed text plus rendered page previews, source hash, page/line locators, page review states, no OCR-as-notation. Content may reference hash-bound source score crops and precise annotation rectangles; overlays must not redraw notation. Claim types distinguish visible evidence, primary statements, history, scholarship, course interpretation, Caplin theory, and tutor judgment.

## Release and privacy
Public GitHub receives only code, synthetic fixtures, generic integration docs, and license-permitted skill material. Never publish private handouts, derived book corpus, original lessons, recordings, model/font files, credentials, or absolute personal paths in new release fixtures. Deploy means update the existing local Caplin skill and test through that entrypoint; no new public website is implied. A code push is not deployment.

## Skills
Verify the seven recommended sources: PDF (openai/skills), summarize-slides, competency-unpacker, Study Notes Generator, MuseScore CLI, mindmap, educational-content-reviewer. Retain immutable revisions/hashes and actual licenses. Adopt narrow read-only instructions after full review; do not execute third-party install hooks, network content uploads, or cleanup. Unclear license/source stays reference-only with an original local capability covering the requested behavior. No blind collection install.

## Acceptance
Real legacy PDF intake -> adaptive questions -> confirmed brief -> evidence-authored pack -> readable PDF/Markdown/annotated score -> selected study aids -> manifest and QA; exercise guided and worked modes plus a text-only handout, malformed inputs, stale hashes, prompt injection, output traversal, cache corruption, and unrequested video. Inspect output page images and verify output text/links. Test existing framework and installed skill, commit/push, verify remote commit, deploy/update skill with rollback backup, run installed-entrypoint smoke tests. Any unavailable video/listening verification remains explicit; no render claimed from an audit or manifest flag.
