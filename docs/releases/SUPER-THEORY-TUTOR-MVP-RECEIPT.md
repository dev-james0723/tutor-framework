# Super Theory Tutor — blocked foundation checkpoint

Execution state: **verified local foundations; MVP implementation incomplete; no staging or production deployment.**

Only saved-plan Tasks 1–3 are complete. Task 4 is blocked before implementation; Tasks 4–14 remain open. This file records a recoverable checkpoint and does not complete Task 14 or establish a production-ready release. The home shell currently links to `/sign-up`, which is not yet implemented.

## Source and isolation

- Canonical packaging lineage: `b13eeedd9765f00a15c06f35852382989abea279` on `feat/global-music-theory-super-skill-20261002`; remote rechecked, main remains its ancestor, no newer related approved lineage was found.
- Frozen implementation source: `394c1b7d9d3ca1edd68dd821e209866e3e883792`. Subsequent receipt/evidence commits do not change runtime code.
- Working branch: `feat/super-theory-tutor-mvp-20261003`.
- Isolated checkout: `/Users/ouxianxing/Projects/tutor-framework-super-theory-mvp-20261003`.
- Original checkout: `/Users/ouxianxing/Projects/tutor-framework`; HEAD/branch and all 36 original untracked files verified unchanged by SHA-256 and path inventory. No reset, stash, clean or overwrite performed.
- No tracked changes to the original `src/` engine or installed/frozen skill source. Unrelated Caplin Learning Pack files were not included. Only the six approved product documents and saved plan were copied.
- Existing regression packaging needs its ignored Caplin baseline. The local-only reference points to the already-installed, manifest-verified baseline; its 38 file hashes were verified. No baseline knowledge was copied into this branch.
- No production URLs, schema deployment, configured model-alias version or public CN launch exist for this checkpoint.

## Implemented foundations

1. Next.js/TypeScript workspace and app-shell rendering test without model/network availability. Only `/` and `/_not-found` currently build.
2. Authenticated internal FastAPI adapter around the unchanged deterministic engine, including operation envelopes, original student practice projection, bounded MusicXML/MXL parsing and real Verovio rendering with stable source-event IDs.
3. Regional policy contracts and PostgreSQL schema `0001`: explicit immutable home region, realm/ownership enforcement, append-only practice evidence, permitted evidence states, user deletion cascades and disposable migration up/down/up.

Regional policy tests are not evidence that actual resources are physically in Singapore/Beijing. The actual provider router, public account/session flow, regional storage and tenant E2E are pending.

## Verification of frozen foundation source

Observed at `2026-10-04T01:06:14.627263+00:00`; Node/Next build is local, not a deployment. PostgreSQL integration used a disposable PostgreSQL 17.11 cluster bound to `127.0.0.1:55437`, not a production database.

| Check | Result | Command |
|---|---|---|
| python-regression | 322 tests; OK; 1 inherited skip | `env PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v` |
| global-engine-gate | passed; all three subprocess gates exit 0 | `env PYTHONPATH=src .venv/bin/python tools/global_music_theory_gate.py` |
| theory-api | 42 passed; one Starlette TestClient deprecation warning; source identical to frozen commit | `env PYTHONPATH=src:services/theory-api .venv/bin/python -m pytest services/theory-api/tests -q` |
| web-postgres | 37 passed: shell 1, region 25, actual PostgreSQL integration 11 | `env TEST_DATABASE_URL=postgresql://postgres@127.0.0.1:55437/super_theory_test pnpm --filter @super-theory/web test` |
| web-typecheck | exit 0 | `pnpm --filter @super-theory/web typecheck` |
| web-lint | exit 0 | `pnpm --filter @super-theory/web lint` |
| web-build | exit 0; only / and /_not-found exist | `pnpm --filter @super-theory/web build` |

The Theory API green run occurred immediately before its commit with identical source, inputs, configuration and environment; it was reused. The remaining listed checks ran on frozen commit `394c1b7`. Raw command output is recoverable in the ignored plan workspace; file hashes, summaries, commands and all row statuses are committed in [the validated evidence JSON](super-theory-foundations-2026-10-03-evidence.json).

Known nonfatal warnings: existing PyMuPDF SWIG deprecation and Starlette TestClient httpx deprecation. The inherited unittest skip remains visible and is not counted as a pass.

## Foundation review and repairs

A fresh read-only reviewer reviewed Tasks 1–3 and independently ran the original 37-test API suite. Two Important findings were accepted; no Critical or Minor findings were established. This checkpoint review does not replace the final whole-product review required after Tasks 4–13.

