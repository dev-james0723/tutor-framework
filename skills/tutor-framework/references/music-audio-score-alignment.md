# Music lecture audio → score alignment

Use this reference when a tutor receives a lecture recording that contains both
spoken explanation and musical demonstration.

## Evidence pipeline

1. Preserve the original audio reference.
2. Segment the timeline into speech, music, speech-over-music, silence/noise, or
   unknown regions. Every region keeps start/end timestamps.
3. Never replace a musical passage with only a generic "[music]" marker.
4. If the work/score is known, attempt score alignment first and create
   audio-time → measure/beat anchors.
5. Automatic music transcription (AMT) may add note hypotheses. Treat pitch,
   onset, offset, voice, rhythm, and chord estimates as reviewable evidence.
6. Only reconstruct a provisional ScoreIR when measure/beat quantization already
   exists. Do not invent barlines, rests, meter, voices, or missing notes.
7. Send ambiguous/polyphonic/low-confidence passages to human review.

## Provenance

Keep these layers distinct:

- authoritative or visually verified score evidence;
- audio-derived notes and score-alignment evidence;
- instructor/course interpretation from speech or transcript;
- the tutor's own analytical judgment.

A professor's explanation does not rewrite the score. An AMT output does not
become a verified score merely because it looks plausible.

## Adapter contract

The public framework stays dependency-free. Concrete runtimes plug into
AudioSegmenter, AudioTranscriber, ScoreAligner, or ScoreReconstructor.

Useful local implementations may include:

- a speech/music/noise segmenter;
- an automatic music transcription model producing note events;
- chroma-feature dynamic-time-warping for known-score synchronization;
- downstream symbolic analysis once reviewed MusicXML/ScoreIR exists.

Provider or model availability is not implied by these interfaces. An unavailable
adapter must produce an unavailable/review-required state, not a guessed result.

## Confidence rules

- confirmed: reserved for evidence that has actually been confirmed by the
  applicable review process; never use it for an audio reconstruction by itself.
- probable: usable as a working hypothesis with visible provenance.
- ambiguous: competing readings remain plausible.
- requires_human_review: weak segmentation, unclear polyphony, missing adapters,
  failed alignment, or other unresolved evidence prevents promotion.

## CAPLIN-style lecture example

A lecturer may say "notice the fragmentation here" and then play eight seconds of
piano. The tutor should preserve both spans and, when possible, connect:

lecture timestamp
→ instructor statement
→ music playback timestamp
→ work / movement
→ measure / beat
→ score evidence
→ formal-function analysis

The musical playback is first-class evidence, not discarded transcript filler.
