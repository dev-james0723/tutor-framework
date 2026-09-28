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
       -> known score? -> ScoreAligner -> measure/beat anchors
       -> otherwise/supplement -> AudioTranscriber -> note hypotheses
       -> explicit quantization only -> provisional ScoreIR
  -> provenance/review state
  -> CAPLIN teaching and form analysis
```

## Adapter boundaries

- AudioSegmenter
- AudioTranscriber
- ScoreAligner
- ScoreReconstructor

All adapters fail closed. Missing/failed runtimes produce unavailable or
requires_human_review states, never fabricated notes.

## Evidence policy

Audio reconstruction is never confirmed by itself. Low-confidence evidence stays
probable, ambiguous, or requires_human_review. The tutor must never claim that
arbitrary polyphonic lecture audio can always yield every note exactly.

## Local runtime direction

Concrete local backends may include a speech/music/noise segmenter, Spotify Basic
Pitch or another compatible AMT runtime, chroma + dynamic-time-warping alignment,
and the existing score-harmony-analyzer downstream after symbolic evidence exists.
Heavy runtimes remain optional and outside Tutor Framework dependencies.

No remote upload, paid provider, or external publication is part of this change.

## Acceptance

- deterministic tests cover timestamp preservation, fail-closed adapters,
  known-score-first routing, provisional reconstruction, and low-confidence review;
- a public synthetic lecture fixture contains no copyrighted/student audio;
- existing Tutor Framework tests, compileall, release gate, and diff checks pass;
- CAPLIN V3 routes lecture audio through this evidence model and exposes an honest
  doctor for optional local backends.
