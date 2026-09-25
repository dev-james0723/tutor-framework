"""Offline release checks for the public tutor framework boundary."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from tutor_framework.packs.manifest import load_manifest


def run_release_gate(root: str | Path) -> tuple[str, ...]:
    root = Path(root)
    findings: list[str] = []
    findings.extend(_check_required_files(root))
    findings.extend(_check_family_manifests(root))
    findings.extend(_check_skill_registry(root))
    findings.extend(_check_multilingual_fixture(root))
    findings.extend(_scan_unresolved_markers(root))
    return tuple(findings)


def _check_required_files(root: Path) -> list[str]:
    required = (
        "pyproject.toml",
        "README.md",
        "src/tutor_framework/__init__.py",
        "packs/template/manifest.template.json",
        "evals/music/synthetic_cases.json",
    )
    return [f"missing required file: {path}" for path in required if not (root / path).is_file()]


def _check_family_manifests(root: Path) -> list[str]:
    findings: list[str] = []
    paths = sorted((root / "packs" / "families").glob("*.json"))
    if len(paths) != 12:
        findings.append(f"expected 12 family manifests, found {len(paths)}")
    occupations: list[str] = []
    for path in paths:
        try:
            manifest = load_manifest(path)
        except ValueError as exc:
            findings.append(f"invalid pack {path.name}: {exc}")
            continue
        occupations.extend(manifest.occupations)
    if len(occupations) != 27:
        findings.append(f"expected 27 occupation groups, found {len(occupations)}")
    if len(set(occupations)) != len(occupations):
        findings.append("occupation groups are duplicated across family manifests")
    return findings


def _check_skill_registry(root: Path) -> list[str]:
    path = root / "docs" / "skill-adoption-registry.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"invalid skill adoption registry: {exc}"]
    findings: list[str] = []
    for item in payload.get("skills", []):
        if item.get("external_execution") is not False:
            findings.append(f"skill is not fail-closed: {item.get('skill_id')}")
    return findings


def _check_multilingual_fixture(root: Path) -> list[str]:
    path = root / "evals" / "fixtures" / "multilingual.json"
    try:
        cases = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"invalid multilingual fixture: {exc}"]
    locales = {case.get("locale") for case in cases}
    if not {"en-US", "zh-Hant-HK", "es-ES"}.issubset(locales):
        return ["multilingual fixture must cover en-US, zh-Hant-HK and es-ES"]
    return []


def _scan_unresolved_markers(root: Path) -> list[str]:
    findings: list[str] = []
    scan_roots = (root / "src", root / "tests", root / "packs", root / "evals")
    markers = ("TODO", "FIXME", "NotImplemented", "XXX")
    for scan_root in scan_roots:
        if not scan_root.exists():
            continue
        for path in scan_root.rglob("*"):
            if not path.is_file() or path.suffix not in {".py", ".json", ".md"}:
                continue
            if path.name == "release_gate.py":
                continue
            text = path.read_text(encoding="utf-8")
            for marker in markers:
                if marker in text:
                    findings.append(f"unresolved marker {marker} in {path.relative_to(root)}")
    return findings


if __name__ == "__main__":
    project_root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    errors = run_release_gate(project_root)
    if errors:
        print("release gate failed")
        print("\n".join(errors))
        raise SystemExit(1)
    print("release gate passed")
