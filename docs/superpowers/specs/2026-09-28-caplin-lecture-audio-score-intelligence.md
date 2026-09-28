# CAPLIN Lecture Audio → Score Intelligence Design

Date: 2026-09-28
Status: approved for implementation
Scope: Tutor Framework music domain + CAPLIN V3 integration

## Problem

Music-theory lecture recordings often alternate between spoken explanation and
musical demonstrations. A speech transcript may reduce the most important musical
evidence to "[music]". CAPLIN must preserve and understand both streams.

## Required behavior

- timestamp speech, music, speech-over-music, silence/noise, and unknown regions;
- preserve the original audio source and direct time locators;
- identify the musical work/excerpt before note-level transcription when course context does not already identify it;
- keep piece matches as explicit context/fingerprint/semantic evidence rather than silently treating identity as verified;
- recognize note events only through explicit adapter evidence;
- prefer alignment to a known authoritative score before reconstructing notation;
- connect audio time to work / movement / measure / beat when supported;
- reconstruct only a provisional ScoreIR from explicit quantized note evidence;
- preserve uncertainty for polyphonic, noisy, overlapping, or weak passages;
- keep verified score evidence, audio-derived evidence, instructor interpretation,
  and CAPLIN analysis as separate provenance layers.

## Architecture

The reusable implementation belongs under the music artifact-reader/domain layer,
not TutorEngine and not the CAPLIN teaching profile.

```text
lecture audio
  -> AudioSegmenter
  -> timed regions
  -> music region
       -> unknown work? -> PieceIdentifier -> candidate work/excerpt
       -> candidate/known work -> authoritative or user-supplied score lookup
       -> known score? -> ScoreAligner -> measure/beat anchors
       -> otherwise/supplement -> AudioTranscriber -> note hypotheses
       -> explicit quantization only -> provisional ScoreIR
  -> provenance/review state
  -> CAPLIN teaching and form analysis
```

## Adapter boundaries

- AudioSegmenter
- PieceIdentifier
- AudioTranscriber
- ScoreAligner
- ScoreReconstructor

All adapters fail closed. Missing/failed runtimes produce unavailable or
requires_human_review states, never fabricated notes.

## Evidence policy

Audio reconstruction is never confirmed by itself. Low-confidence evidence stays
probable, ambiguous, or requires_human_review. The tutor must never claim that
arbitrary polyphonic lecture audio can always yield every note exactly.

## Piece identification and runtime direction

Piece identification runs before AMT when the work is unknown. Course metadata may be used as a context candidate, but it is not proof that the played excerpt is the same work.

Google Sound Search / Pixel Now Playing are first-party recognition systems, not a documented general third-party Sound Search API. Do not invent or scrape an undocumented endpoint. CAPLIN may optionally use the documented Gemini audio-understanding API as a best-effort **semantic** identifier for a deliberately selected short excerpt. That route is disabled by default, requires explicit external-transfer opt-in, and remains probable/ambiguous until corroborated by score/context.

Concrete local backends may include a speech/music/noise segmenter, Spotify Basic Pitch or another compatible AMT runtime, chroma + dynamic-time-warping alignment, and the existing score-harmony-analyzer downstream after symbolic evidence exists. Heavy runtimes remain optional and outside Tutor Framework dependencies.

The default path keeps private lecture material local. No remote upload, paid provider, or external publication is silently enabled by this change.

## Acceptance

- deterministic tests cover timestamp preservation, fail-closed adapters,
  known-score-first routing, provisional reconstruction, and low-confidence review;
- a public synthetic lecture fixture contains no copyrighted/student audio;
- existing Tutor Framework tests, compileall, release gate, and diff checks pass;
- CAPLIN V3 routes lecture audio through this evidence model and exposes an honest
  doctor for optional local backends.
