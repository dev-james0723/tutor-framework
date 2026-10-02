#!/usr/bin/env python3
"""Install only the new Global Music Theory identity; archive-only rollback."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import uuid
import sys
import subprocess
from pathlib import Path


IDENTITY = "global-music-theory-super-skill"


def _copy_code(source: Path, destination: Path) -> None:
    for path in source.rglob("*"):
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        if path.is_symlink():
            raise ValueError("symlink in public code bundle")
        relative = path.relative_to(source)
        if path.is_dir():
            (destination / relative).mkdir(parents=True, exist_ok=True)
        elif path.is_file() and path.suffix in {".py", ".json", ".cjs"}:
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


def install(repository: Path, destination: Path, *, with_caplin: bool = False, python_executable: str | None = None) -> dict:
    repository = Path(repository).expanduser().resolve(strict=True)
    destination = Path(destination).expanduser().resolve()
    interpreter = str(Path(python_executable or sys.executable).expanduser().absolute())
    if "\n" in interpreter or " " in interpreter or not os.access(interpreter, os.X_OK):
        raise ValueError("a safe executable Python path is required")
    source_skill = repository / "skills" / IDENTITY
    source_code = repository / "src" / "tutor_framework"
    if not (source_skill / "SKILL.md").is_file() or not source_code.is_dir():
        raise ValueError("reviewed skill and package sources are required")
    if destination.name == IDENTITY:
        raise ValueError("destination must be the parent skills directory, not the final skill path")
    target = destination / IDENTITY
    if target.exists() or target.is_symlink():
        raise ValueError("new skill already exists; refusing to replace")
    destination.mkdir(parents=True, exist_ok=True)
    staging = destination / ("." + IDENTITY + "-" + uuid.uuid4().hex)
    staging.mkdir(parents=False, exist_ok=False, mode=0o700)
    try:
        shutil.copy2(source_skill / "SKILL.md", staging / "SKILL.md")
        reference = staging / "references"
        reference.mkdir()
        shutil.copy2(repository / "docs/GLOBAL_MUSIC_THEORY.md", reference / "implementation.md")
        vendor = staging / "vendor" / "tutor_framework"
        vendor.mkdir(parents=True)
        _copy_code(source_code, vendor)
        if with_caplin:
            baseline = source_skill / "caplin-baseline"
            if not (baseline / "SKILL.md").is_file():
                raise ValueError("frozen Caplin baseline missing; no substitute is allowed")
            shutil.copytree(baseline, staging / "private" / "caplin-baseline", symlinks=True,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        if with_caplin:
            for private_path in (staging / "private").rglob("*"):
                if not private_path.is_symlink():
                    private_path.chmod(0o700 if private_path.is_dir() else 0o600)
            (staging / "private").chmod(0o700)
        executable = staging / "bin" / "global-music-theory"
        executable.parent.mkdir()
        executable.write_text("#!" + interpreter + "\n" +
                              "import sys\nfrom pathlib import Path\n"
                              "sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'vendor'))\n"
                              "from tutor_framework.domains.music.global_theory.__main__ import main\n"
                              "raise SystemExit(main())\n", encoding="utf-8")
        executable.chmod(0o755)
        hashes = {str(path.relative_to(staging)): hashlib.sha256(path.read_bytes()).hexdigest()
                  for path in staging.rglob("*") if path.is_file() and not path.is_symlink()}
        (staging / "install-manifest.json").write_text(
            json.dumps({"identity": IDENTITY, "version": "0.2.0", "files": hashes,
                        "caplin_baseline_copied": with_caplin, "python_executable": interpreter, "source_commit": subprocess.check_output(["git", "-C", str(repository), "rev-parse", "HEAD"], text=True).strip()}, indent=2)+"\n", encoding="utf-8")
        os.replace(staging, target)
        return {"state": "installed_new_identity", "path": str(target),
                "files_hashed": len(hashes), "caplin_baseline_copied": with_caplin}
    except Exception:
        shutil.rmtree(staging)
        raise


def rollback(destination: Path) -> dict:
    destination = Path(destination).expanduser().resolve()
    target = destination / IDENTITY
    manifest = target / "install-manifest.json"
    if not manifest.is_file() or json.loads(manifest.read_text()).get("identity") != IDENTITY:
        raise ValueError("only this new skill installation can be archived")
    archive = destination / (IDENTITY + ".rollback-" + uuid.uuid4().hex[:8])
    os.replace(target, archive)
    return {"state": "archived_new_identity", "archive": str(archive)}


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    commands = p.add_subparsers(dest="command", required=True)
    i = commands.add_parser("install"); i.add_argument("--repository", required=True)
    i.add_argument("--python-executable"); i.add_argument("--destination", required=True, help="Parent skills directory; the new skill identity is appended"); i.add_argument("--with-caplin", action="store_true")
    r = commands.add_parser("rollback"); r.add_argument("--destination", required=True)
    args = p.parse_args(argv)
    try:
        result = install(args.repository, args.destination, with_caplin=args.with_caplin, python_executable=args.python_executable) if args.command == "install" else rollback(args.destination)
        print(json.dumps(result, indent=2)); return 0
    except (OSError, ValueError) as error:
        print(json.dumps({"state": "blocked", "error": str(error)})); return 2


if __name__ == "__main__":
    raise SystemExit(main())
