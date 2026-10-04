# Super Theory Tutor Client Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a production-ready responsive Super Theory Tutor Web/PWA that exposes the existing Global Music Theory Super Skill through account-based learning, practice and score workflows with hard Global/Mainland-China regional isolation.

**Architecture:** Add a Next.js/TypeScript web client and BFF plus a thin Python Theory API around the existing `global_theory` domain. Keep deterministic musical reasoning in Python; use a server-only regional model router to turn deterministic/source-grounded results into pedagogical structured blocks. Store each tenant in its selected region with PostgreSQL/object storage/model/email adapters that fail closed across regional boundaries.

**Tech Stack:** Next.js App Router, React, TypeScript, Tailwind, shadcn/ui-compatible primitives, Vercel AI SDK-compatible streaming abstraction, Better Auth, PostgreSQL, Python FastAPI, existing Tutor Framework/Global Music Theory modules, Verovio, pytest/unittest, Vitest, Playwright.

**Spec:** `docs/product/super-theory-tutor-client-2026-10-03/02-ENGINEERING-SPEC.md`

## Global Constraints

- Read the full product package beginning at `docs/product/super-theory-tutor-client-2026-10-03/00-START-HERE.md`.
- Preserve the existing Python theory engine; do not rewrite music-theory calculations in TypeScript.
- Preserve existing unrelated Caplin Learning Pack work in the root checkout. Implementation must begin from a fresh isolated worktree after resolving the newest approved canonical source lineage.
- Account home region is explicit: `global` or `cn`. It is not inferred from nationality or locale.
- CN tenants must fail closed rather than route/fallback to a non-CN provider.
- MVP score intake is MusicXML/MXL only. Do not claim PDF/photo OMR support.
- No user-facing model picker.
- No hidden chain-of-thought display.
- No fake mastery percentage; use the evidence states defined in the PRD.
- Launch app locales: English, Simplified Chinese, Traditional Chinese, with explicit benchmark/review.
- No billing, classroom admin, community, native app, live voice or MIDI input in MVP.
- Mainland China public launch remains gated on the documented legal/compliance checklist.
- Every implementation task follows red -> green -> regression verification.
- Do not claim completion until the acceptance matrix and live production critical paths pass.

## Review Focus

1. **Cross-region leakage:** a CN tenant with a broken Beijing provider config must fail, never use Singapore/global fallback. Add failure-injection coverage in Task 5.
2. **Assessment answer leakage:** Check-mode streaming, accessible descriptions and pre-rendered state must not expose answer/hints before submission. Add E2E coverage in Task 8.
3. **Model/theory disagreement:** a model-generated explanation must not silently override a deterministic theory result or a `review_required` state. Add contract coverage in Task 6.
4. **Unsafe score input:** malformed XML/external entities/unsupported PDF/photo must not reach an unsafe parser or produce a fabricated musical reading. Add upload-security coverage in Task 9.
5. **Deletion completeness:** account deletion must remove/revoke relational data and private score objects according to policy in both regional stacks. Add integration coverage in Task 10.

---

### Task 1: Isolated execution workspace and client skeleton

**Files:**
- Create in fresh worktree: `pnpm-workspace.yaml`
- Create: `apps/web/package.json`
- Create: `apps/web/tsconfig.json`
- Create: `apps/web/next.config.ts`
- Create: `apps/web/src/app/layout.tsx`
- Create: `apps/web/src/app/page.tsx`
- Create: `packages/contracts/package.json`
- Create: `packages/contracts/src/index.ts`
- Test: `apps/web/src/app/__tests__/app-shell.test.tsx`

**Interfaces:**
- Produces: a buildable web app and shared contracts package; no product logic yet.

