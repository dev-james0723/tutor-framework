# Super Theory Tutor Client — Design & UX System

## 1. Direction: Living Music Manuscript
The product should feel like an excellent contemporary music-theory book became interactive software.

It is not:
- a SaaS admin dashboard
- a generic chatbot
- a gamified children’s app
- a glowing “AI” demo

It is:
- content-first
- calm
- musically literate
- source-aware
- direct
- tactile when interaction clarifies music

## 2. Visual tokens

### Color roles
- Paper: `#F7F5EF`
- Ink: `#161616`
- Primary cobalt: `#3157E8`
- Secondary neutrals: derive accessible warm grays around the paper/ink pair
- Semantic warning/error/success: use purpose-specific accessible colors; do not reuse primary cobalt for semantic failure states

Exact derived tokens must be contrast-tested rather than copied by eye.

### Type
- Learning/editorial content: high-legibility serif with full required Latin/CJK coverage or a deliberate Latin-serif + CJK-serif pairing
- UI/control text: clean sans with full locale coverage
- core fonts self-hosted or served from region-reliable owned infrastructure
- notation uses established music-font/rendering path

### Layout
Desktop:
- nav rail ~64–80px
- center canvas optimized for reading/notation, not full-width text
- context panel ~280–340px when open

Mobile:
- one content column
- sticky/fixed composer only if safe-area and keyboard behavior are correct
- context becomes sheet
- no horizontal score overflow without an explicit pan/zoom affordance

## 3. Main screens

### Landing
Primary:
- value proposition
- one sample ask field
- one primary CTA
Secondary:
- three concise examples
- no feature-card wall

### Sign up / Sign in
Quiet form.
Region explanation is explicit at sign-up.
Do not mix theory preference onboarding into credential entry.

### Onboarding
One decision per step.
Show progress only if meaningful.
Always allow Skip for optional theory preferences.

### Home
Question-first.
Three recent sessions max.
Two next-practice suggestions max.

### Learning Workspace
Central content owns the screen.
Tutor responses are composed of semantic blocks.
Context panel shows only interpretation-relevant state.

### Practice
Single task focus.
No sidebar chatter.
Hint is secondary.
Feedback appears in the same spatial context as the answer.

### Score Workspace
Score is primary visual object.
Selection must be obvious and keyboard-addressable where technically possible.
Questions can inherit selected measure/event context without manual copy/paste.

## 4. Component behavior

### Composer
States:
- idle
- focused
- attachment present
- sending
- streaming
- offline/retryable
- blocked by rate/budget
- unsupported attachment

### Tutor block
Each block has:
- semantic type
- accessible reading order
- optional provenance
- copy only when useful
- no decorative container if whitespace is enough

### Ambiguity notice
Use when:
- multiple interpretations are valid
- terminology mapping is context-dependent/disputed
- source confidence is insufficient
- score parse needs review

It must not look like a fatal error.

### Evidence disclosure
Collapsed by default for simple answers.
Expanded/visible for source-bound/deep work.
Show source identity/status rather than dumping raw internal metadata.

## 5. Motion
Allowed:
- source-anchored panel transitions
- note/chord highlight sequence
- subtle correct/incorrect state transition
- stream insertion that preserves reading position
- selection continuity between score and explanation

Avoid:
- background decorative motion
- floating gradients/orbs
- mandatory autoplay explanations
- motion as the only state indicator

Typical UI transitions: ~180–220ms; gesture motion can use interruptible spring behavior.
Reduced motion removes spatial animation while preserving state through text/icon/color.

## 6. Content/copy rules
- answer the user before teaching around the answer in Explain mode
- errors tell the user how to recover
- no “magic AI” claims
- no “mastered” label without validated evidence model
- no false certainty
- retain important English theory labels when helpful in Chinese UI
- distinguish “official/source-backed,” “calculated,” “generated example,” and “interpretation”

## 7. Responsive acceptance
Must be manually inspected at:
- 1440x900
- 768x1024
- 430x932
- 390x844
- 320px width sanity check
- 200% zoom

Check:
- no clipped composer
- no hidden primary action
- no score toolbar overflow without access path
- sheets/dialogs fit viewport
- iOS safe areas
- virtual keyboard does not trap/send the composer off-screen
- long CJK and English strings do not overlap
