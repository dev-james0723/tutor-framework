"""Report manifest observations without inventing delivered pilot capabilities."""
import json
from pathlib import Path


def audit(root):
    manifest = json.loads((Path(root) / "outputs/lesson-manifest.json").read_text())
    scenes = manifest.get("scenes", [])
    ids = {scene.get("id", scene.get("scene_id")) for scene in scenes}
    # Presence checks intentionally do not certify musical accuracy or rendering.
    transfer = any(scene.get("stage") == "transfer" and scene.get("passage_id")
                   and scene.get("transfer_from_passage_id")
                   and scene["passage_id"] != scene["transfer_from_passage_id"]
                   and scene.get("state") == "rendered" for scene in scenes)
    contexts = manifest.get("contexts", [])
    context = bool(contexts) and any(scene.get("context_id") in {
        card.get("card_id") for card in contexts} and scene.get("state") == "rendered"
        for scene in scenes)
    result = {
        "real_source_score": bool(manifest.get("sources")),
        "whole_piece_orientation": "01-map" in ids,
        "substantial_analysis": len(scenes) >= 10,
        "controlled_ab_comparison": "09-cadence" in ids,
        "focused_listening": any(scene.get("focused_listening") for scene in scenes),
        "different_material_transfer": transfer,
        "context_card": context,
        "complete_performance_finale": bool(manifest.get("performance")),
        "mochi": any(scene.get("mochi") or scene.get("visual", {}).get("mochi") not in (None, "none") for scene in scenes),
        "english_captions": manifest.get("language") == "English" and (Path(root)/"outputs/lesson.srt").is_file(),
    }
    result["gaps"] = [name for name, present in result.items() if not present]
    result["note"] = "Manifest observations only, not audiovisual acceptance. No inferred capability is passed."
    return result