- [ ] Resolve newest approved source branch/HEAD without mutating the dirty root checkout, then create a fresh isolated worktree using the installed Superpowers worktree workflow.
- [ ] Write the failing app-shell test proving the client renders without model/network availability.
- [ ] Run the test and confirm RED.
- [ ] Add the minimal workspace/client scaffold, strict TypeScript and test runner.
- [ ] Run unit test, typecheck and production build; confirm GREEN.
- [ ] Commit only Task 1 files.

### Task 2: Theory API adapter around existing engine

**Files:**
- Create: `services/theory-api/pyproject.toml`
- Create: `services/theory-api/theory_api/main.py`
- Create: `services/theory-api/theory_api/schemas.py`
- Create: `services/theory-api/theory_api/engine.py`
- Test: `services/theory-api/tests/test_operations.py`
- Test: `services/theory-api/tests/test_health.py`

**Interfaces:**
- Consumes: existing `tutor_framework.domains.music.global_theory` modules.
- Produces: typed HTTP endpoints for interval, scale, chord, meter, solfège, voice-leading, score analysis, practice, curriculum comparison and evidence reconciliation; `/health`; `/version`.

- [ ] Write failing API contract tests for one valid and one ambiguous/unsupported request per required operation family.
- [ ] Run tests; confirm RED without the adapter.
- [ ] Implement a thin adapter that returns typed payload, engine version, warnings, claim/source IDs and review state without duplicating calculation logic.
- [ ] Run API tests and the existing Global Music Theory tests/release gate; confirm GREEN.
- [ ] Commit Task 2.

### Task 3: Regional configuration and PostgreSQL schema

**Files:**
- Create: `apps/web/src/server/region/types.ts`
- Create: `apps/web/src/server/region/policy.ts`
- Create: `apps/web/src/server/db/schema.ts`
- Create: `apps/web/src/server/db/client.ts`
- Create: `apps/web/src/server/db/migrations/0001_initial.sql`
- Test: `apps/web/src/server/region/policy.test.ts`
- Test: `apps/web/src/server/db/schema.test.ts`

**Interfaces:**
- Produces: `HomeRegion = "global" | "cn"`; region-authoritative server context; core PRD tables.

- [ ] Write failing tests that reject missing/invalid region and client attempts to override the authenticated user’s home region.
- [ ] Write schema tests for users, learner profile, conversation/message, evidence, score asset, practice, competency evidence, usage and audit tables.
- [ ] Implement schema/migration and region policy.
- [ ] Verify clean migrate up/down against disposable PostgreSQL and run tests GREEN.
- [ ] Commit Task 3.

### Task 4: Account lifecycle and onboarding

**Files:**
- Create: `apps/web/src/server/auth/config.ts`
- Create: `apps/web/src/server/email/adapter.ts`
- Create: `apps/web/src/app/(auth)/sign-up/page.tsx`
- Create: `apps/web/src/app/(auth)/sign-in/page.tsx`
- Create: `apps/web/src/app/(auth)/verify/page.tsx`
- Create: `apps/web/src/app/(auth)/forgot-password/page.tsx`
- Create: `apps/web/src/app/onboarding/page.tsx`
- Create: `apps/web/src/features/onboarding/OnboardingFlow.tsx`
- Test: `apps/web/e2e/auth-onboarding.spec.ts`

**Interfaces:**
- Consumes: regional DB policy.
- Produces: verified authenticated user with immutable-at-runtime home region and optional learner preferences.

- [ ] Write failing E2E for sign-up -> region -> email verification -> sign-in -> onboarding -> home.
- [ ] Add failure cases for duplicate email, expired verification, reset, unverified account and skipped optional preferences.
- [ ] Implement Better Auth integration and region-compatible email adapter interface.
- [ ] Implement onboarding fields exactly from PRD; locale must not set region and region must not set curriculum.
- [ ] Verify auth E2E in a real test mailbox/provider sandbox and unit/integration suite GREEN.
- [ ] Commit Task 4.

### Task 5: Regional model router with fail-closed isolation

