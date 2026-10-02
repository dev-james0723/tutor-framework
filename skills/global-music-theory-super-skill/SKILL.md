---
name: global-music-theory-super-skill
description: Use for music-theory tutoring, terminology conflicts, mixed curriculum/language contexts, source-bound exam study and original practice. Preserve Caplin Tutor as a separate specialist.
version: "0.1.0"
display_name: Global Music Theory Super Skill
---

# Global Music Theory Super Skill

Use `bin/global-music-theory` from an installed copy, or `python -m tutor_framework.domains.music.global_theory` in the repository. This is an independent entry point. The frozen `private/caplin-baseline` copy is an optional local specialist; the original `caplin-form-tutor` installation and store are never modified by this entry.

## Routing

- Answer simple concepts immediately. Keep response language, UK/US note names, cadence framework, curriculum version, and solfege system separate. Never infer any of them from nationality.
- For substantial tasks, ask only missing adaptive fields, at most five. Select only requested media; text-only overrides visual and audio media. Video requires an explicit requested deliverable.
- Use `term` for the 100-entry relation catalogue. It contains public metadata and review placeholders, not private source-derived definitions. `not-equivalent`, `disputed`, and context-dependent relations require explanation rather than a silent translation.
- Use `curriculum` for source-bound competency metadata. Unknown versions stay unknown. G6–8 exam blueprints need review; grade equivalence is never inferred.
- Caplin access requires explicit `CaplinCompatibility` opt-in with a frozen baseline path, tenant, provenance ID, and allowlisted files. Do not read its private knowledge by default.

## Evidence and exam work

- Keep source statement, interpretation, curriculum requirement, inference, and pedagogical example distinct. Append claim revisions; do not overwrite history.
- Intake accepts original PDF bytes only with exact catalogue identity, checksum, tenant and purpose grant, and the verified existing MinerU helper or structured-result replay adapter. If the adapter or permission is missing, stop with an explicit unavailable or review state. A parsed tree is only a candidate until notation and answers are independently checked.
- Keep original questions, official answers, third-party explanations, AI derivations, teacher results, and learner attempts in separate layers. Confirm the exact paper and question revision before worked or check mode. Hint and exam modes transmit only a strict student field allowlist. Active exam locks cover the whole paper and survive reopening. End exam simulation only after explicit exit.
- Use `practice` for one bounded original rhythm exercise or `mini-exam` for five original G1–5 questions. The latter creates separate student and teacher directories with independent symbolic checks and an unofficial disclaimer. Neither is an official ABRSM paper or teacher-calibrated score.
- For Learning Packs, call the existing `music.lesson.learning_pack` models and renderer through `global_theory.learning`; do not create another manifest or media pipeline. No-save returns session-only text and forbids an output directory.

## Examples

```sh
bin/global-music-theory doctor
bin/global-music-theory route 'What is a crotchet?'
bin/global-music-theory term 'imperfect cadence'
bin/global-music-theory curriculum ABRSM-G6
bin/global-music-theory mini-exam --grade 1 --syllabus-id abrsm-theory-from-2020 --seed 37 --output ./original-practice
```

No network fetch, paid parser, upload, deployment, or permanent installation is implicit in these commands.

## Operational reference

Read `references/implementation.md` for schemas, source/rights gates and rollback. `exam --request request.json` handles exact-resource ingestion, version-safe retrieval, answer-origin layers and the five tutor modes. `mineru-replay` is local-only; a replay is never counted as a new API parse. Do not interpret doctor/catalogue success as an available live ABRSM bank. Grades 6–8 full blueprints and musical expert acceptance remain review-gated.
