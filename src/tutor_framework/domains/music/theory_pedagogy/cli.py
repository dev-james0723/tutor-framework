#!/usr/bin/env python3
"""Unified music-artifact entrypoint for Theory Pedagogy Assistant."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
FRAMEWORK_ROOT = Path(
    os.environ.get("TUTOR_FRAMEWORK_ROOT", "/Users/ouxianxing/Projects/tutor-framework")
).expanduser()
SCORE_ANALYZER_ROOT = Path(
    os.environ.get(
        "SCORE_HARMONY_ANALYZER_ROOT",
        "/Users/ouxianxing/.codex/skills/score-harmony-analyzer",
    )
).expanduser()
CAPLIN_ROOT = Path(
    os.environ.get(
        "CAPLIN_TUTOR_ROOT",
        "/Users/ouxianxing/.agents/skills/caplin-form-tutor",
    )
).expanduser()

if (FRAMEWORK_ROOT / "src").is_dir():
    sys.path.insert(0, str(FRAMEWORK_ROOT / "src"))

from tutor_framework.domains.music.theory_pedagogy import (  # noqa: E402
    TranscriptSegment,
    generate_theory_contrast,
    map_caplin_manifest,
    read_score_source,
    write_contrast_package,
)


def _json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )


def _require_new_directory(path: Path) -> Path:
    path = path.expanduser().resolve()
    if path.exists():
        raise ValueError(f"refusing to overwrite existing output: {path}")
    path.mkdir(parents=True, exist_ok=False)
    return path


def _run(command: list[str], *, timeout: int = 900) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _find_musescore() -> Path | None:
    candidates = []
    if os.environ.get("MUSESCORE_BIN"):
        candidates.append(os.environ["MUSESCORE_BIN"])
    for name in ("mscore", "musescore", "MuseScore4"):
        found = shutil.which(name)
        if found:
            candidates.append(found)
    candidates.extend(
        [
            "/Applications/MuseScore 4.app/Contents/MacOS/mscore",
            "/Applications/MuseScore 4.app/Contents/MacOS/MuseScore4",
        ]
    )
    for candidate in candidates:
        path = Path(candidate).expanduser()
        if path.is_file() and os.access(path, os.X_OK):
            return path.resolve()
    return None


def _render_wav(musicxml: Path, destination: Path) -> dict[str, object]:
    musescore = _find_musescore()
    if musescore is None:
        return {
            "state": "validation_unavailable",
            "reason": "MuseScore CLI is unavailable; WAV was not synthesized",
            "source": str(musicxml),
        }
    proc = _run(
        [str(musescore), "-o", str(destination), str(musicxml)],
        timeout=240,
    )
    if proc.returncode != 0 or not destination.is_file() or destination.stat().st_size == 0:
        if destination.exists():
            destination.unlink()
        return {
            "state": "validation_unavailable",
            "reason": f"MuseScore audio render failed with exit code {proc.returncode}",
            "source": str(musicxml),
            "stderr_tail": proc.stderr[-2000:],
        }
    return {
        "state": "rendered_from_same_musicxml",
        "provider": "musescore-local",
        "source": str(musicxml),
        "wav": str(destination),
        "bytes": destination.stat().st_size,
        "external_calls": False,
    }


def doctor() -> dict[str, object]:
    score_script = SCORE_ANALYZER_ROOT / "scripts" / "score_harmony.py"
    lecture_script = CAPLIN_ROOT / "scripts" / "lecture_audio_pipeline.py"
    return {
        "status": "ready"
        if (FRAMEWORK_ROOT / "src").is_dir()
        and score_script.is_file()
        and lecture_script.is_file()
        else "incomplete",
        "framework": {
            "root": str(FRAMEWORK_ROOT),
            "available": (FRAMEWORK_ROOT / "src").is_dir(),
        },
        "score_reader": {
            "script": str(score_script),
            "available": score_script.is_file(),
        },
        "lecture_mapper": {
            "script": str(lecture_script),
            "available": lecture_script.is_file(),
        },
        "audio_renderer": {
            "provider": "musescore-local",
            "path": str(_find_musescore()) if _find_musescore() else None,
            "available": _find_musescore() is not None,
        },
        "policy": {
            "external_audio_transfer_default": False,
            "printed_score_requires_omr_review": True,
            "generated_examples_are_course_evidence": False,
        },
    }


def generate_example(concept: str, output: Path, *, render: bool) -> dict[str, object]:
    contrast = generate_theory_contrast(concept)
    manifest = write_contrast_package(contrast, output, render=render)
    if render:
        for item in manifest["variants"]:
            musicxml = Path(item["musicxml"])
            item["audio_render"] = _render_wav(
                musicxml,
                musicxml.with_name("score.wav"),
            )
        _write_json(output.expanduser().resolve() / "manifest.json", manifest)
    return {
        "state": "generated_review_required",
        "output": str(output.resolve()),
        "manifest": manifest,
    }


def read_score(
    source: Path,
    output: Path,
    *,
    source_id: str,
    key: str | None = None,
    measures: str | None = None,
) -> dict[str, object]:
    source = source.expanduser().resolve()
    suffix = source.suffix.casefold()
    if suffix in {".musicxml", ".xml"}:
        output = _require_new_directory(output)
        result = read_score_source(source, source_id=source_id)
        payload = {
            "state": result.state,
            "source_id": result.source_id,
            "input_kind": result.input_kind,
            "review_required": result.review_required,
            "reason": result.reason,
            "observations": result.observations,
        }
        _write_json(output / "theory-pedagogy-score-read.json", payload)
        return payload

    score_script = SCORE_ANALYZER_ROOT / "scripts" / "score_harmony.py"
    if not score_script.is_file():
        raise RuntimeError("score-harmony-analyzer is unavailable")
    output = output.expanduser().resolve()
    if output.exists():
        raise ValueError(f"refusing to overwrite existing output: {output}")
    command = [
        sys.executable,
        str(score_script),
        str(source),
        "--output",
        str(output),
        "--language",
        "bilingual",
    ]
    if key:
        command.extend(["--key", key])
    if measures:
        command.extend(["--measures", measures])
    proc = _run(command)
    manifest_path = output / "manifest.json"
    manifest = _json(manifest_path) if manifest_path.is_file() else None
    payload = {
        "state": "completed" if proc.returncode == 0 else "review_required",
        "source_id": source_id,
        "input_kind": "score-harmony-analyzer",
        "returncode": proc.returncode,
        "review_required": proc.returncode != 0,
        "manifest": manifest,
        "stdout_tail": proc.stdout[-4000:],
        "stderr_tail": proc.stderr[-4000:],
        "policy": {
            "omr_is_ground_truth": False,
            "visual_spot_check_required_for_verified_notation": True,
        },
    }
    output.mkdir(parents=True, exist_ok=True)
    _write_json(output / "theory-pedagogy-score-read.json", payload)
    return payload


def _load_segments(path: Path | None) -> tuple[TranscriptSegment, ...]:
    if path is None:
        return ()
    raw = _json(path.expanduser().resolve())
    if not isinstance(raw, list):
        raise ValueError("transcript segment file must contain a JSON list")
    return tuple(
        TranscriptSegment(
            str(item["segment_id"]),
            float(item["start_seconds"]),
            float(item["end_seconds"]),
            str(item["text"]),
            str(item["locator"]),
        )
        for item in raw
    )


def map_lecture(
    source: Path,
    output: Path,
    *,
    known_score: Path | None = None,
    transcript_segments: Path | None = None,
    allow_external_google: bool = False,
    google_context_hint: str | None = None,
) -> dict[str, object]:
    lecture_script = CAPLIN_ROOT / "scripts" / "lecture_audio_pipeline.py"
    if not lecture_script.is_file():
        raise RuntimeError("Caplin lecture-audio pipeline is unavailable")
    output = _require_new_directory(output)
    runtime_output = output / "runtime"
    command = [
        sys.executable,
        str(lecture_script),
        str(source.expanduser().resolve()),
        "--output",
        str(runtime_output),
    ]
    if known_score is not None:
        command.extend(["--known-score", str(known_score.expanduser().resolve())])
    if allow_external_google:
        command.append("--allow-external-google")
    if google_context_hint:
        command.extend(["--google-context-hint", google_context_hint])

    proc = _run(command, timeout=1200)
    manifest_path = runtime_output / "manifest.json"
    if not manifest_path.is_file():
        payload = {
            "state": "validation_unavailable",
            "returncode": proc.returncode,
            "stdout_tail": proc.stdout[-4000:],
            "stderr_tail": proc.stderr[-4000:],
        }
        _write_json(output / "theory-pedagogy-map.json", payload)
        return payload

    manifest = _json(manifest_path)
    mapped = map_caplin_manifest(
        manifest,
        transcript_segments=_load_segments(transcript_segments),
    )
    mapped["runtime_returncode"] = proc.returncode
    mapped["external_google_requested"] = allow_external_google
    mapped["state"] = (
        "mapped_with_review"
        if any(item.get("review_required") for item in mapped["mappings"])
        else "mapped"
    )
    _write_json(output / "theory-pedagogy-map.json", mapped)
    return mapped


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor")

    example = sub.add_parser("generate-example")
    example.add_argument("concept")
    example.add_argument("--output", "-o", required=True, type=Path)
    example.add_argument("--render", action="store_true")

    score = sub.add_parser("read-score")
    score.add_argument("source", type=Path)
    score.add_argument("--output", "-o", required=True, type=Path)
    score.add_argument("--source-id", required=True)
    score.add_argument("--key")
    score.add_argument("--measures")

    lecture = sub.add_parser("map-lecture")
    lecture.add_argument("source", type=Path)
    lecture.add_argument("--output", "-o", required=True, type=Path)
    lecture.add_argument("--known-score", type=Path)
    lecture.add_argument("--transcript-segments", type=Path)
    lecture.add_argument("--allow-external-google", action="store_true")
    lecture.add_argument("--google-context-hint")

    args = parser.parse_args()
    try:
        if args.command == "doctor":
            payload = doctor()
        elif args.command == "generate-example":
            payload = generate_example(args.concept, args.output, render=args.render)
        elif args.command == "read-score":
            payload = read_score(
                args.source,
                args.output,
                source_id=args.source_id,
                key=args.key,
                measures=args.measures,
            )
        else:
            payload = map_lecture(
                args.source,
                args.output,
                known_score=args.known_score,
                transcript_segments=args.transcript_segments,
                allow_external_google=args.allow_external_google,
                google_context_hint=args.google_context_hint,
            )
    except (ValueError, RuntimeError, OSError, subprocess.SubprocessError) as exc:
        print(json.dumps({"state": "failed", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())