**Files:**
- Create: `apps/web/src/server/ai/model-alias.ts`
- Create: `apps/web/src/server/ai/providers.ts`
- Create: `apps/web/src/server/ai/router.ts`
- Create: `apps/web/src/server/ai/errors.ts`
- Test: `apps/web/src/server/ai/router.test.ts`

**Interfaces:**
- Consumes: authenticated `homeRegion`, model alias `fast|tutor|deep`.
- Produces: server-only stream provider restricted to the region’s allowlist.

- [ ] Write failing tests for Global->Singapore and CN->Beijing routing using mocked provider clients.
- [ ] Add required Review Focus test: break CN provider config and assert a hard regional error with zero calls to any global provider.
- [ ] Add same-region failover test if a second approved provider/model alias is configured; no cross-region fallback.
- [ ] Implement provider registry with region-scoped keys/endpoints and server-only model-ID mapping.
- [ ] Revalidate launch model IDs against current Model Studio region docs at implementation time and record the exact configuration version.
- [ ] Run router tests GREEN.
- [ ] Commit Task 5.

### Task 6: Tutor orchestration and structured response contract

**Files:**
- Create: `packages/contracts/src/tutor.ts`
- Create: `apps/web/src/server/tutor/orchestrator.ts`
- Create: `apps/web/src/server/tutor/prompt-context.ts`
- Create: `apps/web/src/app/api/tutor/stream/route.ts`
- Test: `apps/web/src/server/tutor/orchestrator.test.ts`

**Interfaces:**
- Consumes: user message, tutor mode, explicit learner context, optional score selection.
- Produces: validated streamed `TutorResponse` blocks and evidence links.

- [ ] Write failing contract tests for prose, score, keyboard, theory fact, comparison, practice, source and ambiguity blocks.
- [ ] Write deterministic-first test: supported interval request must call Theory API before the model.
- [ ] Add required Review Focus test: model text conflicting with deterministic result cannot replace the engine fact and must be corrected/blocked by orchestration.
- [ ] Implement bounded context construction and structured-output validation with one repair attempt.
- [ ] Implement safe fallback for invalid model structure.
- [ ] Run tests GREEN.
- [ ] Commit Task 6.

### Task 7: Learning Workspace UI

**Files:**
- Create: `apps/web/src/app/(app)/learn/page.tsx`
- Create: `apps/web/src/components/app/AppShell.tsx`
- Create: `apps/web/src/features/tutor/LearningCanvas.tsx`
- Create: `apps/web/src/features/tutor/ContextPanel.tsx`
- Create: `apps/web/src/features/tutor/Composer.tsx`
- Create: `apps/web/src/features/tutor/TutorBlockRenderer.tsx`
- Create: `apps/web/src/styles/tokens.css`
- Test: `apps/web/e2e/learn-workspace.spec.ts`

**Interfaces:**
- Consumes: streamed TutorResponse blocks.
- Produces: desktop three-zone workspace and mobile content-first workspace.

- [ ] Write failing E2E for first ask, stream, retryable error and context sheet.
- [ ] Implement Living Music Manuscript tokens and semantic block renderer.
- [ ] Keep one dominant action per context; no model picker/card soup.
- [ ] Implement reduced-motion path and mobile context sheet.
- [ ] Capture 1440x900 and 390x844 screenshots; fix visible overlap/overflow before GREEN.
- [ ] Run accessibility smoke, E2E and build GREEN.
- [ ] Commit Task 7.

### Task 8: Practice, Check and evidence progression

**Files:**
- Create: `apps/web/src/app/(app)/practice/page.tsx`
- Create: `apps/web/src/features/practice/PracticeSession.tsx`
- Create: `apps/web/src/features/practice/PracticeItem.tsx`
- Create: `apps/web/src/features/practice/AttemptFeedback.tsx`
- Create: `apps/web/src/server/practice/service.ts`
- Create: `apps/web/src/app/api/practice/sessions/route.ts`
- Create: `apps/web/src/app/api/practice/[id]/attempt/route.ts`
- Test: `apps/web/e2e/practice-check.spec.ts`

