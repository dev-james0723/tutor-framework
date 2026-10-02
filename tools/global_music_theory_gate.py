#!/usr/bin/env python3
"""Run the local Global Music Theory release checks without network or paid work."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def structural_check() -> dict:
    package = ROOT / "src/tutor_framework/domains/music/global_theory"
    count = 0
    for path in package.rglob("*.py"):
        compile(path.read_bytes(), str(path), "exec")
        count += 1
    data = package / "data"
    terms = json.loads((data / "terminology.json").read_text())
    curricula = json.loads((data / "curricula.json").read_text())
    resources = json.loads((data / "resources.json").read_text())
    relations = {"exact", "context-dependent", "broader", "narrower", "overlapping", "not-equivalent", "disputed"}
    if len(terms["records"]) != 100 or len(curricula["packs"]) != 44 or len(resources["resources"]) != 51:
        raise ValueError("registry counts changed")
    if any(t["relation"] not in relations or "definition" in t or "usage_example" in t for t in terms["records"]):
        raise ValueError("terminology relation or private content boundary changed")
    if any(r["processing_permission"] != "pending_scope_confirmation" or r["sha256"] is not None
           for r in resources["resources"]):
        raise ValueError("resource catalogue silently authorizes processing")
    for path in list(package.rglob("*.py")) + [ROOT / "tools/global_music_theory_install.py"]:
        for line in path.read_text().splitlines():
            if line.rstrip() != line:
                raise ValueError("trailing whitespace: " + str(path))
    return {"python_files_compiled_in_memory": count, "terms": 100, "curricula": 44, "resources": 51}


def main() -> int:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = str(ROOT / "src")
    try:
        static = structural_check()
        commands = [
            [sys.executable, "-m", "unittest", "discover", "-s", "tests/unit", "-p", "test_global*.py", "-v"],
            [sys.executable, "-m", "unittest", "tests.integration.test_global_learning_pack_adapter", "-v"],
            [sys.executable, "-m", "tutor_framework.release_gate", "."],
        ]
        checks = []
        for argv in commands:
            run = subprocess.run(argv, cwd=ROOT, env=env, capture_output=True, text=True)
            checks.append({"command": " ".join(argv), "exit_code": run.returncode,
                           "summary": (run.stderr or run.stdout).strip().splitlines()[-1:]})
            if run.returncode:
                print(run.stdout, file=sys.stderr)
                print(run.stderr, file=sys.stderr)
                print(json.dumps({"state": "failed", "static": static, "checks": checks}, indent=2))
                return run.returncode
        print(json.dumps({"state": "passed", "static": static, "checks": checks}, indent=2))
        return 0
    except (ValueError, OSError, SyntaxError, KeyError) as error:
        print(json.dumps({"state": "failed", "error": str(error)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
