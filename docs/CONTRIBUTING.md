# Contributing

## Before changing code

Read the architecture, security policy, execution-state definitions, and the
relevant pack manifest. Keep changes within the current branch and do not add
credentials, private occupation source material, or external service calls to
tests.

## Development loop

1. Write a focused failing test for the protocol, policy, reader, pack or example.
2. Implement the smallest change that satisfies the contract.
3. Run the full standard-library suite and compile check:

   ```bash
   PYTHONPATH=src python3 -m unittest discover -s tests -v
   PYTHONPATH=src python3 -m compileall -q src tests
   ```

4. If pytest is available, also run `python3 -m pytest -q`.
5. Review the diff for private source leakage, unresolved markers, new external
   writes, and claims without evidence.

## Adding an occupation pack

Start from `packs/template/manifest.template.json`. Use a stable pack ID, list the
occupation groups it covers, state required capabilities and safety notes, and keep
`external_writes` false with `execution_mode` set to `draft_only` or
`proposal_only`. Add a manifest validation test and a synthetic example.

## Adding a skill or connector

Use the candidate-first checklist in
[`THIRD_PARTY_SKILL_AUDIT.md`](THIRD_PARTY_SKILL_AUDIT.md). A skill name in the
registry is a research candidate, not proof that it is installed, authorized,
compatible, or safe for a particular user. A connector must expose typed results,
availability failures, provenance, and side-effect boundaries.

## Review expectations

Reviewers should check correctness, evidence preservation, multilingual behavior,
hostile-input handling, privacy, regulated-domain escalation, and whether the code
confuses a draft/proposal with an executed action.
