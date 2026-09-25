# Skill adoption reference

Treat external skills as capabilities to audit, not as automatic permissions.
Before combining a skill with Tutor Framework, record:

- source and version;
- license and redistribution terms;
- inputs, outputs, and data sensitivity;
- provider, credential, and network requirements;
- whether it can send, publish, schedule, upload, or otherwise mutate state;
- test evidence and known failure modes; and
- adoption status (`candidate`, `validated`, `not_adopted`, or `retired`).

The repository's `docs/skill-adoption-registry.json` is the durable record. Keep
regulated or high-impact integrations unadopted until qualified domain review is
complete. If a skill can affect an external system, expose capability discovery,
authorization, consent, preview, and execution as separate states. A skill being
installed or listed is never proof that the user authorized an external action.
