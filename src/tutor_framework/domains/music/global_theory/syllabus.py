"""Immutable named-syllabus snapshots, not cross-system grade conversion."""
from __future__ import annotations

import copy
import json
from importlib.resources import files

SYLLABUS_ID = "abrsm-theory-from-2020"


def syllabus_for(syllabus_id: str, grade: int) -> dict:
    if type(grade) is not int or grade not in range(1, 9):
        raise ValueError("grade must be an integer from 1 to 8")
    if syllabus_id != SYLLABUS_ID or grade >= 6:
        return {"state": "review_required", "syllabus_id": syllabus_id, "grade": grade,
                "reason": "No verified matching full scope for this version and grade.",
                "grade_equivalences": [], "full_exam_blueprint_verified": False}
    source = json.loads(files(__package__).joinpath("data/abrsm_from_2020.json").read_text(encoding="utf-8"))
    row = next(row for row in source["packs"] if row["grade"] == grade)
    metadata = {key: value for key, value in source.items() if key != "packs"}
    return copy.deepcopy({**metadata, **row, "state": "verified_outline_subset",
                          "current_exam_applicability": "named_from_2020_outline_only"})
