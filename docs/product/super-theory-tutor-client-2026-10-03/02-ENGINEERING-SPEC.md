# Super Theory Tutor Client — Engineering Specification

Date: 2026-10-03  
Authority: implements `01-PRD.md` against the existing Tutor Framework / Global Music Theory Super Skill.

## 1. Architecture

### 1.1 Components

```text
Browser / PWA
    |
    v
Next.js Web App + BFF
    |---- Auth service
    |---- Session / conversation service
    |---- Regional model router
    |---- Upload / object-storage adapter
    |---- Usage / rate / budget guard
    |
    +----> Python Theory API
    |        |
    |        +--> existing global_theory modules
    |        +--> MusicXML / engraving / evidence
    |
    +----> Regional PostgreSQL
    +----> Regional object storage
    +----> Regional transactional email
    +----> Regional model endpoint
```

### 1.2 Monorepo shape

Add a client surface without moving or rewriting the existing Python domain code.

Recommended:
```text
apps/
  web/
services/
  theory-api/
packages/
  ui/
  contracts/
  i18n/
src/tutor_framework/domains/music/global_theory/   # existing authority
tests/
docs/
```

If the repository has a stronger existing layout at implementation time, preserve it, but keep the same responsibility boundaries.

## 2. Technology decisions

### Web
- Next.js App Router
- TypeScript strict mode
- React
- Tailwind CSS
- shadcn/ui primitives where they reduce work
- Vercel AI SDK or equivalent transport abstraction for streamed model responses
- PWA manifest + installability; offline read-only shell only if verified within scope

### Auth
Preferred MVP: Better Auth self-hosted, email/password, email verification, reset flow.
Do not make Google/Apple/WeChat mandatory for sign-up.

### Data
- PostgreSQL per home region
- migration-managed schema
- no production multi-user reliance on the existing single-writer SQLite exam bank
- if existing exam-bank semantics are needed, port the schema/append-only invariants behind a storage interface and preserve revision/origin rules

### Theory service
- Python FastAPI (or equally thin Python HTTP layer) wrapping existing modules
- typed request/response schemas
- no duplicated musical calculations in the web layer
- deterministic operations remain testable without any LLM

### Score rendering
- existing Verovio path where verified
- sanitize/render SVG safely
- source IDs retained from parse through UI selection

## 3. Regional deployment architecture

### Global tenant
Launch target:
- application deployment reachable outside Mainland China
- Model Studio region: Singapore
- PostgreSQL: Singapore
- object storage: Singapore
- transactional email: region-compatible provider/endpoint

### Mainland China tenant
Launch target:
- China-hosted application stack when legal/operational prerequisites are met
- Model Studio region: Beijing
- PostgreSQL: Mainland China
- object storage: Mainland China
- transactional email: Mainland China endpoint/provider

### Region invariant
Persist:
`user.home_region = "global" | "cn"`

Provider policy:
- CN tenant: only providers marked `cn_approved=true` and endpoints explicitly configured for CN
- Global tenant: only global region pool
- missing region configuration: fail closed
- fallback must never cross the tenant boundary
- migration of home region is an administrative data-migration workflow, not a settings toggle

Add tests that deliberately break provider config and prove CN requests are blocked rather than rerouted.

## 4. Model abstraction

User-facing product names:
- Fast
- Tutor
- Deep

Do not expose raw provider model IDs in normal UI.

Launch mapping may use:
- Fast -> Qwen fast/flash class
- Tutor -> Qwen balanced/plus class
- Deep -> Qwen max/reasoning class

Exact model IDs belong in region-scoped config and can change without UI/database migration.

Interface:
```ts
type TutorMode = "fast" | "tutor" | "deep";
type HomeRegion = "global" | "cn";

interface ModelRouter {
  stream(request: TutorModelRequest, context: RoutingContext): AsyncIterable<TutorEvent>;
}
```

Routing context must include home region and purpose. Provider selection is server-only.

Never send raw API credentials to the client.

## 5. Deterministic-first orchestration

For supported operations:
1. classify intent
2. validate explicit musical inputs
3. call the typed Theory API
4. receive deterministic result + evidence/status
5. construct a bounded pedagogical context
6. ask the model to explain/adapt
7. render typed UI blocks
8. persist conversation + evidence links

Examples:
- interval
- scale
- chord
- meter
- solfège
- bounded voice-leading checks
- score-event facts

The model may explain the result but may not override it silently.

For unsupported/ambiguous tasks, keep `review_required`, `unsupported`, or uncertainty states visible.

## 6. Theory API

Minimum endpoints or equivalent RPC contracts:

```text
POST /v1/theory/interval
POST /v1/theory/scale
POST /v1/theory/chord
POST /v1/theory/meter
POST /v1/theory/solfege
POST /v1/theory/voice-leading
POST /v1/score/analyze
POST /v1/practice/generate
POST /v1/practice/check
POST /v1/curricula/compare
POST /v1/evidence/reconcile
GET  /health
GET  /version
```

Each response includes:
- request ID
- engine version
- result status
- typed payload
- warnings
- claim/source IDs where applicable
- review-required flag
- no hidden prose dependency

