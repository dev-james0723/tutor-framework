---
name: tutor-framework
description: "Build or extend platform-neutral, evidence-grounded tutor systems for many occupations while preserving provenance, review, consent, and external-action boundaries."
license: "Apache-2.0"
metadata:
  version: "0.2.0"
  runtime: "Python 3.11+"
---

# Tutor Framework

Use this skill when designing, implementing, reviewing, or extending an
evidence-grounded tutor that must work across occupations without silently
inventing facts, professional authority, consent, credentials, or external
permissions.

## Quick start

1. Read `docs/ARCHITECTURE.md`, `docs/EXECUTION-STATES.md`, and `packs/README.md`.
2. Inspect the current protocol models, policies, engine, registry, and relevant
   pack before changing behavior.
3. Preserve claims, confidence, provenance, review state, anchors, ambiguity,
   consent, and action state in every material workflow.
4. Run the deterministic checks from the repository README and the release gate:

   ```bash
   PYTHONPATH=src python3 -m unittest discover -s tests -v
   PYTHONPATH=src python3 -m compileall -q src tests
   PYTHONPATH=src python3 -m tutor_framework.release_gate .
   ```

## Core workflow

- Normalize incoming text, documents, images, audio, spreadsheets, maps, and web
  sources into a traceable artifact or canonical representation.
- Separate observed facts, inferred interpretations, teaching decisions, and
  proposed next actions. Keep the source anchor and confidence beside each claim.
- Route by occupation family and task, then load only the smallest applicable
  pack or workflow. Packs are declarative guidance, not credentials or policy
  overrides.
- Produce a reviewable draft. Stop at `awaiting_consent`, `awaiting_review`, or
  `draft_only` when a human, domain expert, account, or external system is needed.
- Record why a result was accepted, rejected, or kept ambiguous so a later tutor
  can continue without turning an assumption into a fact.

## Extension rules

- Put reusable domain-neutral behavior in `src/tutor_framework/core/` or
  `src/tutor_framework/protocol/`.
- Put domain-specific parsing and explanations under
  `src/tutor_framework/domains/<domain>/`.
- Add occupation guidance as JSON manifests under `packs/`; do not hard-code
  provider credentials, personal data, or autonomous publishing behavior.
- Add public, synthetic evaluation cases under `evals/`. Never add real patient,
  student, customer, legal, financial, or private-message data.
- Keep provider integrations behind explicit connector interfaces and preserve
  the distinction between capability discovery, authorization, consent, preview,
  and execution.

## Music score literacy reference

Use the MusicXML slice as the model for a narrow, testable domain extension. It
supports structured score facts, key-signature interpretation, confidence, and
source anchors; it does not claim complete OMR, performance evaluation, or
professional music instruction. See
`skills/tutor-framework/references/music-score-literacy.md` and
`src/tutor_framework/domains/music/score.py`.

## Music lecture audio and score alignment

When a lecture recording contains musical demonstrations, treat those spans as
first-class evidence rather than transcript filler. Use
`src/tutor_framework/domains/music/audio.py` for the provider-neutral contracts
and read
`skills/tutor-framework/references/music-audio-score-alignment.md`.

- preserve timestamped speech, music, speech-over-music, silence/noise, and
  unknown regions;
- prefer alignment to a known score before reconstructing notation;
- keep automatic note recognition as hypotheses with per-event confidence;
- only build provisional ScoreIR from explicit quantized measure/beat evidence;
- never promote an audio reconstruction to confirmed score evidence by itself;
- preserve instructor interpretation, audio-derived evidence, verified score
  evidence, and tutor analysis as separate provenance layers;
- fail closed when a segmentation/transcription/alignment runtime is missing or
  unclear.

Concrete ML/audio libraries stay optional behind adapter protocols. Their presence
never implies permission to upload private recordings or use paid providers.

## Third-party skills

Before adopting another skill, record its source, license, capabilities, data
access, provider requirements, and review status in
`docs/skill-adoption-registry.json`. Keep regulated or high-impact packs
`not_adopted` until a qualified domain review and an explicit integration decision
exist. Use the narrowest compatible skill and do not treat its presence as
authorization to call a provider or perform an external action.

## Completion criteria

A change is ready for review only when the affected tests pass, the release gate
passes, `git diff --check` is clean, new fixtures contain no sensitive data, and
the resulting action state is explicit. A local check, preview, approval screen,
or draft is not a publication, message, schedule, upload, deployment, or push.