**Interfaces:**
- Produces: original practice flow, hints, attempts and allowed evidence states.

- [ ] Write failing E2E for attempt -> optional hint -> retry -> feedback -> changed next item.
- [ ] Add required Review Focus test proving Check mode answer/hint is absent from DOM, streamed payload and accessible description before submit.
- [ ] Implement evidence transitions: unassessed, assisted success, independent success, delayed/transfer success.
- [ ] Ensure generated/open responses do not receive invented grades.
- [ ] Run practice E2E and DB-state assertions GREEN.
- [ ] Commit Task 8.

### Task 9: MusicXML/MXL Score Workspace

**Files:**
- Create: `apps/web/src/app/(app)/scores/[id]/page.tsx`
- Create: `apps/web/src/features/score/ScoreViewer.tsx`
- Create: `apps/web/src/server/scores/service.ts`
- Create: `apps/web/src/server/storage/adapter.ts`
- Create: `apps/web/src/app/api/scores/upload/route.ts`
- Test: `apps/web/e2e/score-workspace.spec.ts`
- Add fixtures under: `apps/web/e2e/fixtures/scores/`

**Interfaces:**
- Consumes: MusicXML/MXL only.
- Produces: region-stored immutable score asset, parsed source-event IDs, sanitized rendered score and selection context for tutor.

- [ ] Write failing E2E for known MusicXML upload -> render -> select context -> grounded ask.
- [ ] Add required Review Focus cases for malformed XML, XXE attempt, oversized input, PDF and image upload; assert safe rejection/no fake analysis.
- [ ] Implement hashing, allowlist, regional storage, Theory API parse and sanitized Verovio rendering.
- [ ] Verify source event identity survives UI selection.
- [ ] Run score E2E and security fixtures GREEN.
- [ ] Commit Task 9.

### Task 10: Library, settings, data export and deletion

**Files:**
- Create: `apps/web/src/app/(app)/library/page.tsx`
- Create: `apps/web/src/app/(app)/settings/page.tsx`
- Create: `apps/web/src/server/account/export.ts`
- Create: `apps/web/src/server/account/delete.ts`
- Create: `apps/web/src/app/api/account/export/route.ts`
- Create: `apps/web/src/app/api/account/route.ts`
- Test: `apps/web/e2e/account-data.spec.ts`

**Interfaces:**
- Produces: saved sessions/scores/practice browsing, preference updates, export and deletion.

- [ ] Write failing E2E for logout/login persistence and meaningful session titles/filters.
- [ ] Write export test with only the current user’s data.
- [ ] Add required Review Focus deletion test proving relational data and private score-object cleanup/revocation.
- [ ] Implement settings without allowing direct home-region flip; region migration stays unavailable in MVP UI.
- [ ] Run E2E/integration GREEN.
- [ ] Commit Task 10.

### Task 11: Internationalization, accessibility and PWA shell

**Files:**
- Create: `packages/i18n/src/en.ts`
- Create: `packages/i18n/src/zh-CN.ts`
- Create: `packages/i18n/src/zh-TW.ts`
- Create: `apps/web/public/manifest.webmanifest`
- Create: `apps/web/e2e/accessibility.spec.ts`
- Create: `apps/web/e2e/locales.spec.ts`

**Interfaces:**
- Produces: complete MVP chrome in three locales and installable web app metadata.

- [ ] Add locale sweep failing on missing keys or hard-coded user-facing English in owned MVP surfaces.
- [ ] Add keyboard-only critical path and 320px/200%-zoom checks.
- [ ] Implement self-hosted/owned font delivery suitable for Latin + CJK; no core Google Fonts dependency.
- [ ] Validate visible focus, accessible names, contrast and reduced motion.
- [ ] Verify mobile composer/safe-area behavior in WebKit/Safari class.
- [ ] Run locale/accessibility E2E GREEN and capture representative screenshots.
- [ ] Commit Task 11.

