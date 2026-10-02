"""Small, original, independently solved rhythm practice from source-bound scope."""
from __future__ import annotations

import difflib
import hashlib
import json
from fractions import Fraction
from pathlib import Path
from .syllabus import syllabus_for


DISCLAIMER = "Unofficial original practice material. Not endorsed by ABRSM."
DURATIONS = {"quaver": Fraction(1, 2), "crotchet": Fraction(1), "minim": Fraction(2)}


def _solve(meter_quarters: int, sounding: tuple[str, ...]) -> Fraction:
    return Fraction(meter_quarters) - sum((DURATIONS[n] for n in sounding), Fraction())


def build_original_practice(*, grade: int, syllabus_id: str, competency_id: str, seed: int,
                            authorized_source_stems: tuple[str, ...] = ()) -> dict:
    if grade not in range(1, 9):
        raise ValueError("grade must be 1–8")
    if grade >= 6:
        return {"state": "review_required", "reason": "Current G6–8 blueprint and marking evidence are insufficient for an exam-equivalent paper.",
                "available": "Teacher-reviewed, rubric-based open tasks may be authored without official score claims."}
    if competency_id != "rhythm.duration":
        return {"state": "review_required", "reason": "No independently checked generator for this competency."}
    syllabus = syllabus_for(syllabus_id, grade)
    if syllabus["state"] == "review_required" or competency_id not in syllabus["generator_competencies"] + ["rhythm.duration"]:
        return {"state": "review_required", "reason": "Versioned syllabus evidence required."}
    if not isinstance(seed, int):
        raise ValueError("integer seed required")
    candidates = []
    for meter in (3, 4):
        for first in DURATIONS:
            for second in DURATIONS:
                remaining = _solve(meter, (first, second))
                if remaining in DURATIONS.values():
                    candidates.append((meter, first, second, remaining))
    meter, first, second, correct = candidates[seed % len(candidates)]
    correct_name = next(name for name, duration in DURATIONS.items() if duration == correct)
    names = list(DURATIONS)
    shift = (seed // len(candidates)) % 3
    names = names[shift:] + names[:shift]
    options = [{"id": letter, "text": name + " rest"} for letter, name in zip("ABC", names)]
    correct_id = next(option["id"] for option in options if option["text"] == correct_name + " rest")
    prompt = (f"A percussionist writes a {meter}/4 measure containing a {first} and a {second}. "
              "Which single rest completes its notated duration? Choose one.")
    for old in authorized_source_stems:
        normalized = lambda s: " ".join(s.casefold().split())
        if difflib.SequenceMatcher(None, normalized(prompt), normalized(old)).ratio() >= 0.84:
            return {"state": "review_required", "reason": "Near-duplicate of an authorized source question."}
    # Independent solver checks all options against the meter, not the generator's selected label.
    solved = [o["id"] for o in options if DURATIONS[o["text"].removesuffix(" rest")] == _solve(meter, (first, second))]
    if solved != [correct_id]:
        raise ValueError("independent solver rejected generated options/key")
    paper_id = "original:" + hashlib.sha256(f"{grade}:{syllabus_id}:{competency_id}:{seed}".encode()).hexdigest()[:16]
    common = {"paper_id": paper_id, "version": "1.0", "disclaimer": DISCLAIMER}
    return {
        "student_paper": {**common, "question_id": paper_id+":q1", "prompt": prompt,
                          "options": options, "marks": 1, "answer_space": "Select A, B, or C."},
        "answer_key": {**common, "question_id": paper_id+":q1", "answer": correct_id,
                       "correct_option_id": correct_id, "origin": "independent_system_derivation"},
        "worked_solutions": {**common, "question_id": paper_id+":q1",
                             "steps": [f"The measure contains {meter} crotchet units.",
                                       f"The written notes use {DURATIONS[first]} + {DURATIONS[second]} units.",
                                       f"The remaining duration is {correct} unit(s): {correct_name} rest."],
                             "answer_origin": "independent_system_derivation"},
        "marking_rubric": {**common, "question_id": paper_id+":q1", "practice_only": True,
                           "criteria": [{"condition": "selected correct rest", "marks": 1}],
                           "official_marking_claim": False},
        "competency_map": {**common, "question_id": paper_id+":q1", "competency_id": competency_id,
                           "syllabus_id": syllabus_id, "source_id": syllabus["source_id"],
                           "source_applicability": "historical outline; current applicability requires review",
                           "difficulty": "estimated", "teacher_calibrated": False},
    }


def export_practice(bundle: dict, directory: Path) -> dict[str, str]:
    if set(bundle) != {"student_paper", "answer_key", "worked_solutions", "marking_rubric", "competency_map"}:
        raise ValueError("five separately validated deliverables required")
    directory = Path(directory).resolve()
    if directory.exists() and any(directory.iterdir()):
        raise ValueError("practice export directory must be empty")
    directory.mkdir(parents=True, exist_ok=True)
    result = {}
    for name, content in bundle.items():
        target = directory / f"{name}.json"
        target.write_text(json.dumps(content, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        result[name] = hashlib.sha256(target.read_bytes()).hexdigest()
    return result