- Unsafe UTF-16 entity input reached the existing byte-screening parser before defusedxml. Added LE/BE endpoint tests proving rejected XML never invokes that parser, then moved encoding-aware preflight before it. Standard MusicXML metadata doctype remains supported without fetching external resources.
- Zero-denominator timing and unsupported ZIP compression returned unstructured 500 errors. Added real malformed-input endpoint tests, then normalized known timing/archive failures to bounded `invalid_input` 422 responses with request IDs.

Observed RED: 4 failures, 1 pass. Observed GREEN: all 42 API tests passed. No original musical calculation logic changed.

## Complete acceptance matrix status

Every row from the approved matrix is retained. A local foundation pass does not imply a product gate passed. `validation_unavailable` means the required full-product check could not run for the stated reason; it is not a pass.

| Area | Status | Exact reason/evidence boundary |
|---|---|---|
| Source preservation | `passed` | Frozen checkpoint full unittest and existing Global Music Theory release gate passed; original engine and dirty checkout unchanged. |
| Account | `validation_unavailable` | Account lifecycle not implemented; approved regional database/email bindings and real test mailbox unavailable. |
| Region | `validation_unavailable` | 25 regional policy tests and real PostgreSQL realm tests passed; authenticated-user lifecycle and browser evidence pending. |
| CN isolation | `validation_unavailable` | CN resource policy unit tests passed; actual model router, provider failure injection and regional request logs not implemented. |
| Onboarding | `validation_unavailable` | Task 4 UI and live account prerequisites pending. |
| i18n | `validation_unavailable` | Three-locale client implementation and locale sweep pending Task 11. |
| Tutor Explain | `validation_unavailable` | Deterministic engine API passes; orchestration and browser learning flow pending Tasks 6–7. |
| Tutor Practice | `validation_unavailable` | Original student projection and API feedback tested; persisted session/UI sequence pending Task 8. |
| Tutor Check | `validation_unavailable` | API student projection/hint withholding tested; pre-submit DOM/stream/accessibility and DB enforcement pending Task 8. |
| Tutor Deep | `validation_unavailable` | Source/uncertainty/competing-interpretation client flow pending Tasks 6–7. |
| Structured rendering | `validation_unavailable` | Shared TutorResponse validation and block renderer pending Tasks 6–7. |
| MusicXML | `validation_unavailable` | Real synthetic MusicXML/MXL parse/render/event IDs tested at API boundary; storage/upload/selection/browser follow-up pending Task 9. |
| Unsupported score | `validation_unavailable` | API rejects PDF/image/XXE/malformed input; recoverable upload UI E2E pending Task 9. |
| Persistence | `validation_unavailable` | Real PostgreSQL migration/cascade/ownership tests passed; logout-login and application persistence flows pending. |
| Evidence model | `validation_unavailable` | Four permitted states, append-only attempts and ownership tested in PostgreSQL; evidence-transition service/UI pending Task 8. |
| Account export/delete | `validation_unavailable` | Relational cascade tested; account export/deletion orchestration and private object cleanup pending Task 10. |
| Security | `validation_unavailable` | Internal API token/realm/input limits tested; public account/session/object checks and full static/runtime review pending. |
| Rate/cost | `validation_unavailable` | Production request, concurrency and daily-budget controls pending Task 12. |
| Provider outage | `validation_unavailable` | No real provider configured; provider router and recovery E2E pending Tasks 5/12. |
| Theory outage | `validation_unavailable` | Orchestration/failure recovery pending Tasks 6/12; no BFF fallback path exists yet. |
| Accessibility | `validation_unavailable` | Product surfaces and critical keyboard/focus/contrast/reduced-motion checks pending Tasks 7–11. |
| Zoom/width | `validation_unavailable` | Product critical-path 320px/200%-zoom browser checks unavailable; UI not implemented. |
| Responsive | `validation_unavailable` | Required four product screenshot/interaction captures not run; only initial app shell exists. |
| Safari class | `validation_unavailable` | Playwright WebKit product critical path not implemented or run. |
| Visual QA | `validation_unavailable` | Product loading/empty/error states and screenshots unavailable. |
| Runtime health | `validation_unavailable` | No product browser/staging/production critical path exists to inspect. |
| Observability | `validation_unavailable` | Web/theory/provider request correlation and redacted production logs pending Task 12. |
| Performance | `validation_unavailable` | Shell renders without network/model in unit test; production latency measurements unavailable. |
| Rollback | `validation_unavailable` | Disposable SQL migration up/down/up passed; production rollback/package exercise pending Task 13. |
| Production | `validation_unavailable` | No staging or production artifact deployed; product Tasks 4–13 incomplete and approved target/resources unavailable. |
| CN launch | `validation_unavailable` | Actual CN domain/deployment identity and ICP/PSB/generative-AI/privacy review evidence unavailable; public launch not verified. |

## Required critical-path scripts

All eight remain `validation_unavailable`; none were presented as real execution.

