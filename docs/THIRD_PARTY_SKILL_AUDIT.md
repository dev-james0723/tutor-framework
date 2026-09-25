# Third-party skill audit checklist

Use this checklist before moving a skill from `research_candidate` to `candidate`
or `approved`. The registry is not an installer and does not imply that any skill is
available in a runtime.

## Identity and source

- [ ] Record the exact skill name, provider, version or commit, and source URL/path.
- [ ] Prefer official documentation or source-controlled instructions.
- [ ] Preserve the original skill text and note any local adaptation separately.
- [ ] Confirm the skill is relevant to the intended occupation family and locale.

## Trust and data handling

- [ ] Identify credentials, file access, browser access, network calls and data
      retention.
- [ ] Check for prompt injection, hidden instructions, arbitrary code execution,
      destructive commands, uploads, messages, publication and account changes.
- [ ] Confirm sensitive artifacts can remain local and that logs are redacted.
- [ ] Test malformed, oversized and adversarial inputs.

## Capability and license

- [ ] Verify the claimed capability exists in the target runtime.
- [ ] Verify the license, attribution, commercial terms and redistribution scope.
- [ ] Check provider version compatibility and failure behavior.
- [ ] Define an unavailable-capability result and a human-review boundary.

## Adoption gate

An approval record must state what was inspected, what was not inspected, permitted
scope, forbidden side effects, test evidence, reviewer, date and expiry/recheck
condition. Until then, keep the registry status at `research_candidate` or
`candidate` and keep `external_execution` false.
