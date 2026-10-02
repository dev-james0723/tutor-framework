"""Read-only legacy inventory. Presence of files is not audiovisual verification."""
from pathlib import Path
import json
from .legacy import audit
from .mediaqa import release_decision


def compile_existing(root, output):
    evidence = audit(root)
    checks = {"decode": "failed" if evidence["missing"] else "validation_unavailable"}
    decision = release_decision(checks)
    result = {"compiler_schema": 1, "baseline": evidence, "qa": decision,
              "status": "inventory_only_not_a_render_or_verification"}
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    return result
