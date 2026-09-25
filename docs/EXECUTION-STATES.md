# Execution states

These states are deliberately separate and not equivalent:

| State | Meaning | What it does not mean |
|---|---|---|
| **local validation** | Tests, schema checks, compile checks or a local preview passed for the stated inputs and environment. | It is not a deployment, publication, send, upload or external execution. |
| **candidate integration** | A skill, connector or provider has a reviewable manifest, audit notes and bounded local test. | It is not installed, authorized for every user, or safe for unrestricted use. |
| **external execution** | A separately authorized adapter actually changed or contacted an external system. | It must never be inferred from a draft, proposal, approval screen or local preview. |

The current repository demonstrates local validation only. Its public packs and
reference examples are draft-only, and its connector interfaces are contracts. No
provider account, OMR binary, message, schedule, upload, publication or deployment
is required or claimed here.

For every result, report the state, inputs, environment, verification evidence and
any unavailable checks. Preserve proposed actions as proposed until the explicit
action-time boundary is crossed.
