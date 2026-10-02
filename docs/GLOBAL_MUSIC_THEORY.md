# Global Music Theory Super Skill — implementation v0.2.0

This is an additive, independently installed Tutor Framework entry point, not a replacement for Caplin Tutor or a second Learning Pack/parser stack. The release is a bounded working pilot. Live ABRSM ingestion and expert acceptance remain blocked as described below; a green test suite is not an assertion of universal music-theory expertise.

## Implemented runtime

The `global-music-theory` entry point composes response language, terminology preferences, curriculum/version, target competencies, musical tradition, analytical framework, notation/solfege, learning goal and requested deliverables. Simple supported definitions answer directly. Substantial requests ask only missing context, at most five questions. Nationality is never used to select a curriculum or musical tradition. English, Traditional Chinese and bilingual foundational responses are implemented; other response-language support is not asserted.

The public registry contains 100 terminology metadata records, all seven relationship classes, and separately authored bounded explanations for fundamentals and cadence conflicts. Restricted/private-source definitions are not distributed. UK imperfect cadence, US imperfect authentic cadence and the narrower Caplin framework are explicitly distinguished. The preserved Caplin IAC source conflict remains review-required. Forty-four source-bound curriculum/context records are configurations, not cloned skills. Named ABRSM from-2020 Grades 1–5 generator constraints come from one immutable data file, `data/abrsm_from_2020.json`. No numerical grade equivalence is invented.

Twelve module contracts route foundations, rhythm, aural work, harmony/counterpoint, form, jazz/pop, composition/performance, exam coaching, terminology, media evidence, Learning Packs and source QA. A contract marked `review_required` or `unsupported` must not be presented as a fully implemented specialist. Caplin is an explicit, read-only, tenant-scoped local compatibility module; it never writes to the original skill or learning store.

## Source and exam pipeline

`ExistingMinerUResult` replays original-byte-bound structured results. `ExistingMinerUHelper` invokes the already installed `pdf-rag-parser` helper; it does not reimplement the provider stack. New cloud jobs require both a matching purpose grant and explicit cloud/cost authorization. Credentials must already be available through an approved environment. The adapter never queries a credential store. No-save forbids cloud processing or persistent output.

The normalizer consumes real MinerU `layout.json` pages, nested blocks and image references. It retains source coordinates, reading order, original page dimensions, source checksums and image hashes. Archive paths are scoped and bounded. Question extraction produces candidates, not verified musical readings. Missing marks, hierarchy, scores or unrecognized structures require review. Text matching is never a substitute for notation recognition. Existing score/symbolic/OMR contracts remain the authority when exact pitches and rhythms matter.

A private per-tenant SQLite bank preserves revisions and six separate append-only layers: source question, official answer, third-party explanation, AI-derived answer, teacher result and learner answer. Reopening retains answer origins and active exam locks. Paper/set/version/number/checksum identities are mandatory. Official-answer promotion requires a paired official resource, matching version/set, verified bytes, a numbered source region and reviewer attribution; arbitrary supplied answer text cannot be promoted. Notation-only keys remain review-required. `source_text_verified` is not `musically_verified`.

Hint mode uses student-field allowlists and staged conceptual hints. Worked and Check modes require the exact question revision. Check stores the learner attempt separately and reports unavailable assessment neutrally. An active simulation locks answers across the entire paper, including through other modes and after reopening. Practice completion cannot bypass an active exam. Targeted practice returns a student-only original mini-paper and retains teacher artifacts separately until explicit completion.

## Original practice and Learning Packs

The mini-paper generator selects five distinct supported competencies within the named Grade 1–5 scope. It independently solves items, validates distractors, checks MusicXML pitches/durations/key signatures, and compares against any explicitly supplied authorized source questions. This is targeted practice, not a complete official examination blueprint. Five linked artifacts are produced: student paper, answer key, worked solutions, rubric and competency map. Shared question/concept/passage/claim IDs persist across them. Difficulty is estimated, scores are practice feedback, and teacher calibration remains outstanding.

Every generated paper states: **Unofficial original practice material. Not endorsed by ABRSM.**

