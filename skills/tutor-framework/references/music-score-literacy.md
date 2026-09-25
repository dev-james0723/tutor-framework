# Music score literacy reference

The MusicXML slice is the framework's first domain-specific example. It is small
enough to test deterministically and rich enough to demonstrate how domain facts
should retain evidence:

- parse a structured score artifact rather than guessing from an image;
- represent measures, notes, duration, pitch, and key-signature facts;
- explain common key-signature and tonic interpretations;
- attach confidence and source anchors to material claims; and
- preserve ambiguity when the artifact or notation is incomplete.

Use `src/tutor_framework/domains/music/score.py` and
`evals/music/synthetic_cases.json` as the implementation and fixture references.
The slice does not provide complete optical music recognition, performance
grading, copyright clearance, or professional music-teaching authority. Image
or audio ingestion should remain an explicit connector with its own provenance,
quality checks, and human review.
