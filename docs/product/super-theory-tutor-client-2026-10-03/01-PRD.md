# Super Theory Tutor Client — Product Requirements Document

Date: 2026-10-03  
Target: production-ready MVP  
Primary users: independent music-theory learners, conservatory/university students, exam-oriented learners, teachers/students using the tutor informally, and multilingual learners who need terminology/curriculum disambiguation.

## 1. Product thesis

Super Theory Tutor must make the existing Global Music Theory Super Skill usable by a normal learner without requiring knowledge of prompts, CLI commands, model names, source schemas, or the internal tutor framework.

The core jobs are:
1. Understand a theory concept.
2. Ask a contextual follow-up without re-explaining the whole situation.
3. Practice a concept and receive targeted feedback.
4. Check a learner’s answer without leaking the key first.
5. Analyze supported symbolic score material.
6. Reconcile terminology/curriculum differences.
7. Return later and continue from saved learning context.

A generic chat clone fails this brief. The product must embed tutoring directly in the learning/practice/score flow.

## 2. MVP success definition

A first-time user can:
1. Create and verify an account.
2. Complete onboarding in roughly 60–90 seconds without learning prompt syntax.
3. Ask a first music-theory question.
4. Receive a structured explanation that may include notation/keyboard/chord/comparison blocks.
5. Enter Practice or Check mode and complete an item.
6. Upload a MusicXML/MXL score, render it, analyze supported structure, and ask a follow-up grounded in that score.
7. Sign out and return later with history, preferences and practice evidence preserved.

The system must also prove that a Mainland China account does not silently send model traffic to a non-CN provider.

## 3. MVP information architecture

### Public
- Landing
- Sign up
- Verify email
- Sign in
- Forgot/reset password
- Privacy / Terms / data-region explanation
- Service status / support entry

### Authenticated
- Home
- Learn / Workspace
- Practice
- Library / History
- Score Workspace
- Settings
- Account & Data

Desktop primary navigation:
- New
- Learn
- Practice
- Library
- Settings

Mobile:
- content-first single-column workspace
- secondary context in bottom sheet/drawer
- no desktop sidebar squeezed into mobile

## 4. Account lifecycle

### 4.1 Sign-up
Required fields:
- email
- password
- agreement to terms/privacy
- explicit home-region selection: `global` or `cn`

Required behaviors:
- email verification
- password reset
- rate-limited auth attempts
- clear recoverable errors
- sign out
- delete account
- export user data

### 4.2 Home region
Copy must explain:
“Your home region determines where your account and AI requests are processed. It does not determine your language, nationality, curriculum, terminology, or musical tradition.”

Rules:
- never infer home region from nationality
- browser/network location may only suggest a default
- user must confirm
- changing home region later is a controlled migration, not a profile toggle
- CN tenants cannot fall back to a non-CN model provider

### 4.3 Identity providers
MVP:
- email/password

Post-MVP:
- WeChat login
- Google/Apple as region-appropriate additions

MVP must not depend on a Western social-login provider to be usable.

## 5. Onboarding

Onboarding must be skippable except home region and required account/legal fields.

### Step 1 — Home region
- Global
- Mainland China

### Step 2 — Interface language
Launch target:
- English
- 简体中文
- 繁體中文

Important: interface-language availability is separate from verified pedagogical terminology coverage. Simplified Chinese content must pass its own benchmark before launch claims.

### Step 3 — Theory preferences
Optional:
- terminology: UK / US / ask when relevant
- note naming
- solfège: fixed-do / movable-do / ask
- minor movable-do basis: la-based / do-based
- curriculum: General / ABRSM / AP Music Theory / University / Other / Not sure
- explanation depth: concise / normal / detailed

### Step 4 — Interactive “how to use it”
Show four task starters rather than a prompt-engineering tutorial:
- Explain: “Why is this chord V7?”
- Practice: “Give me five secondary-dominant exercises.”
- Check: “Check my Roman-numeral analysis.”
- Deep: “Compare two interpretations of this passage.”

The system asks only genuinely missing context and keeps adaptive questions bounded.

## 6. Home

Primary object: one ask box.

Heading: “What are you working on?”

Suggested actions:
- Explain a concept
- Practice a topic
- Check my answer
- Analyze MusicXML

Below:
- Continue: up to three recent learning sessions
- Practice next: up to two evidence-supported weak/unassessed concepts

Do not add decorative KPI cards, fake streaks, fake mastery meters, model selectors or admin-like chrome.

## 7. Learning Workspace

### 7.1 Desktop layout
Three functional zones:
- small left navigation rail
- central Learning Canvas
- optional right Context panel

### 7.2 Learning Canvas
Responses render typed blocks, not markdown-only blobs:
- prose explanation
- inline formula/theory notation
- score block
- piano-keyboard block
- chord/scale/interval block
- terminology comparison
- curriculum note
- practice item
- hint
- feedback/check result
- source/evidence block
- ambiguity/review-required notice

