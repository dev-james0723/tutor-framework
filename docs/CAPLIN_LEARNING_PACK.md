# Caplin Learning Pack

A local, source-grounded study-material workflow inside the existing music domain. It adds a real installed Caplin entrypoint rather than a second tutor system.

## What is implemented

PDF/Markdown/text intake produces a complete source-unit index and PDF page previews. The host tutor inspects those pages and asks only unresolved goal, help-mode and output-selection questions. A confirmed `LearningBrief` and source-cited `PackContent` drive deterministic exports: PDF/HTML/Markdown notes, source-faithful annotated score, listening guide, quiz, flashcards, essay outline, one-page summary and an offline interactive concept/form map.

The host Caplin tutor performs source interpretation and musical reasoning. This package does not invent analyses from raw PDF text or make an unconfigured external model call. Annotation preserves original vector pages and adds overlays plus a separate margin legend; it does not redraw music notation. Guided/coached exports remove answer-bearing content before rendering, including hidden HTML/metadata. Runtime schemas and checks do not replace semantic review of neutral question wording and factual accuracy.

Videos are selected companions, not an automatic side effect of every upload. An existing registered video can be reused with provenance in a worked/review pack. A new video request remains a handoff to the existing whiteboard/Mochi production workflow. Neither this notes exporter nor the legacy `audit-existing` command is a new video renderer. Missing selected materials are reported as pending.

## Commands

From the repository, with an interpreter containing optional PDF support:

```bash
PYTHONPATH=src python3 -m tutor_framework.domains.music.lesson.learning_pack doctor
PYTHONPATH=src python3 -m tutor_framework.domains.music.lesson.learning_pack schema --output /path/to/contracts.json
PYTHONPATH=src python3 -m tutor_framework.domains.music.lesson.learning_pack intake /path/to/assignment.pdf --output /path/to/lesson/intake --language zh-Hant
```

Read the dossier and its page previews. When the host has visually identified score pages, supply `--score-pages 2,3`. The flag is an explicit review input, not automated OMR. Save user answers separately, then:

```bash
PYTHONPATH=src python3 -m tutor_framework.domains.music.lesson.learning_pack brief DOSSIER.json --answers ANSWERS.json --output BRIEF.json
PYTHONPATH=src python3 -m tutor_framework.domains.music.lesson.learning_pack build DOSSIER.json --brief BRIEF.json --content CONTENT.json --output /path/to/lesson/pack --runtime RUNTIME.json --allow-source-root /path/to/approved/references
PYTHONPATH=src python3 -m tutor_framework.domains.music.lesson.learning_pack verify /path/to/pack/revisions/HASH
```

`RUNTIME.json` is trusted operator configuration with `node`, `playwright` and `chromium` paths. It is not accepted from PDF instructions. An explicit `--no-pdf` is available for debug/text-only export; it must not be used to pretend a requested PDF was produced.

## Deploy to the existing skill

```bash
python3 tools/deploy_caplin_learning_pack.py \
  --repo /path/to/tutor-framework \
  --skill-root /path/to/existing/caplin-form-tutor \
  --python /path/to/media-python \
  --export-runtime /path/to/local-runtime.json \
  --backup-root /path/to/private/deployment-backups \
  --dry-run
```

Remove `--dry-run` for the explicitly approved deployment. The deployer requires an existing Caplin 3.3/3.4 installation, preserves private knowledge and lecture code, backs up touched files, verifies installed hashes, and records the repository commit. It deploys V3.4.0 routing plus `scripts/learning_pack.py`; future calls do not depend on the current working directory. Rollback is available via `rollback_installation(backup_path)` and refuses to overwrite files changed after deployment.

Local deployment is not public hosting. No Vercel/Supabase service, external upload or new global skill is created by this task.

## Verification and evidence

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
# Also run the same suite using the existing media interpreter so real PDF tests run.
```

Tests cover source coverage, stale hashes, corrupt cached outputs, source-directory bounds, PDF glyph-only pages, malformed metadata, question-first gating, guided answer leakage, annotation geometry, original source pixels, no-video selection, content revision preservation, and installed-entrypoint deployment/rollback. The optional PDF tests report a skip in an interpreter without PyMuPDF; a release must also record a run where those tests actually execute.

The exporter reports artifact integrity separately from content accuracy and visual review. Legacy saved QA assertions cannot become fresh passes; legal MIDI note-on/zero-velocity note-off semantics are preserved. No new musical-confidence claim follows from file presence, waveform shape or a successful render.

A representative acceptance fixture uses the owner's existing Beethoven Op.119 No.1 assignment and produces bilingual notes and annotated pages. The fixture, original score, derived course maps, videos, private content manifests and output files stay in ignored local artifacts, not in this public repository. Public tests use original synthetic fixtures.

## Reviewed companion skills and licensing

The integration includes seven narrow capability guides. Five contain unchanged, pinned, license-identified upstream instruction snapshots: OpenAI PDF (Apache-2.0), Summarize Slides (MIT), Competency Unpacker (CC BY-SA 4.0), MuseScore CLI (Apache-2.0) and Mindmap (MIT). The CC BY-SA directory is separately identified with its attribution/license. Generic exclusive-controller rules and runtime installation scripts are not adopted.

Educational Content Reviewer had no established repository reuse license in the reviewed snapshot. The previously named Smithery Study Notes Generator could not be resolved to a verifiable source. Neither is represented as an installed upstream package; original native equivalents provide the relevant capability.

See `integrations/caplin-learning-pack/references/learning-pack-skills/sources.lock.json` and adjacent license notices. No third-party font or browser binary is distributed. PyMuPDF/MuPDF are separately offered under AGPL or commercial terms; review those terms for your distribution/use case. Playwright-core uses Apache-2.0. This repository does not imply that private musical scores or recordings are cleared for publication.

Primary runtime documentation:
- https://pymupdf.readthedocs.io/en/latest/about.html
- https://playwright.dev/docs/api/class-page#page-pdf
- https://playwright.dev/docs/browsers
