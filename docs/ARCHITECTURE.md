# Architecture

## Design goal

The framework is a tutor protocol and safety boundary, not a collection of
autonomous occupational agents. A domain pack may add recognition and teaching
knowledge through public contracts; it cannot bypass provenance, consent, or action
policies.

## Layers

1. **Protocol** — typed models such as `Claim`, `EvidenceRef`, `TaskIntent`,
   `TutorDecision`, `ToolManifest`, `ConsentRecord`, and `ActionProposal`. Models
   use schema version `1.0`, reject unsafe values, and serialize deterministically.
2. **Policy** — pure supportability, conflict, review, memory-promotion, consent,
   and action-boundary functions. Inferred claims cannot become durable confirmed
   memory without review and evidence.
3. **Core lifecycle** — `TutorSession`, `LearnerState`, injected `DomainReader`,
   `TeachingProfile`, capability registry, and `TutorEngine.run_turn()`. The core
   contains no occupation-specific parser.
4. **Occupation routing and connectors** — explicit occupation correction, locale
   and units context, capability availability, and side-effect-free connector
   interfaces. A missing capability returns an unavailable result.
5. **Public packs** — declarative manifests in `packs/`. They describe occupations,
   tasks, capabilities, locales, safety notes and execution mode. They do not
   install or authorize tools.
6. **Domain slices and examples** — MusicXML/ScoreIR and lecture-audio/score
   intelligence are music-domain slices; office, customer service, education and
   creative examples are intentionally draft or learning exercises.

## Evidence flow

```text
artifact -> reader -> canonical IR -> deterministic verification
         -> anchored claims -> teaching decision -> bounded practice/draft
         -> reviewed memory candidate (optional)
```

An external adapter may be offered at a boundary, but the core only consumes its
typed result. OMR is therefore an optional interface; absence of an OMR runtime is
an explicit unavailable state rather than a guessed score.

For lecture audio, the music-domain path is similarly adapter-based:

```text
lecture audio -> timestamped speech/music segmentation
              -> known score? -> score alignment -> measure/beat anchors
              -> otherwise -> note hypotheses -> provisional reconstruction
              -> review/provenance -> teaching analysis
```

Known-score alignment is preferred before reconstruction. Audio-derived note
hypotheses remain distinct from verified score evidence and from an instructor's
interpretation. Low-confidence or unclear polyphonic regions remain ambiguous or
review-required rather than being promoted to facts.

## Safety flow

```text
intent -> route -> discover capability -> propose draft
                                  -> policy review -> explicit human approval
                                  -> (future adapter execution, if separately authorized)
```

Regulated, rights-affecting, physical-hazard and externally mutating actions remain
proposed or require escalation. The current public packs do not execute external
writes.

## Extension rules

- Add a protocol field only with a schema/version decision and round-trip tests.
- Put recognition in a reader and canonical representation in a domain module;
  do not put it into `TutorEngine`.
- Keep every material claim supportable and anchored.
- Prefer unavailable or review-required states over inferred capability or authority.
- Add a synthetic, non-sensitive fixture before adding a provider integration.
- Keep heavy audio/ML libraries outside the framework's required dependencies;
  implement them behind the music audio adapter protocols and preserve their
  backend/version/provenance in concrete integrations.