### 7.3 Context panel
Only show context that changes the current interpretation:
- key/tonic
- selected curriculum/version
- terminology system
- solfège mode
- attached score/source
- assumptions
- evidence/source status

Do not expose implementation internals, provider names or raw chain-of-thought.

## 8. Tutor behaviors

### Explain
- answer promptly
- use deterministic engine outputs when supported
- give a useful example
- optionally offer one understanding check
- do not force Socratic questioning

### Practice
Flow:
1. present original bounded item
2. accept attempt
3. optionally provide staged hint
4. accept revised attempt
5. give explanation/feedback
6. move to a changed/new item

Track hint use and answer exposure.

### Check
- withhold answer/hints until learner submits
- return correct / partly correct / incorrect / insufficient information when supportable
- do not invent scores for open responses
- preserve reviewer-required states

### Deep
- identify prerequisites
- call source/curriculum/terminology reconciliation when needed
- separate sourced fact, deterministic result, interpretation and pedagogical example
- show meaningful uncertainty and competing interpretations
- no hidden reasoning transcript

## 9. Practice product

Practice is a first-class route, not “send a prompt.”

MVP topics come from supported engine capabilities and verified curriculum metadata.

Practice UI must show:
- item progress
- question/prompt
- notation/visual if needed
- response control
- Check answer
- optional Hint
- feedback
- next item

Practice must work without a permanent chat transcript dominating the screen.

## 10. Score Workspace

MVP accepted inputs:
- MusicXML
- MXL where parser/runtime support is verified

Flow:
1. upload
2. validate type/size
3. parse
4. render score
5. preserve source event IDs / measure / voice / written pitch / timing
6. show supported analysis
7. let learner select score context and ask a question

Not in MVP:
- scanned PDF OMR
- score photos
- handwritten notation
- claims that text extraction proves musical notation

Unsupported uploads return a clear explanation and safe next step.

## 11. Terminology & curriculum behavior

The product must preserve existing Super Skill distinctions:
- response language
- UK/US terminology
- curriculum/version
- solfège
- musical tradition
- analytical framework

Do not infer one from another.

When terminology is:
- equivalent: explain mapping
- context-dependent: state context
- disputed: present the dispute
- not equivalent: do not silently translate

No numerical grade equivalence may be invented.

## 12. Learning progress

Persist evidence, not psychological labels.

Allowed evidence states:
- unassessed
- assisted success evidence
- independent success evidence
- delayed/transfer success evidence

Do not display “100% mastered” from one correct attempt.

Persist:
- concept/item/rubric version
- response
- assistance/hints
- answer exposure
- retries
- independent result
- uncertainty
- timestamp

## 13. Library & history

Auto-title sessions by meaningful topic.

Filters:
- Harmony
- Rhythm
- Form
- Aural
- Fundamentals
- Composition
- Exam prep
- Scores

Library sections:
- Recent
- Saved
- Practice
- Scores

## 14. Settings

Sections:
- Account
- Language
- Theory preferences
- Curriculum
- Accessibility
- Data & privacy
- Export data
- Delete account

Reduced motion must be a persistent preference in addition to system preference.

## 15. Global / Mainland China product contract

The user experiences one product and shared interaction model.

Shared:
- product behavior
- schemas
- UX
- theory engine
- regression suite
- release process

Region-specific:
- database
- object storage
- model endpoint/key
- transactional email provider/endpoint
- observability sinks where required
- deployment/domain/legal configuration

CN data/model traffic must remain inside the approved CN stack unless an explicit future cross-border design is separately approved.

## 16. Accessibility

Target WCAG 2.2 implementation guidance.

Must support:
- full keyboard navigation
- visible focus
- accessible names/roles
- meaningful score/visual alternatives
- non-color-only state
- 200% zoom
- 320px minimum-width task completion
- reduced motion
- captions/transcripts for future time-based media
- touch targets appropriate to mobile
- no essential hover-only or drag-only action

Assessment alternatives must not reveal the answer being assessed.

## 17. Reliability and trust

The interface must clearly distinguish:
- deterministic result
- external/source claim
- assistant interpretation
- generated example
- unresolved/review-required result

No completion/verification claim without corresponding runtime evidence.

## 18. Explicit non-goals for MVP
- native iOS/Android
- live voice
- microphone or MIDI performance input
- PDF/photo/handwriting OMR
- official ABRSM question-bank publication
- unverified Grade 6–8 expert marking
- classroom administration
- teacher analytics dashboard
- billing/subscriptions
- social/community
- broad social login matrix
- user-facing model picker
- dozens of unbenchmarked languages

## 19. Launch gates
- real account lifecycle
- real verification email
- all four tutor behaviors
- deterministic theory regression
- score upload/render/analyze/follow-up
- session persistence
- CN routing isolation
- mobile/desktop accessibility
- recoverable provider/database/upload failures
- budget/rate guardrails
- production smoke tests
- Mainland China compliance checklist completed before China public launch
