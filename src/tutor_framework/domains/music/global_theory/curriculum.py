"""Source-bound curriculum metadata; no grade equivalence inference."""
from __future__ import annotations

import json
from importlib.resources import files


def packs() -> list[dict]:
    data = json.loads(files(__package__).joinpath("data/curricula.json").read_text(encoding="utf-8"))
    return data["packs"]


def curriculum(curriculum_id: str, *, version: str | None = None) -> dict:
    found = next((p for p in packs() if p["curriculum_id"] == curriculum_id), None)
    if found is None:
        return {"curriculum_id": curriculum_id, "state": "unsupported", "version": version or "unknown"}
    result = dict(found)
    result["version"] = version or "unknown"
    result["version_state"] = "unconfirmed" if not version else "caller_supplied_requires_source_check"
    result["explicit_competencies"] = [k for k, v in found["competencies"].items() if v == "explicit"]
    result["gaps"] = [k for k, v in found["competencies"].items() if v != "explicit"]
    result["grade_equivalences"] = []
    return result
