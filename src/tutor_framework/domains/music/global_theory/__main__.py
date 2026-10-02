"""Local entry point for Global Music Theory Super Skill."""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import fields
from importlib.resources import files
from pathlib import Path

from . import LearnerContext, route, terminology
from .context import MODULE_STATUS
from .curriculum import curriculum
from .learning import build_learning_pack
from .practice import build_original_practice, export_practice
from .mini_exam import build_mini_exam, export_mini_exam


VERSION = "0.2.0"


def _read(path: str) -> dict:
    source = Path(path)
    if source.stat().st_size > 8_000_000:
        raise ValueError("JSON input too large")
    value = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON object required")
    return value


def _context(path: str | None) -> LearnerContext:
    value = _read(path) if path else {}
    allowed = {field.name for field in fields(LearnerContext)}
    if set(value) - allowed:
        raise ValueError("unknown LearnerContext fields")
    for name in ("target_level_or_competencies", "desired_deliverables"):
        if isinstance(value.get(name), list):
            value[name] = tuple(value[name])
    return LearnerContext(**value)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="global-music-theory")
    commands = p.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor")
    theory = commands.add_parser("theory"); theory.add_argument("--request", required=True); theory.add_argument("--context")
    score = commands.add_parser("analyze-score"); score.add_argument("--score", required=True); score.add_argument("--source-id", required=True); score.add_argument("--context"); score.add_argument("--formal-annotations")
    compare = commands.add_parser("compare-curricula"); compare.add_argument("source"); compare.add_argument("target")
    compare.add_argument("--source-version"); compare.add_argument("--target-version")
    reconcile = commands.add_parser("reconcile"); reconcile.add_argument("--request", required=True)
    opened = commands.add_parser("open-practice"); opened.add_argument("--topic", required=True); opened.add_argument("--seed", type=int, required=True)
    opened.add_argument("--context"); opened.add_argument("--output"); opened.add_argument("--no-save", action="store_true"); opened.add_argument("--student-only", action="store_true")
    check_open = commands.add_parser("check-open"); check_open.add_argument("--request", required=True)
    r = commands.add_parser("route"); r.add_argument("question"); r.add_argument("--context")
    t = commands.add_parser("term"); t.add_argument("term"); t.add_argument("--context")
    c = commands.add_parser("curriculum"); c.add_argument("id"); c.add_argument("--version")
    commands.add_parser("resources")
    exam = commands.add_parser("exam"); exam.add_argument("--request", required=True)
    exam.add_argument("--context"); exam.add_argument("--no-save", action="store_true")
    replay = commands.add_parser("mineru-replay"); replay.add_argument("--result-directory", required=True)
    replay.add_argument("--sha256", required=True); replay.add_argument("--extract-questions", action="store_true")
    practice = commands.add_parser("practice")
    practice.add_argument("--grade", type=int, required=True)
    practice.add_argument("--syllabus-id", required=True)
    practice.add_argument("--competency-id", required=True)
    practice.add_argument("--seed", type=int, required=True)
    practice.add_argument("--output")
    practice.add_argument("--context"); practice.add_argument("--no-save", action="store_true")
    mini = commands.add_parser("mini-exam")
    mini.add_argument("--grade", type=int, required=True)
    mini.add_argument("--syllabus-id", required=True)
    mini.add_argument("--seed", type=int, required=True)
    mini.add_argument("--output")
    mini.add_argument("--context"); mini.add_argument("--no-save", action="store_true")
    pack = commands.add_parser("pack")
    pack.add_argument("--dossier", required=True); pack.add_argument("--brief", required=True)
    pack.add_argument("--content", required=True); pack.add_argument("--context", required=True)
    pack.add_argument("--output")
    return p


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command in {"practice", "mini-exam", "open-practice"}:
            context = _context(args.context)
            if args.output and (args.no_save or context.no_save):
                raise ValueError("no-save forbids practice export")
        if args.command == "doctor":
            result = {"identity": "global-music-theory-super-skill", "display_name": "Global Music Theory Super Skill",
                      "version": VERSION, "modules": MODULE_STATUS, "external_calls": False,
                      "mineru": __import__(__package__+".mineru", fromlist=["mineru_configuration"]).mineru_configuration(), "caplin": "explicit opt-in only"}
        elif args.command == "open-practice":
            from .open_practice import build_open_practice, export_open_practice
            bundle = build_open_practice(topic=args.topic, seed=args.seed, context=_context(args.context))
            if args.output and 'student_paper' in bundle:
                result = export_open_practice(bundle, Path(args.output), student_only=args.student_only)
            else:
                result = bundle['student_paper'] if args.student_only and 'student_paper' in bundle else bundle
        elif args.command == "check-open":
            from .open_practice import assess_open_response
            request = _read(args.request)
            result = assess_open_response(request['bundle'], request['learner_response'],
                                          criterion_awards=request.get('criterion_awards'), reviewer_id=request.get('reviewer_id'))
        elif args.command == "theory":
            from .operations import evaluate
            result = evaluate(_read(args.request), _context(args.context))
        elif args.command == "analyze-score":
            from .score_workflow import analyze_score
            source = Path(args.score).expanduser()
            if source.stat().st_size > 2_000_000:
                raise ValueError("Score input exceeds the 2 MB symbolic reader limit")
            annotations = _read(args.formal_annotations).get('annotations', []) if args.formal_annotations else []
            result = analyze_score(source.read_bytes(), source_id=args.source_id, context=_context(args.context), formal_annotations=annotations)
        elif args.command == "compare-curricula":
            from .score_workflow import compare_curricula
            result = compare_curricula(args.source, args.target, source_version=args.source_version, target_version=args.target_version)
        elif args.command == "reconcile":
            from .score_workflow import reconcile_claims
            result = reconcile_claims(_read(args.request)['claims'])
        elif args.command == "route":
            result = route(args.question, _context(args.context))
        elif args.command == "term":
            result = terminology(args.term, _context(args.context))
        elif args.command == "curriculum":
            result = curriculum(args.id, version=args.version)
        elif args.command == "resources":
            result = json.loads(files(__package__).joinpath("data/resources.json").read_text(encoding="utf-8"))
        elif args.command == "exam":
            from .exam_cli import execute_exam_request
            result = execute_exam_request(_read(args.request), no_save=args.no_save or _context(args.context).no_save)
        elif args.command == "mineru-replay":
            from .mineru import load_existing_mineru_result
            result = load_existing_mineru_result(Path(args.result_directory), expected_pdf_sha256=args.sha256,
                                                 extract_questions=args.extract_questions)
        elif args.command == "practice":
            bundle = build_original_practice(grade=args.grade, syllabus_id=args.syllabus_id,
                                             competency_id=args.competency_id, seed=args.seed)
            result = {"state": "review_required", **bundle} if bundle.get("state") == "review_required" else bundle
            if args.output and bundle.get("state") != "review_required":
                result = {"state": "generated_for_review", "artifact_hashes": export_practice(bundle, Path(args.output))}
        elif args.command == "mini-exam":
            bundle = build_mini_exam(grade=args.grade, syllabus_id=args.syllabus_id, seed=args.seed)
            result = export_mini_exam(bundle, Path(args.output)) if args.output and "state" not in bundle else bundle
        else:
            from tutor_framework.domains.music.lesson.learning_pack.models import LearningBrief, PackContent
            result = build_learning_pack(_read(args.dossier), LearningBrief.from_dict(_read(args.brief)),
                                         PackContent.from_dict(_read(args.content)), _context(args.context),
                                         Path(args.output) if args.output else None)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, TypeError, KeyError, RuntimeError) as error:
        print(json.dumps({"state": "blocked", "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
