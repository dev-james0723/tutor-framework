# Super Theory Tutor Client — Start Here

Status: design/specification package only. No product code has been changed by this package.

## Source identity at packaging time
- Repository: `/Users/ouxianxing/Projects/tutor-framework`
- Branch: `feat/global-music-theory-super-skill-20261002`
- HEAD observed before packaging: `b13eeedd9765`
- Existing unrelated dirty/untracked Caplin Learning Pack work must be preserved and must not be reset, stashed, cleaned, overwritten, or folded into this project.

## Product mission
Turn the existing Global Music Theory Super Skill into a production-ready responsive client that works as one product worldwide, including Mainland China, without reducing the existing deterministic theory engine to a generic chat wrapper.

The client is a **Music Theory Workspace + AI Tutor + Practice Engine**. Conversation is one interaction surface, not the product architecture.

## Canonical authority
Read in this order:
1. `01-PRD.md`
2. `02-ENGINEERING-SPEC.md`
3. `03-DESIGN-AND-UX-SYSTEM.md`
4. `04-REFERENCE-MATRIX.md`
5. `05-ACCEPTANCE-MATRIX.md`
6. `../../superpowers/plans/2026-10-03-super-theory-tutor-client.md`

Existing domain authority:
- `src/tutor_framework/domains/music/global_theory/`
- `docs/research/2026-10-01-global-music-theory/`
- `tools/global_music_theory_gate.py`
- `~/.agents/skills/global-music-theory-super-skill/SKILL.md` (installed copy, read-only reference)
- `~/.agents/skills/global-music-theory-super-skill/references/implementation.md` (installed copy, read-only reference)

## Frozen MVP decisions
- Ship as a responsive Web App / PWA first. No native iOS/Android app in MVP.
- Reuse the Python Global Music Theory engine. Do not rewrite musical logic in TypeScript.
- Support three primary tutor behaviors plus one advanced behavior: Explain, Practice, Check, Deep.
- MusicXML/MXL score upload is in MVP. Scanned PDF/photo/handwriting OMR is not.
- Account creation is mandatory for persistence. Email/password + verification + reset is the MVP auth baseline.
- User explicitly chooses account home region: Global or Mainland China. Language, curriculum and musical convention are separate choices.
- Region selection is a data-residency / provider-routing decision, never inferred from nationality.
- Model provider architecture is region-aware and provider-neutral. Launch default: Alibaba Cloud Model Studio with Singapore for Global and Beijing for Mainland China.
- Mainland China requests must fail closed rather than silently route to a non-CN provider.
- No user-facing model picker in MVP.
- Progress uses evidence states, not fake universal “mastery” percentages.
- No billing, teacher dashboard, community/social layer, live voice, MIDI input, official ABRSM exam-bank claims, or unsupported Grade 6–8 marking in MVP.

## Visual direction
“Living Music Manuscript”: interactive music-textbook clarity with product-grade software behavior.
- Warm paper-like content surface.
- Near-black ink.
- Cobalt as the primary interactive accent.
- Restrained semantic red for errors/conflicts.
- Editorial serif for learning content, clean sans for controls.
- Self-host CJK-capable fonts; do not depend on Google Fonts CDN for core typography.
- Avoid generic AI purple gradients, glow, card soup, button soup and decorative dashboards.
- Motion must explain state or musical causality and honor reduced motion.

## Critical implementation rule
LLM output is not the musical truth source. For supported deterministic operations, the data path is:

`user intent -> typed theory operation -> deterministic result/evidence -> tutor model explanation -> structured UI`

For disputed or source-bound topics, preserve the engine’s evidence, terminology and review states rather than forcing one answer.

## Reference-image note
No bespoke client mockup images were approved in the current design pass, so this package does not invent or silently adopt visual assets. `04-REFERENCE-MATRIX.md` records the external interaction/design references that informed the system. New screenshots or mockups must be treated as references until explicitly approved.
