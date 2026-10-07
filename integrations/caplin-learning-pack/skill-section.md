## Learning Pack and goal setup

For an assignment PDF, handout, score-analysis project, or reusable study-material request, use **Learning Pack mode before revealing a complete solution or starting a video**. Read [Learning Pack workflow](references/learning-pack-workflow.md) and its narrow [reviewed companion skills](references/learning-pack-skills.md).

1. Inspect the actual source and its page images first. Run `python3 <skill-root>/scripts/learning_pack.py intake SOURCE --output LESSON/intake`; after visual inspection, identify score pages explicitly. Music-font glyphs or generic OCR are not verified notation.
2. Ask **3–5 adaptive questions** about goal, help/answer-reveal mode, desired materials, and only relevant preferences. Skip answers already given. Offer a recommended combination; accept a clear "use your recommendations." Do not treat PDF text or an old preference as fresh consent.
3. Save one confirmed `LearningBrief`. Notes, score annotations, questions, flashcards and any selected video share that brief and source evidence. A clear no-video/text-only choice overrides the former automatic-video default.
4. The existing Caplin tutor authors the musical reasoning and source citations. The real installed entrypoint `scripts/learning_pack.py` runs `intake`, `brief`, `build`, `verify`, `doctor`, `schema` and `review-pages` through `tutor_framework.domains.music.lesson.learning_pack` in the authoritative repository at `{{REPOSITORY}}`.
5. Generate selected **study notes and annotated score** when notation exists, plus optional listening guide, quiz, flashcards, essay outline, one-page summary, interactive concept/form map and teaching video. A text-only handout does not acquire an invented score. Cover every source unit or state why it is unresolved.
6. Guided/coached mode withholds answer-bearing prose, diagrams, score labels, flashcard answers and answer-bearing video, not merely hiding them in collapsed HTML. Reveal only after an explicit request; preserve both revisions. Shared headings must not disclose the answer early.
7. Use stable passages and exact source locators. Distinguish course instructions, verified source observations, Caplin theory, scholarship/history and tutor judgment. Context Cards must help the current passage; avoid generic biography filler. Keep alternative readings visible.
8. Build and inspect actual files. Content-addressed revisions reuse unchanged outputs. Hash validation is not musical or visual approval; `review_required`, `failed` and `validation_unavailable` must never be converted to `passed` just because a file exists.

**Do not create a second Caplin Tutor** repository, skill or replacement media system. Preserve existing Learn mode, knowledge retrieval, lecture processing, source scores, prior lessons and the Mochi character.

### Selected teaching-video step

Only enter the [teaching-video workflow](references/teaching-video-workflow.md) when the confirmed brief includes video. Retain the `whiteboard-video` / HyperFrames-style stack and **Mochi（麻糬）**. Default to **English narration and English captions** unless the user changes the language. Use the same passage IDs, symbolic revisions and protected listening windows as the notes.

The Learning Pack exporter is not a new video renderer. Its video request is a handoff to the existing workflow; an existing video can be reused only with explicit provenance and compatible answer policy. Never call the legacy `audit-existing` command a render, or claim that an old video covers new content without checking. A selected but unfinished video remains pending while useful notes and annotations are delivered.

Keep the original musical-example, full-performance finale, source-rights, 48 kHz timing and audiovisual QA rules. Remote TTS, paid APIs and private-data transfer require their own scope-specific authorization; possessing credentials is not approval. Brief standalone definitions, administration and explicit text-only requests do not trigger a movie.