Original-score engraving uses local Verovio and the existing symbolic/MIDI validation contracts. Portable SVG glyph expansion is checked before PDF generation. The Global adapter reuses the existing Learning Pack manifest, layered notes, exercises, quiz, hints, flashcards, review plan and annotated-score renderer. Text-only forbids visual/audio export; no-save is session-only. Video is never automatic in the Global entry, while the unchanged Caplin installation retains its legacy behavior. No new video-provider call was made for this release.

Global evidence revisions can be projected into the existing framework `Claim`/`EvidenceRef` contracts without promoting inferred content to confirmed fact. Private and licensed content require a tenant. Retrieval/indexing is not model training.

## Commands

After separate installation:

```sh
~/.agents/skills/global-music-theory-super-skill/bin/global-music-theory doctor
~/.agents/skills/global-music-theory-super-skill/bin/global-music-theory route 'What is a minim?'
~/.agents/skills/global-music-theory-super-skill/bin/global-music-theory term IAC --context context.json
~/.agents/skills/global-music-theory-super-skill/bin/global-music-theory mini-exam --grade 3 --syllabus-id abrsm-theory-from-2020 --seed 57 --output ./new-original-mini
~/.agents/skills/global-music-theory-super-skill/bin/global-music-theory exam --request scoped-exam-request.json
```

An exam request contains `action`, an explicitly curated `catalogue`, `tenant_id`, optional explicit `storage_root`, action `parameters` and a scoped `grant` for ingestion/answer-source matching. Supported actions are `ingest`, `retrieve`, `tutor`, `add_answer_layer`, `match_official_answer`, `finish_exam` and `finish_practice`. A persistent request must not be combined with `--no-save` or a no-save context. Ingestion selects `existing_result` or `existing_helper`; there is no flat-text fallback. The typed APIs and wholly synthetic acceptance fixtures document exact schemas.

## Installation, preservation and rollback

`tools/global_music_theory_install.py install --repository . --destination ~/.agents/skills --python-executable /absolute/path/to/private/runtime/bin/python --with-caplin` creates a new identity, copies the public runtime, optionally copies the frozen baseline into a private 0700 directory, pins the interpreter, and writes a file-hash manifest. Existing destinations are refused. It does not read/copy the private learning store, replace Caplin, or change Caplin's discovery identity. The runtime's optional dependencies are declared under `global-music` in `pyproject.toml`.

Rollback is `tools/global_music_theory_install.py rollback --destination ~/.agents/skills`. It verifies the new identity and renames only that installation to a unique archive; it does not delete source material, change Caplin, or reverse unrelated work. Bank schema changes require an explicit migration; unknown schema versions fail closed. Historical answer revisions cannot be overwritten.

## Release evidence and honest limits

Run the full unittest suite, `tools/global_music_theory_gate.py`, the existing release gate, original/copied Caplin tests, and post-install tests from outside the repository. The 50 research cases currently exercise routing/privacy/media invariants; they are not 50 teacher-adjudicated musical answers. Additional independent tests cover source authority, cross-paper leakage, persistent isolation, no-save, original generation, notation consistency and real engraving.

During this implementation, a prior non-ABRSM MinerU result replayed successfully: 200 pages, 1,964 blocks and 214 hashed image references. It is not a new parse. **No live ABRSM paper was parsed or ingested.** Credential retrieval was blocked by the host's security boundary, and catalogue processing rights were still awaiting explicit scope confirmation. No alternate credential-access path, paid job, new account, login bypass or restricted publication was attempted.

Remaining acceptance gates: authorized live ABRSM documents and provider access; the missing/mislinked Grade 3 sample key; complete Grade 6–8 source-bound blueprints and open-response marking; expert review of notation/cadence interpretations and estimated practice difficulty; broader traditions/languages and specialist-answer benchmark adjudication. Large or irregular question layouts may still require manual structured review. The local bank is intended for controlled single-writer CLI use, not an unreviewed multi-user web service.

Raw research, private book/course references, frozen local Caplin data, licensed PDFs and private learner data are excluded from the public branch. Machine-specific preservation hashes, command logs, source-availability counts, manual-inspection records and installation receipts remain in the owner's private implementation receipt directory.


## v0.2 continuation: executable analytical work

