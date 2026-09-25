# Tutor Framework Global Occupation Expansion

## Goal

Build a platform-neutral, evidence-grounded tutor framework whose first verified
vertical slice is music score literacy and whose public extension contract can
serve common occupations without assuming English, desktop access, one vendor,
or autonomous professional judgment.

## Global constraints

- Python 3.11+; `src/` layout; pytest.
- Keep artifact recognition, canonical representation, reasoning, teaching, and memory separate.
- Every material claim has type, confidence, provenance, review state, and an anchor when applicable.
- Preserve ambiguity; never silently upgrade uncertainty.
- Fail closed for unsupported analysis, hostile input, missing anchors, unsafe action, or absent capability.
- External tools and skills are optional adapters and never override core safety, consent, or provenance policy.
- No external service, paid API, OMR binary, account mutation, publication, deployment, or message sending is required for tests.
- Keep private C.A.P.L.A.N. source details out of public files; expose only the approved adapter contract.
- All outputs distinguish proposed/draft actions from executed actions.

## Task 1: Bootstrap package and test harness

Create `pyproject.toml`, `src/tutor_framework/`, protocol/core/profile/domain package
initializers, `tests/unit/`, `tests/integration/`, and a package smoke test. Configure
Python 3.11+, pytest, package discovery, and a minimal version. Verify the smoke test.

## Task 2: Protocol models and deterministic JSON

Create protocol models for `Anchor`, `EvidenceRef`, `Claim`, `ArtifactReadResult`,
`TutorDecision`, `TaskIntent`, `OccupationProfile`, `RiskClass`, `ToolManifest`,
`SkillManifest`, `ConsentRecord`, `LocalizationContext`, and `ActionProposal`.
Reject invalid confidence, malformed enums, and non-JSON-safe values. Preserve
deterministic serialized field ordering and schema versioning. Add round-trip tests.

## Task 3: Provenance, uncertainty, consent, and safety policies

Create pure policy functions for supportability, human review, conflict resolution,
memory promotion, consent scope, and action execution boundaries. Inferred claims
cannot become confirmed without review. Regulated, rights-affecting, physical-hazard,
and external-write actions must escalate or remain proposed.

## Task 4: Tutor Core lifecycle

Create `LearnerState`, `TutorSession`, `DomainReader`, `TeachingProfile`, capability
registry interfaces, and `TutorEngine.run_turn()`. The engine must route tasks but
must not contain occupation-specific parsing or C.A.P.L.A.N.-specific rules.

## Task 5: Occupation and capability registry

Create occupation routing, capability manifests, explicit user correction, locale and
unit context, and unavailable-capability results. Add connector interfaces for local
files, images, audio, documents, spreadsheets, web sources, maps, and scheduling.

## Task 6: Public occupation-pack contract

Create `packs/`, a pack manifest schema, an authoring template, and manifests for the
12 approved pack families covering the 27 guide occupation groups. Add common packs for
document assistant, spreadsheet assistant, photo checklist, voice notes, SOP tutor,
customer conversation practice, and source-backed research.

## Task 7: Music Score Literacy vertical slice

Implement the approved narrow slice: `ScoreIR`, hardened MusicXML reader, optional OMR
boundary, deterministic verification, grounded structural analysis, score teaching,
bounded practice generation, evidence-gated memory, and public synthetic evals.

## Task 8: First low-risk occupation examples

Implement small reference examples for office/admin, customer service, education, and
creative production using the common protocol and pack contract. Keep outputs drafts or
learning exercises; do not add external writes.

## Task 9: Public documentation and security registry

Create README, architecture, contribution guide, security policy, skill-adoption
registry, licensing notes, third-party skill audit checklist, and a clear distinction
between local validation, candidate integration, and external execution.

## Task 10: Evaluation and release gate

Add contract tests, multilingual fixtures, hostile-input tests, safety tests, missing
anchor tests, low-confidence tests, and pack manifest validation. Run the full suite,
build/package checks, and a repository scan for unresolved implementation markers.

## Acceptance

- The repository imports cleanly and has a runnable test suite.
- Protocol, policy, core, occupation, capability, and pack contracts are independently testable.
- MusicXML can flow through read → ScoreIR → verify → grounded claim → teaching decision → practice task.
- The occupation registry covers all 27 guide groups through 12 family manifests.
- No material output can silently become a confirmed claim or an executed external action.
- All claims of completion cite fresh verification evidence.
