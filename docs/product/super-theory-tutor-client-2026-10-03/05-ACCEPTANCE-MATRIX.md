# Super Theory Tutor Client — Acceptance Matrix

Every row requires fresh evidence from the final candidate. “Implemented” is not a pass condition.

| Area | Required acceptance | Evidence |
|---|---|---|
| Source preservation | Existing Global Music Theory CLI/runtime regression remains green | full relevant unit suite + release gate output |
| Account | Sign up, verification, sign in, reset, sign out work | E2E + real transactional email in staging/prod |
| Region | Home region is explicit and persisted | DB/API evidence + E2E |
| CN isolation | CN tenant cannot call/fallback to non-CN provider | integration failure-injection + request logs |
| Onboarding | First user can finish/skip optional steps and reach first ask | E2E desktop/mobile |
| i18n | English, Simplified Chinese, Traditional Chinese app chrome complete for MVP routes | locale sweep + screenshot QA |
| Tutor Explain | deterministic-supported question uses engine result and coherent explanation | contract test + E2E |
| Tutor Practice | attempt -> hint optional -> retry -> feedback -> next changed item | E2E + DB evidence |
| Tutor Check | answer remains hidden until submission | E2E regression |
| Tutor Deep | source/uncertainty/competing interpretation shown when required | fixture + E2E |
| Structured rendering | typed blocks validate; invalid model output fails safely | unit/integration |
| MusicXML | upload -> parse -> render -> analyze -> contextual follow-up | real fixture E2E |
| Unsupported score | PDF/photo gives recoverable unsupported path, no fake OMR claim | E2E |
| Persistence | conversation/preferences/practice survive logout-login | E2E |
| Evidence model | progress states use allowed evidence labels, no fake mastery | DB/UI test |
| Account export/delete | user can export and delete own data | integration + E2E + storage cleanup evidence |
| Security | no client API keys; auth/session/object checks enforced | static/runtime review |
| Rate/cost | limits and safe budget behavior work | integration/failure injection |
| Provider outage | recoverable error, no duplicate unsafe retries | integration + E2E |
| Theory outage | recoverable error; model does not fabricate deterministic result | integration |
| Accessibility | keyboard/focus/names/contrast/reduced-motion tested | automated + manual task checks |
| Zoom/width | critical path at 200% zoom and 320px | browser evidence |
| Responsive | 1440x900, 768x1024, 430x932, 390x844 | screenshot + interaction evidence |
| Safari class | mobile-sensitive path works in WebKit/Safari class | test record |
| Visual QA | no clipping/overlap/overflow; loading/empty/error states inspected | screenshots/diffs |
| Runtime health | no unexplained console errors/failed requests on critical path | browser/network evidence |
| Observability | request IDs connect web/theory/provider without leaking private prompt data | staging/prod log sample |
| Performance | app shell does not wait for model; latency targets measured | production/staging metrics |
| Rollback | app/schema/model-config rollback path documented and exercised where feasible | release receipt |
| Production | live domain HTTPS critical path passes | production smoke record |
| CN launch | ICP/PSB/generative-AI/privacy obligations explicitly reviewed for actual deployment | launch checklist; not inferred from code |

## Required final critical-path scripts

1. New Global user: sign up -> verify -> onboarding -> Explain -> Practice -> logout -> login -> history.
2. New CN user: sign up -> verify -> onboarding -> Explain, while capturing provider-region evidence.
3. Check-mode item: prove answer/hint is unavailable before submission.
4. Score: upload a known MusicXML fixture -> render -> select context -> ask a grounded question.
5. Failure: disable model provider -> recoverable UI.
6. Failure: break Theory API -> no fabricated deterministic answer.
7. Accessibility: keyboard-only from sign-in through first practice completion.
8. Mobile: run 390x844 and 430x932 with virtual-keyboard/composer interaction where tooling permits.

## Completion rule
Do not say “done,” “shipped,” “production-ready,” or equivalent until every applicable row above has fresh evidence. Report blockers and unverified rows explicitly.
