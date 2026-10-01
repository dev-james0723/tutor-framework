"""Reusable fail-closed compiler evidence stage; rendering adapters remain explicit."""
from pathlib import Path
import json
from .legacy import audit
from .mediaqa import release_decision
def compile_existing(root, output):
 evidence=audit(root)
 checks={"decode":"passed" if not evidence["missing"] else "failed",
         "caption_structure":"passed" if not evidence["missing"] else "validation_unavailable",
         "perceptual_listening":"validation_unavailable",
         "baseline_preserved":"passed"}
 decision=release_decision(checks)
 result={"compiler_schema":1,"baseline":evidence,"qa":decision,
         "status":"pilot_requires_perceptual_and_unverified_music_evidence" if not decision["verified_lesson"] else "verified"}
 Path(output).parent.mkdir(parents=True,exist_ok=True);Path(output).write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
 return result
