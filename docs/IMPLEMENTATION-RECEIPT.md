# Tutor Framework implementation receipt

Date: 2026-09-25
Repository: `tutor-framework-github-candidate`
Status: local publication candidate; not pushed or published

## Objective coverage

- **Publication candidate:** a clean, GitHub-ready copy of the implementation
  with the reusable `skills/tutor-framework/` package; no push, publication,
  deployment or external execution performed.
- **Generalized foundation:** versioned JSON-safe protocol, provenance and safety
  policies, generic tutor lifecycle, occupation router, capability registry and
  connector interfaces.
- **Public pack contract:** 12 family manifests cover all 27 guide occupation
  groups; seven common draft-only workflow packs are included.
- **Music Score Literacy:** hardened MusicXML reader, `ScoreIR`, deterministic
  verification, anchored structural claims, teaching decision, bounded practice,
  optional fail-closed OMR boundary, evidence-gated memory and public synthetic
  evaluation fixture.
- **Reference examples:** office/admin, customer service, education and creative
  production examples return draft or learning outputs with no external actions.
- **Research and governance:** architecture, contribution, security, license,
  execution-state and third-party skill audit documents plus a concrete candidate
  skill registry. Healthcare and legal domain packs remain `not_adopted` pending
  professional review.

## Fresh validation

Commands run from the repository root:

```text
PYTHONPATH=src python3 -m unittest discover -s tests -v  -> 40 passed
PYTHONPATH=src python3 -m compileall -q src tests       -> passed
PYTHONPATH=src python3 -m tutor_framework.release_gate . -> release gate passed
python3 -c 'import tomllib; ...'                       -> pyproject parse passed
git diff --check                                        -> passed
```

The release gate checks required files, 12 family manifests, 27 unique occupation
groups, skill-registry fail-closed status, multilingual fixtures and unresolved
markers.

## Explicit limitations and remaining work

- `pytest` was not available on this host, so the standard-library `unittest`
  suite is the verified local fallback.
- The official skill validator could not run because this host's Python runtime
  does not have the `yaml` module installed. The frontmatter was checked for the
  required delimiters and fields, and the repository tests and release gate passed.
- `python3 -m build` and wheel packaging were not verified because `build` and
  `setuptools` are absent; dependency installation was unavailable under the
  current network/account limits.
- No provider SDK, OMR binary, cloud connector, account credential, message,
  schedule, upload, publication or deployment has been configured or exercised.
- Real occupation packs for regulated, rights-affecting, clinical, legal,
  emergency or physical-hazard work still require domain review, jurisdictional
  review and connector-specific threat testing.
- Candidate skills in `docs/skill-adoption-registry.json` are research records,
  not evidence of installation, authorization or runtime compatibility.

## Recovery pointers

- Reusable skill: `skills/tutor-framework/SKILL.md`
- Skill references: `skills/tutor-framework/references/`
- Public architecture: `docs/ARCHITECTURE.md`
- Release gate: `src/tutor_framework/release_gate.py`