The continuation retains the v0.1 source/rights gates while adding six concrete operations: interval number/quality/direction; correctly spelled major and named minor scales; complete spelled triads/seventh-chord roots and inversions; fixed/movable-do with explicit minor basis; simple/compound/irregular meter groups; and bounded similar-motion perfect-interval checks across named voices. A separate existing music21 environment was used for independent interval comparisons; these are software cross-checks, not human expert approval.

Scale register convention: the supplied tonic is the lower endpoint of the one-octave range. Descending output starts at its octave and ends on the supplied lower tonic. Classical melodic minor descends in its natural form; a jazz/pop context does not silently inherit that rule and is held for explicit convention review. Fixed-do outputs written accidental information rather than disguising an altered note. Parallel-motion checks use written interval quality as well as semitone distance, so an enharmonic augmented fourth is not mislabeled a perfect fifth.

New commands:

```sh
global-music-theory theory --request operation.json --context context.json
global-music-theory analyze-score --score original.musicxml --source-id my-score
global-music-theory compare-curricula ABRSM-G1 ABRSM-G2
global-music-theory reconcile --request competing-claims.json
global-music-theory open-practice --topic composition --seed 17 --student-only
global-music-theory check-open --request learner-response.json
```

Example operation objects:

```json
{"operation":"interval","first":"C4","second":"Eb4","source_id":"user-question"}
{"operation":"scale","tonic":"F#4","mode":"major"}
{"operation":"chord","notes":["B3","D4","F4","G4"]}
{"operation":"meter","numerator":5,"denominator":8,"groups":[2,3]}
{"operation":"solfege","system":"movable_do","tonic":"A3","mode":"natural_minor","minor_basis":"la","notes":["A3","C4","E4"]}
```

A score analysis preserves each source event ID, original measure and voice, local and absolute onset, written pitch and sounding MIDI. It does not fabricate a PDF crop or claim an OMR result. A lecture/score conflict retains both source records and returns review-required rather than silently preferring whichever source seems more authoritative. Curriculum switching computes explicitly evidenced competency overlap and missing/unconfirmed areas.

Open-response practice now supports voice-leading revision, original composition continuation and comparison of formal interpretations. Each uses five separate student/key/solution/rubric/map artifacts. The example response is one system-created possibility, not an official key. Reviewer-supplied partial-credit awards remain labeled as caller-supplied reviewer results, and free responses are never assigned invented grades. Requested ABRSM Grade 6–8 context stays alignment-review-required until a verified blueprint is available.

The catalogue's 51 historical resource entries now include their exact known source URLs without promoting permissions or inventing checksums. In this continuation, ten exact public sample/syllabus downloads were attempted from the Mac and all returned HTTP 403. No credentials were retrieved through an alternate path, no protected file was acquired, and no new MinerU job was submitted. Original documents and approved provider access therefore remain genuine external acceptance blockers.

### Primary references for bounded calculations

Definitions were checked against the author-published Music Theory for the 21st-Century Classroom, sections 3.1, 4.4, 5.1, 8.1 and 26.3, and Open Music Theory's major/minor scale and solfege chapters. The code and exercises are independently authored; source exercises, diagrams and textbook content are not bundled.

- https://musictheory.pugetsound.edu/mt21c/IntervalsIntroduction.html
- https://musictheory.pugetsound.edu/mt21c/MinorScales.html
- https://musictheory.pugetsound.edu/mt21c/meter.html
- https://musictheory.pugetsound.edu/mt21c/SeventhChordsIntroduction.html
- https://musictheory.pugetsound.edu/mt21c/ObjectionableParallels.html
- https://viva.pressbooks.pub/openmusictheory/chapter/major-scales/
- https://viva.pressbooks.pub/openmusictheory/chapter/minor-scales/

### v0.2 review hardening

Written-notation revisions are distinct from the shared sounding-event revision. Event claim IDs include the notation revision, so enharmonic respelling cannot reuse the same written-pitch claim. Automatic melodic intervals are restricted to unambiguous monophonic attacks: chord members, rests, overlapping events and tie continuations are not selected as new melody notes. A pitch outside the optional interval-operation scope preserves the exact score events and produces an explicit warning. No-save travels with each original open-practice artifact and cannot be accidentally dropped at a later export call. Student-only export creates no teacher answer files.