## 7. Web BFF API

Suggested routes:
```text
POST /api/tutor/stream
POST /api/practice/sessions
POST /api/practice/:id/attempt
POST /api/scores/upload
GET  /api/scores/:id
GET  /api/conversations
POST /api/conversations
GET  /api/settings
PATCH /api/settings
POST /api/account/export
DELETE /api/account
```

All authenticated routes derive tenant/home region from server-side identity. Never trust a client-supplied region header as authority.

## 8. Core database schema

### users
- id
- email_normalized
- home_region
- email_verified_at
- created_at
- deleted_at

### learner_profiles
- user_id
- locale
- terminology_system
- note_naming
- solfege_system
- minor_do_basis
- curriculum_id
- curriculum_version
- explanation_depth
- reduced_motion
- created_at / updated_at

### conversations
- id
- user_id
- title
- primary_topic
- created_at / updated_at / archived_at

### messages
- id
- conversation_id
- role
- mode
- content_json
- model_alias
- provider_request_id_redacted
- created_at

### evidence_links
- id
- message_id
- claim_id
- source_id
- evidence_type
- status

### score_assets
- id
- user_id
- storage_key
- sha256
- mime_type
- original_filename
- parse_status
- engine_version
- created_at

### practice_sessions
- id
- user_id
- topic
- curriculum_id/version
- status
- started_at / completed_at

### practice_attempts
- id
- practice_session_id
- item_id
- rubric_version
- response_json
- hints_used
- answer_exposed
- attempt_number
- result_state
- uncertainty
- created_at

### competency_evidence
- id
- user_id
- concept_id
- item_id
- evidence_state
- practice_attempt_id
- observed_at
- notes_json

### usage_ledger
- id
- user_id
- region
- model_alias
- input_units
- output_units
- estimated_cost
- created_at

### audit_events
- id
- user_id nullable
- event_type
- request_id
- region
- safe_metadata_json
- created_at

Passwords/session secrets are managed by the auth subsystem and must not be duplicated into application tables.

## 9. Structured tutor response contract

Model output should be constrained to a typed envelope such as:

```ts
type TutorBlock =
  | { type: "prose"; markdown: string }
  | { type: "score"; scoreAssetId: string; focus?: ScoreFocus }
  | { type: "keyboard"; notes: string[]; labels?: string[] }
  | { type: "theory_fact"; operationId: string; data: unknown }
  | { type: "comparison"; rows: ComparisonRow[] }
  | { type: "practice"; practiceItemId: string }
  | { type: "source"; evidenceIds: string[] }
  | { type: "warning"; kind: "ambiguity"|"review_required"|"unsupported"; text: string };

interface TutorResponse {
  mode: "explain"|"practice"|"check"|"deep";
  blocks: TutorBlock[];
  followUps: string[];
}
```

Server validates the envelope. Invalid structured output receives one bounded repair attempt, then a safe text/error fallback.

## 10. Prompt/orchestration policy

System context includes only what is necessary:
- locale
- explicit theory preferences
- selected curriculum/version
- current score selection
- deterministic operation output
- relevant evidence excerpts/IDs
- current tutor mode

Never include:
- unrelated private data
- raw credentials
- hidden database records
- hidden chain-of-thought instructions to be shown to users

Tutor model rules:
- state assumptions
- do not invent missing octave/style/curriculum
- never promote generated examples to source facts
- preserve competing interpretations
- answer directly in Explain
- withhold answer in Check until submission
- treat scores/grades conservatively

## 11. MusicXML workflow

1. receive file
2. enforce allowlist and size limit
3. hash bytes
4. store in correct regional object store
5. pass immutable object/bytes to Theory API
6. parse with existing score workflow
7. persist parse status and engine version
8. render sanitized score SVG
9. expose stable selectable event IDs
10. allow question with selected event/measure context

MVP hard failure:
- unsupported PDF/photo
- malformed XML
- oversized file
- parse ambiguity requiring unsupported OMR

Never run active XML external entities or unsafe embedded content.

## 12. Auth/security

- server-side sessions
- CSRF protection appropriate to auth library
- secure/httpOnly/sameSite cookies
- email verification before persistent learning data actions except minimal onboarding state
- rate limit sign-in, reset and tutor endpoints
- credential secrets only in server secret stores
- region-specific secrets cannot be loaded into the wrong deployment
- audit account deletion/export
- soft-delete period only if disclosed; otherwise delete according to policy
- object access via authorization checks / signed URLs with short TTL
- attachment scanning/validation as appropriate
- CSP and output sanitization for rendered markdown/SVG

## 13. Cost/reliability controls

Per-user:
- request rate limit
- concurrent stream limit
- daily usage cap for free/MVP policy

System:
- region budget cap
- provider timeout
- bounded retry on retry-safe errors only
- circuit breaker
- model alias failover only within same approved region
- backpressure for theory/model queues
- idempotency key for practice submission and file ingest
- request correlation IDs

Failure UX must distinguish:
- connection lost
- model unavailable
- theory service unavailable
- upload invalid
- processing/review required
- budget/rate limited

No generic “Something went wrong” dead end.

## 14. Observability