### Task 12: Usage controls, observability and failure recovery

**Files:**
- Create: `apps/web/src/server/limits/rate.ts`
- Create: `apps/web/src/server/limits/budget.ts`
- Create: `apps/web/src/server/observability/request-context.ts`
- Create: `apps/web/src/server/observability/logging.ts`
- Create: `apps/web/src/components/system/RecoverableError.tsx`
- Test: `apps/web/src/server/limits/limits.test.ts`
- Test: `apps/web/e2e/failure-recovery.spec.ts`

**Interfaces:**
- Produces: request IDs, region-safe redacted logs, rate/concurrency/daily caps and recoverable failure UX.

- [ ] Write failing tests for rate, concurrent-stream and budget caps.
- [ ] Write failure E2E for model timeout, theory outage, database transient failure and upload failure.
- [ ] Ensure theory outage cannot fall through to model-fabricated deterministic answers.
- [ ] Implement bounded retry/circuit-breaker semantics only for retry-safe failures.
- [ ] Verify logs contain IDs/status/region but not raw credentials or private score contents.
- [ ] Run tests GREEN.
- [ ] Commit Task 12.

### Task 13: Regional deployment packages

**Files:**
- Create: `deploy/global/README.md`
- Create: `deploy/cn/README.md`
- Create: `deploy/docker/web.Dockerfile`
- Create: `deploy/docker/theory-api.Dockerfile`
- Create: `deploy/config/global.example.env`
- Create: `deploy/config/cn.example.env`
- Create: `docs/product/super-theory-tutor-client-2026-10-03/06-DEPLOYMENT-AND-COMPLIANCE.md`

**Interfaces:**
- Produces: same application artifacts with separated regional configuration and explicit launch blockers.

- [ ] Build immutable web/theory images and run local container smoke.
- [ ] Document Global Singapore and Mainland China Beijing resource mapping without storing secrets.
- [ ] Add startup validation that refuses mixed/missing regional provider configuration.
- [ ] Document rollback, migration compatibility and exact deployment evidence required.
- [ ] Record Mainland China ICP/PSB/generative-AI/privacy gates as external launch conditions; do not falsely mark them complete from code.
- [ ] Commit Task 13.

### Task 14: Full acceptance, staging and production release

**Files:**
- Update only evidence/receipt files created for release; do not weaken tests.
- Create: `docs/releases/SUPER-THEORY-TUTOR-MVP-RECEIPT.md`

**Interfaces:**
- Consumes: final frozen candidate commit.
- Produces: evidence-backed release receipt.

- [ ] Freeze candidate source identity and run the existing full Tutor Framework/Global Music Theory tests and release gate.
- [ ] Run web unit/integration/typecheck/lint/build once against final code.
- [ ] Run Playwright critical paths for Global and CN routing configs.
- [ ] Validate preview/staging first; prefer promotion of verified artifact where the deployment platform supports it.
- [ ] Capture UI at 1440x900, 768x1024, 430x932 and 390x844 plus required error/loading states.
- [ ] Run targeted accessibility checks and WebKit/Safari-class critical path.
- [ ] Inspect browser console, failed network requests and deployment/runtime logs.
- [ ] Run the eight critical-path scripts from `05-ACCEPTANCE-MATRIX.md`.
- [ ] Verify real production account creation, verification email, first ask, practice, persistence and MusicXML flow.
- [ ] For Mainland China, do not enable public launch until external compliance rows are actually satisfied; record blocked if not.
- [ ] Write release receipt containing production URLs/environments, commit/branch, schema version, regional model-alias config version, tested browsers/devices, screenshots, commands/results, physical-vs-emulated disclosure, blockers/unverified items.
- [ ] Only after all applicable rows pass, report the MVP production-ready.
