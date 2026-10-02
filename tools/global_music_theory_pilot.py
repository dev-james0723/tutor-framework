#!/usr/bin/env python3
"""Generate entirely original local pilot artifacts through production services."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tutor_framework.domains.music.global_theory import LearnerContext
from tutor_framework.domains.music.global_theory.learning import build_learning_pack
from tutor_framework.domains.music.global_theory.mini_exam import build_mini_exam, export_mini_exam
from tutor_framework.domains.music.global_theory.syllabus import SYLLABUS_ID
from tutor_framework.domains.music.lesson.learning_pack.document import scan_document
from tutor_framework.domains.music.lesson.learning_pack.models import (
    Citation, CoverageItem, LearningBrief, NoteBlock, PackContent, PackPassage,
    PackSource, PracticeItem, ScoreAnnotation,
)


def _draw_original_score(path: Path) -> None:
    from tutor_framework.domains.music.global_theory.engraving import engrave_original_score
    notes = ''.join(f'<note id="n{i}"><pitch><step>{step}</step><octave>4</octave></pitch><duration>1</duration><type>quarter</type></note>' for i, step in enumerate('CDEC', 1))
    xml = '<score-partwise version="4.0"><part-list><score-part id="P1"><part-name>Original</part-name></score-part></part-list><part id="P1"><measure number="1"><attributes><divisions>1</divisions><key><fifths>0</fifths></key><time><beats>4</beats><beat-type>4</beat-type></time><clef><sign>G</sign><line>2</line></clef></attributes><direction><sound tempo="120"/></direction>' + notes + '</measure></part></score-partwise>'
    rendered = engrave_original_score(xml, title="Original C-major reading exercise")
    path.write_bytes(rendered["pdf_bytes"])
    path.with_suffix(".musicxml").write_text(xml)
    path.with_suffix(".mid").write_bytes(rendered["midi_bytes"])
    path.with_suffix(".svg").write_text(rendered["svg"])


def generate(destination: Path) -> dict:
    destination = Path(destination).expanduser().resolve()
    if destination.exists():
        raise ValueError("pilot destination already exists")
    destination.mkdir(parents=True)
    mini = export_mini_exam(build_mini_exam(grade=3, syllabus_id=SYLLABUS_ID, seed=57),
                            destination / "original-mini-paper")
    source = destination / "original-score.pdf"
    _draw_original_score(source)
    dossier = scan_document(source, destination / "intake", score_pages=(1,))
    citation = Citation("pilot-score", "Original one-measure score", page=1)
    source_model = PackSource("pilot-score", str(source), dossier["source_hash"],
                              "Original C-major reading exercise", "System-created original for this pilot", kind="score", private=False)
    passage = PackPassage("passage-one", "pilot-score", "pilot-original-v1", "1", 1,
                          traversal=("1",), evidence_state="review_required")
    blocks = (
        NoteBlock("method", "concepts", "Read the staff first",
                  "Use the treble clef and count the line or space before naming each pitch.",
                  ("passage-one",), (citation,), "study_instruction", answer_bearing=False),
        NoteBlock("analysis", "passage_analysis", "Worked pitch reading",
                  "The original symbolic score spells C4, D4, E4, C4. C4 is the tonic; the fourth note returns to it. Written pitches and MIDI have been checked against the same event stream.",
                  ("passage-one",), (citation,), "tutor_judgment", evidence_state="review_required"),
        NoteBlock("listening", "listening_guide", "Read or sing the contour",
                  "Sing C4–D4–E4, then return to C4. The companion MIDI was checked against the symbolic pitch/onset events; no external recording is claimed.",
                  ("passage-one",), (citation,), "study_instruction", answer_bearing=False),
    )
    coverage = tuple(CoverageItem(unit["unit_id"], ("method", "analysis", "listening")) for unit in dossier["units"])
    content = PackContent(
        "Original C-major reading pack", (source_model,), (passage,), blocks, coverage,
        (PracticeItem("quiz-one", "Which pitch is the tonic, and which note returns to it?", "C4; the fourth note",
                      "C4 is the tonic of C major. The last note returns to the opening C4.", ("passage-one",), (citation,)),),
        (ScoreAnnotation("annotation-one", "passage-one", "pilot-score", 1,
                         (0.075, 0.148, 0.85, 0.285), "C4-D4-E4-C4: tonic return", answer_bearing=True),),
        visual_reviewed_pages=(), review_notes="Original MusicXML engraved locally with Verovio; symbolic/MIDI consistency passed. Pedagogical expert review remains pending.",
    )
    brief = LearningBrief(dossier["source_hash"], "understand",
                          ("notes", "annotated_score", "quiz", "flashcards", "listening_guide"),
                          help_mode="worked", language="en", confirmed=True, no_video=True)
    context = LearnerContext(learning_goal="understand", desired_deliverables=brief.materials,
                             analysis_framework="basic_staff_pitch", text_only=False)
    learning = build_learning_pack(dossier, brief, content, context, destination / "learning-pack")
    result = {"state": "original_engraved_pilot_for_review", "mini_exam": mini,
              "learning_pack": learning, "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
              "external_parser_used": False, "real_abrsm_paper_parsed": False,
              "music_review": "review_required", "visual_review": "review_required"}
    (destination / "pilot-result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n")
    return result


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(); p.add_argument("destination")
    args = p.parse_args()
    print(json.dumps(generate(Path(args.destination)), ensure_ascii=False, indent=2))
