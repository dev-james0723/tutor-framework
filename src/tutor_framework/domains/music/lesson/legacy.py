"""Read-only reconciliation of the verified use-x20 baseline into compiler evidence."""
from pathlib import Path
import hashlib,json
def sha(p):
 h=hashlib.sha256()
 with Path(p).open("rb") as f:
  for b in iter(lambda:f.read(1048576),b""): h.update(b)
 return h.hexdigest()
def audit(root):
 root=Path(root); out=root/"outputs"; work=root/"work"
 manifest=json.loads((out/"lesson-manifest.json").read_text())
 validation=json.loads((out/"validation.json").read_text())
 required=[out/"lesson.mp4",out/"annotated-score.pdf",out/"lesson.srt",out/"lesson.vtt",out/"lesson-manifest.json",out/"receipt.json",out/"validation.json"]
 missing=[str(p) for p in required if not p.is_file()]
 return {"baseline_root":str(root),"missing":missing,"hashes":{str(p):sha(p) for p in required if p.is_file()},"scenes":len(manifest.get("scenes",[])),"manifest_state":manifest.get("state"),"validation":validation,"perceptual_review":manifest.get("voice",{}).get("perceptual_review","validation_unavailable"),"read_only":True}
