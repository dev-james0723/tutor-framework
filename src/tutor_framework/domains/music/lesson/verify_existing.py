"""Recompute evidence for the existing pilot without promoting unavailable review."""
from pathlib import Path
import hashlib,json,subprocess
from .adapters import midi_notes
from .mediaqa import release_decision
def sha(p):
 h=hashlib.sha256()
 with Path(p).open("rb") as f:
  for b in iter(lambda:f.read(1048576),b""):h.update(b)
 return h.hexdigest()
def verify(root, baseline_hashes=None):
 r=Path(root); o=r/"outputs"; w=r/"work"; v=json.loads((o/"validation.json").read_text()); m=json.loads((o/"lesson-manifest.json").read_text())
 p=subprocess.run(["ffmpeg","-v","error","-i",str(o/"lesson.mp4"),"-f","null","-"],capture_output=True,text=True)
 checks={}
 checks["decode"]="passed" if p.returncode==0 else "failed"
 checks["timebase"]="passed" if m.get("fps")==24 and all(abs(round(s["duration"]*24)-s["duration"]*24)<1e-6 for s in m["scenes"]) else "failed"
 checks["source_notation"]="passed" if v.get("notation_review") and all(x.get("notation_parse")=="pass" for x in v.get("music",[])) else "review_required"
 checks["caption_structure"]="passed" if all(x.get("caption_text_and_bounds")=="pass" for x in v.get("speech",[])) else "failed"
 checks["protected_listening"]="passed" if all(x.get("narration_overlap") is False for s in m["scenes"] for x in s.get("listening_windows",[])) else "failed"
 checks["loudness_and_clipping"]="passed" if max([x["peak"] for x in v.get("speech",[])]+[x["peak"] for x in v.get("music",[])])<1 else "failed"
 checks["notation_readability"]="passed" if not v.get("visual_layout",{}).get("scene_warnings") else "review_required"
 checks["layout_collisions"]=checks["notation_readability"]
 checks["caption_audio_review"]="validation_unavailable"
 checks["perceptual_listening"]="validation_unavailable"
 checks["context_provenance"]="review_required"
 checks["finale_identity_completeness"]="review_required"
 checks["score_audio_highlight"]="review_required"
 checks["repeat_traversal"]="review_required"
 symbolic=[]
 for name in ("EX-HC","EX-PAC","EX-IAC"):
  mid=w/"music"/(name+".mid")
  try:symbolic.append({"asset":name,"midi_attacks":len(midi_notes(mid.read_bytes())),"state":"parsed"})
  except Exception as e:symbolic.append({"asset":name,"state":"review_required","error":str(e)})
 checks["symbolic_midi"]="review_required" if any(x["state"]!="parsed" for x in symbolic) else "review_required"
 checks["scene_transitions"]="review_required"
 if baseline_hashes:
  base=json.load(open(baseline_hashes));changed=[]
  for name,info in base.items():
   p=Path(name)
   if not p.is_file() or sha(p)!=info["sha256"]:changed.append(name)
  checks["baseline_preserved"]="passed" if not changed else "failed"
 else: changed=[];checks["baseline_preserved"]="validation_unavailable"
 return {"checks":checks,"decision":release_decision(checks),"symbolic_midi_observation":symbolic,"baseline_changes":changed,"lesson_sha256":sha(o/"lesson.mp4")}