1. New Global user: sign up -> verify -> onboarding -> Explain -> Practice -> logout -> login -> history. **Not run:** Complete product routes and authenticated regional integrations are not implemented/configured.
2. New CN user: sign up -> verify -> onboarding -> Explain, while capturing provider-region evidence. **Not run:** Complete product routes and authenticated regional integrations are not implemented/configured.
3. Check-mode item: prove answer/hint is unavailable before submission. **Not run:** Complete product routes and authenticated regional integrations are not implemented/configured.
4. Score: upload a known MusicXML fixture -> render -> select context -> ask a grounded question. **Not run:** Complete product routes and authenticated regional integrations are not implemented/configured.
5. Failure: disable model provider -> recoverable UI. **Not run:** Complete product routes and authenticated regional integrations are not implemented/configured.
6. Failure: break Theory API -> no fabricated deterministic answer. **Not run:** Complete product routes and authenticated regional integrations are not implemented/configured.
7. Accessibility: keyboard-only from sign-in through first practice completion. **Not run:** Complete product routes and authenticated regional integrations are not implemented/configured.
8. Mobile: run 390x844 and 430x932 with virtual-keyboard/composer interaction where tooling permits. **Not run:** Complete product routes and authenticated regional integrations are not implemented/configured.

## Exact integration blockers and input preview

No approved production env path/secret-store binding, regional resources, test mailbox or paid test/provisioning ceiling was supplied. Vercel authentication exists, but read-only search found no matching theory project; authentication alone does not authorize a new paid service or identify resource region.

Provide the approved local env-file path or secret-store names and resource IDs/endpoints without posting secrets in chat. The original authorization to commit/push/deploy is retained; no repeat deployment approval is requested.

| Capability | Global stack | Mainland China stack |
|---|---|---|
| PostgreSQL | Approved Singapore database/secret reference | Approved Beijing database/secret reference |
| Private object storage | Private Singapore bucket/access binding | Private CN bucket/access binding |
| Compute/domain | Approved Global web/BFF and Theory API target | Approved CN web/BFF and Theory API target |
| Model Studio | Approved Singapore endpoint/key reference and internal alias IDs/version | Approved Beijing endpoint/key reference and internal alias IDs/version |
| Transactional email | Region-compatible provider, verified sender, approved test recipient | Region-compatible provider, verified sender, approved test recipient |
| New paid effects | Explicit resource/model test ceiling if new paid provisioning/calls are needed | Same requirement, isolated from Global |

No provider calls, external transactional emails, paid resource creation or production migration were performed. Marketplace discovery was read-only; no mock integration is counted as a real service.

The selected [Vercel Marketplace skill](/Users/ouxianxing/.codex/plugins/cache/openai-curated-remote/vercel/0.21.4/skills/marketplace/SKILL.md) requires building against real environment variables. Its account prerequisite is: “If it needs the user's account or a dashboard/browser step → STOP and ask them to complete it, then continue.” Combined with Task 4’s real-mailbox E2E requirement, missing approved account/resource configuration prevents dependent account integration from meeting its completion contract.

CN public launch remains unverified. No actual approved CN domain/deployment identity or ICP/PSB/generative-AI/privacy obligation-review evidence was supplied. Neither policy unit tests nor code establish those launch gates. Core CN implementation and tenant/provider verification are also unfinished, independently of legal launch gates.

## Recorded rulings

1. Native worktree tooling targets the unrelated chat directory, so use an external manual Git worktree for the explicitly named source repository. This protects the dirty checkout; the tradeoff is no automatic app worktree attachment.
2. Missing production provisioning does not prevent the explicit plan’s offline shell, deterministic API and actual disposable PostgreSQL foundations. They remain local evidence; production adapter refinement may still be needed.
3. Task 4 requires real integration and mailbox verification. Stop dependent implementation until approved bindings/recipient/cost scope are supplied, retain all remaining tasks, and do not substitute mocks. A later full-branch review and full frozen-product acceptance remain required.

## Recovery

Resume the same saved plan at Task 4 from this isolated branch. Retain `.superpowers/sdd/2026-10-03-super-theory-tutor-client/progress.md`, task briefs, raw logs and `.token-pilot/state.json`; do not reuse or modify the dirty source checkout. Preserve the root task ID `super-theory-tutor-mvp-20261003` and all 14 original requirements.

Before a future release, complete Tasks 4–13, conduct the final whole-branch review, freeze the full product candidate, run every applicable matrix row and all eight critical-path scripts, verify production auth/email/providers/persistence/score flows, and update this receipt with actual artifact/deployment identities. Do not promote this shell as the MVP.

Token Pilot provider counters are unavailable after a session/project identity mismatch. Token use, cost and savings remain unknown.
