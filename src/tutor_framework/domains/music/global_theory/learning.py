"""Projection into the existing Learning Pack authority, including session-only mode."""
from __future__ import annotations

from pathlib import Path

from .context import LearnerContext
from tutor_framework.domains.music.lesson.learning_pack.models import LearningBrief, PackContent
from tutor_framework.domains.music.lesson.learning_pack.render import payload_for, notes_markdown
from tutor_framework.domains.music.lesson.learning_pack.service import build_pack, validate_content


def build_learning_pack(dossier: dict, brief: LearningBrief, content: PackContent,
                        context: LearnerContext, output: Path | None = None) -> dict:
    if context.text_only and any(item in brief.materials for item in ("annotated_score", "video", "audio", "mindmap")):
        raise ValueError("text-only forbids visual or audio media export")
    if "video" in brief.materials and ("video" not in context.desired_deliverables or context.text_only):
        raise ValueError("global video requires explicit deliverable and no text-only override")
    if context.no_save:
        if output is not None:
            raise ValueError("no-save forbids an output directory")
        # Existing validators read the source but write nothing. Render only into process memory.
        validate_content(dossier, brief, content)
        payload = payload_for(brief, content)
        return {"state": "session_only", "notes": notes_markdown(payload),
                "answer_policy": payload["answer_policy"], "persisted": False,
                "pending_materials": [x for x in brief.materials if x != "notes"]}
    if output is None:
        raise ValueError("output directory required for persisted Learning Pack")
    return build_pack(dossier, brief, content, output, pdf=False, product_name="GLOBAL MUSIC THEORY")
