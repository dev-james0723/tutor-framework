"""Fresh limited checks; saved legacy assertions remain observations, not passes."""
from pathlib import Path
import json
import subprocess
from .cache import file_hash
from .mediaqa import release_decision


def verify(root, baseline_hashes=None):
    root = Path(root); output = root / "outputs"; checks = {}
    observations = json.loads((output / "validation.json").read_text())
    try:
        process = subprocess.run(["ffmpeg", "-v", "error", "-i", str(output/"lesson.mp4"), "-f", "null", "-"],
                                 capture_output=True, text=True, timeout=300)
        checks["decode"] = "passed" if process.returncode == 0 else "failed"
    except (OSError, subprocess.TimeoutExpired):
        checks["decode"] = "validation_unavailable"
    changed = []
    if baseline_hashes:
        baseline = json.loads(Path(baseline_hashes).read_text())
        for name, info in baseline.items():
            path = Path(name)
            if not path.is_file() or file_hash(path) != info["sha256"]:
                changed.append(name)
        checks["baseline_preserved"] = "passed" if baseline and not changed else "failed"
    decision = release_decision(checks)
    return {"checks": decision["checks"], "decision": decision,
            "legacy_observations_unverified": observations,
            "baseline_changes": changed, "lesson_sha256": file_hash(output/"lesson.mp4")}