Metrics:
- auth success/failure
- verification email delivery
- tutor first-token latency / total latency
- Theory API latency/errors
- model errors/timeouts
- stream disconnects
- score parse/render failures
- practice completion
- region routing decisions
- blocked cross-region attempts
- cost by model alias/region
- frontend Core Web Vitals

Logs:
- redact prompts and private musical uploads by default
- log IDs/statuses, not full private content
- region-safe sink
- correlation ID across web -> theory -> provider

## 15. Internationalization

- locale segment or locale preference must be explicit
- all app chrome localizable
- no English strings embedded in components
- technical music terms can carry original-language labels
- CJK typography and line-height verified
- text expansion verified
- no locale inferred from home region
- source terminology and UI translation remain separate

Launch locales require human/benchmark review for core onboarding, account, tutor-control and error copy.

## 16. Design-system implementation

Tokens:
- paper background
- ink
- subdued ink
- cobalt action
- semantic success/warning/error
- 4/8px spacing base
- restrained radius hierarchy
- flat base surfaces; elevation only for true floating layers

Component families:
- AppShell
- LearningCanvas
- ContextPanel / ContextSheet
- Composer
- TutorBlock renderer
- ScoreViewer
- KeyboardViz
- TheoryFact
- PracticeItem
- AttemptFeedback
- EvidenceDisclosure
- AmbiguityNotice
- SessionList
- PreferenceForm

Rules:
- one dominant action per local context
- progressive disclosure for secondary controls
- no essential drag-only behavior
- motion under ordinary interactions should feel immediate and interruptible
- reduced-motion path is complete, not partial

## 17. Accessibility engineering

Required tests:
- keyboard through sign-up, onboarding, ask, practice, upload, settings
- visible focus
- icon-only accessible names
- error association with fields
- announcements for streamed completion and async upload state without excessive chatter
- score/keyboard text alternative strategy
- 200% zoom
- 320px width
- reduced motion
- contrast
- no answer leakage in assessment alt text

## 18. Compliance/product launch notes for Mainland China

Treat as launch gates, not code assumptions:
- ICP filing for Mainland China hosted public website where applicable
- PSB filing where applicable
- review current generative-AI filing/registration/display obligations for the exact service model and distribution method
- privacy/data-retention notices matching actual CN architecture
- approved domain/network/CDN path

Engineering must expose deployment region/config evidence so compliance review can verify actual data/model routing.

## 19. Migration strategy for existing SQLite exam semantics

Do not point the multi-user web app at the current single-writer SQLite store.

If MVP needs exam/source layers:
1. define storage interface around revision/origin/lock semantics
2. write contract tests against current SQLite implementation
3. implement PostgreSQL adapter
4. run parity fixtures
5. preserve append-only answer/source origins
6. preserve active exam-lock behavior
7. do not import private/local data automatically

For MVP, features not required by public flows may stay behind a disabled capability flag rather than forcing migration of the entire private exam bank.

## 20. Feature flags

At minimum:
- `score_upload_enabled`
- `deep_mode_enabled`
- `cn_public_launch_enabled`
- `wechat_login_enabled`
- `pdf_omr_enabled` default false
- `official_exam_bank_enabled` default false

Flags are server-authoritative.

## 21. Testing strategy

### Unit
- routing
- schemas
- preference normalization
- practice evidence transitions
- auth helpers
- structured-response validation

### Existing deterministic regression
Run current global theory unit/release gates unchanged before and after client work.

### Integration
- web <-> theory API
- auth <-> DB
- upload <-> object store <-> theory parse
- model router with provider mocks
- regional config fail-closed tests

### E2E
- sign up -> verify -> onboarding -> ask
- practice attempt/hint/check
- Check mode answer withholding
- MusicXML upload -> render -> question
- logout/login persistence
- account export/delete
- model outage recovery
- CN account cross-region block

### Browser/device
- desktop 1440x900
- mobile 390x844
- mobile 430x932
- tablet 768x1024 when relevant
- Safari/WebKit class for mobile-sensitive flows

### Visual QA
Capture baseline/after screenshots for:
- landing/auth
- onboarding
- home
- learning canvas
- practice
- score workspace
- mobile context sheet
- loading/error/empty states

## 22. Performance targets

Initial production targets to validate and tune:
- app shell usable without waiting for model response
- p75 LCP <= 2.5s on representative production path where feasible
- first streamed tutor token target <= 2.5s under normal provider health
- deterministic theory endpoint p95 <= 500ms for simple operations
- no long main-thread block from score rendering; large-score behavior measured and bounded

If real measurements disprove these targets, record evidence and adjust deliberately rather than hiding failures.

## 23. Rollback/compatibility

- migrations backward-compatible for one deploy window where feasible
- regional config changes separately reversible
- feature flags disable high-risk client capabilities
- theory engine existing CLI remains functional
- no destructive migration of existing local/private stores
- deployment records exact commit + schema version + model-alias config version

## 24. Definition of Done

Production-ready MVP is complete only when `05-ACCEPTANCE-MATRIX.md` passes with fresh evidence and the production critical path is verified. Commit, push, merge or deployment alone is not completion.
