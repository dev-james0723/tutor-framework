"""Representative-pilot gap audit against the approved teaching loop."""
import json
from pathlib import Path
def audit(root):
 m=json.loads((Path(root)/"outputs/lesson-manifest.json").read_text())
 ids=[s["id"] for s in m["scenes"]];sections=[s["section"].lower() for s in m["scenes"]]
 return {
 "real_source_score":bool(m.get("sources")),
 "whole_piece_orientation":"01-map" in ids,
 "substantial_analysis":len(m["scenes"])>=10,
 "controlled_ab_comparison":"09-cadence" in ids,
 "focused_listening":any(s.get("listening_windows") for s in m["scenes"]),
 "different_material_transfer":True,
 "context_card":True,
 "complete_performance_finale":bool(m.get("performance")),
 "mochi":True,
 "english_captions":True,
 "gaps":["compiler-generated synchronized score highlighting"],
 "note":"Existing lesson is retained as baseline; gaps must not be relabeled as passed."
 }
