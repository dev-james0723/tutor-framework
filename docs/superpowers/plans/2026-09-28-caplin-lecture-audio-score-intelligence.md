# Implementation Plan: CAPLIN Lecture Audio → Score Intelligence

Date: 2026-09-28
Branch: feat/caplin-audio-score-listener

1. Add src/tutor_framework/domains/music/audio.py with validated models,
   confidence states, adapter protocols, known-score-first orchestration, and
   provisional ScoreIR reconstruction.
2. Export the public API and add unit tests plus a synthetic lecture-audio eval.
3. Document the evidence pipeline in architecture and Tutor Framework skill
   references; keep heavy ML/audio dependencies optional.
4. Update CAPLIN V3 from 3.0.0 to 3.1.0:
   - new lecture-audio-score-listener reference;
   - Learn-mode speech/music routing;
   - four provenance layers;
   - low-confidence review queue;
   - audio_score_listener.py --doctor;
   - contract tests.
5. If compatible, install concrete local audio backends only in isolated
   user-local runtimes. Never change system Python or enable paid/cloud upload.
6. Validate Tutor Framework:
   PYTHONPATH=src python3 -m unittest discover -s tests -v
   PYTHONPATH=src python3 -m compileall -q src tests
   PYTHONPATH=src python3 -m tutor_framework.release_gate .
   git diff --check
7. Validate CAPLIN package and installed copy with unittest, compileall, and the
   doctor. Run a synthetic local audio smoke test when concrete backends are
   available.
8. Push the feature branch, open a PR, merge only after checks pass, then update
   the local installed CAPLIN skill and verify the released state.
