# Architecture reference

The framework is intentionally split into small, testable layers:

| Layer | Location | Responsibility |
| --- | --- | --- |
| Protocol | `src/tutor_framework/protocol/` | Versioned envelopes, claims, confidence, provenance, anchors, review state, and consent state. |
| Core | `src/tutor_framework/core/` | Tutor lifecycle, fail-closed policies, occupation routing, and connector interfaces. |
| Domains | `src/tutor_framework/domains/` | Narrow domain parsers and explanations, such as the MusicXML score slice. |
| Packs | `packs/` | Declarative occupation families and reusable workflows. |
| Evaluation | `tests/` and `evals/` | Deterministic behavior checks and public synthetic cases. |
| Release gate | `src/tutor_framework/release_gate.py` | Pack, fixture, metadata, and repository readiness checks. |

The normal data path is:

`source artifact -> canonical representation -> grounded claims -> teaching decision -> reviewable draft -> consent/review -> explicit execution`

No layer should collapse a proposed action into a completed external action. Read
`docs/ARCHITECTURE.md` for the full contract and `docs/EXECUTION-STATES.md` for
the state machine.
