# Super Theory Tutor Client — Reference Matrix

This is a research/design reference log, not a license to clone visual designs.

## Local authority inspected

### Global Music Theory Super Skill
- Installed: `~/.agents/skills/global-music-theory-super-skill/SKILL.md`
- Runtime reference: `~/.agents/skills/global-music-theory-super-skill/references/implementation.md`
- Source: `src/tutor_framework/domains/music/global_theory/`
Key reuse:
- deterministic theory operations
- curriculum/terminology separation
- source/evidence states
- MusicXML/score workflow
- original practice
- open-response/check semantics
- no-save/privacy boundaries

### Tutor Framework
- `~/.codex/skills/tutor-framework/SKILL.md`
- `references/pedagogy-and-adaptation.md`
- `references/accessibility-and-evaluation.md`
Key reuse:
- Explain / Practice / Check / Deep
- observable evidence states
- media chosen by instructional value
- WCAG 2.2 implementation guidance
- no fixed learning-style inference

### Research skills
- `~/.codex/skills/research/SKILL.md`
- `~/.codex/skills/research-deep/SKILL.md`
Used for structured research discipline, source verification and uncertainty handling.

### UI skills
- `~/.codex/skills/ui-improvement/SKILL.md`
- `~/.claude/skills/better-interface/SKILL.md`
Key principles:
- content is the interface
- no card/button soup
- responsive redesign instead of desktop shrinkage
- evidence-based accessibility and runtime review

### Superpowers 6.4.2
- brainstorming
- writing-plans
- test-driven-development
- verification-before-completion
Used to keep design, planning, execution and completion evidence separate.

## skills.sh candidates researched

High-signal references found via `npx skills find`:
- `anthropics/skills@frontend-design`
- `vercel-labs/agent-skills@web-design-guidelines`
- `leonxlnx/taste-skill@design-taste-frontend`
- `emilkowalski/skills@emil-design-eng`
- `pbakaus/impeccable@impeccable`
- `anthropics/skills@webapp-testing`
- `mattpocock/skills@teach`

No new skill installation is authorized or required by this package. Prefer the already-installed local composite skills first.

## Product/design references

### Musicalysis
URL: https://www.musicalysis.com/
Use as a reference for:
- instrument/score workspace with assistant nearby
- music-native interaction rather than text-only chat
Do not clone its visual identity.

### Tenuto / musictheory.net
URL: https://www.musictheory.net/products/tenuto
Use as a reference for:
- focused drill/practice presentation
- low-chrome question flow
Do not copy proprietary exercise content.

### Khan Academy / Khanmigo learning-flow research
URL: https://blog.khanacademy.org/
Use as a reference for:
- tutoring embedded in the learner’s active task rather than isolated in a separate chat destination
Use product principle only, not content/UI copying.

### Next.js self-hosting
URL: https://nextjs.org/docs/app/guides/self-hosting
Use for:
- deployment architecture and reverse-proxy expectations

### Vercel AI SDK
URL: https://ai-sdk.dev/
Use for:
- streaming transport/provider abstraction patterns
Do not couple domain truth to the SDK.

### shadcn/ui
URL: https://ui.shadcn.com/
Use for:
- accessible composable primitives where they fit
Do not force a library migration if the eventual app scaffold differs.

### Better Auth
URL: https://www.better-auth.com/
Use for:
- self-hosted auth evaluation
- email/password/verification/reset baseline
- future social provider extension
Pin exact package/version only during implementation after security/license verification.

### Alibaba Cloud Model Studio
URL: https://www.alibabacloud.com/help/en/model-studio/
Use for:
- regional model endpoints
- region-scoped credentials/model availability
- Singapore/Beijing deployment research
Exact currently available model IDs must be revalidated during implementation and before release.

### Alibaba Cloud ICP documentation
URL: https://www.alibabacloud.com/help/en/icp-filing/
Use for:
- Mainland China website launch prerequisites

### CAC generative-AI notices
URL: https://www.cac.gov.cn/
Use for:
- current Mainland China generative-AI filing/registration review
Legal/compliance status must be rechecked immediately before public CN launch.

## Reference-asset state
No approved bespoke mockup image exists yet for this client. Therefore:
- no unapproved screenshot is copied into product assets
- no third-party product screenshot is bundled into shipping code
- future Figma/mockup work should follow `03-DESIGN-AND-UX-SYSTEM.md`
