"""Read-only replay of existing MinerU structured results; never submits an API job."""
from __future__ import annotations

import hashlib
import math
import json
import re
import shutil
import stat
import zipfile
from pathlib import Path, PurePosixPath


def _relative(name: str) -> PurePosixPath:
    if not isinstance(name, str) or not name or "\\" in name or "\x00" in name:
        raise ValueError("unsafe result path")
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in (".", "..") for part in path.parts) or ":" in path.parts[0]:
        raise ValueError("unsafe result path")
    return path


def _spans(node):
    if isinstance(node, dict):
        if node.get("type") in {"text", "image"} and ("content" in node or "image_path" in node):
            yield node
        for field in ("lines", "spans", "blocks"):
            for child in node.get(field, ()):
                yield from _spans(child)


def normalize_mineru_layout(layout: dict, *, extract_questions: bool = False) -> dict:
    if not isinstance(layout, dict) or not isinstance(layout.get("pdf_info"), list) or not layout["pdf_info"]:
        raise ValueError("structured MinerU pdf_info is required")
    pages = layout["pdf_info"]
    if [p.get("page_idx") for p in pages] != list(range(len(pages))):
        raise ValueError("MinerU page indices are missing or discontinuous")
    page_map = []
    blocks = []
    for page in pages:
        size = page.get("page_size")
        if (not isinstance(size, list) or len(size) != 2 or
                any(type(x) not in (int, float) or (not math.isfinite(x) or x <= 0) for x in size)):
            raise ValueError("MinerU page dimensions are required")
        width, height = size
        page_index = page["page_idx"]
        page_map.append({"pdf_page_index": page_index, "printed_page_label": "unknown",
                         "width": width, "height": height})
        for raw in page.get("para_blocks", []):
            bbox = raw.get("bbox")
            if not isinstance(bbox, list) or len(bbox) != 4 or not all(type(x) in (int, float) for x in bbox):
                raise ValueError("MinerU block has no valid page coordinates")
            normalized = [bbox[0] / width, bbox[1] / height, bbox[2] / width, bbox[3] / height]
            if not (0 <= normalized[0] < normalized[2] <= 1 and 0 <= normalized[1] < normalized[3] <= 1):
                raise ValueError("MinerU block outside page")
            spans = list(_spans(raw))
            images = [str(_relative(s["image_path"])) for s in spans if s.get("image_path")]
            text = "\n".join(str(s["content"]) for s in spans if s.get("type") == "text" and s.get("content"))
            blocks.append({"page": page_index, "bbox": normalized, "type": raw.get("type", "unknown"),
                           "reading_order": raw.get("index"), "text": text,
                           "image_path": images[0] if images else None, "image_paths": images,
                           "source_coordinates": list(bbox),
                           "review_status": "review_required"})
    result = {"page_map": page_map, "blocks": blocks,
              "flags": {"parsed": True, "musically_verified": False, "reviewed_usable": False},
              "parser_status": "structured_layout_candidate"}
    if extract_questions:
        questions = []
        current = None
        for block in blocks:
            text = block["text"].strip()
            match = re.match(r"^(\d+(?:\.\d+)*)[.)]\s*(.+)", text)
            if match:
                if current:
                    questions.append(current)
                number = match.group(1)
                mark = re.search(r"\((\d+)\s*marks?\)", match.group(2), re.I)
                current = {"original_number": number, "parent_number": number.rsplit(".", 1)[0] if "." in number else None,
                           "stem": match.group(2), "pages": [block["page"]],
                           "regions": [{"page": block["page"], "bbox": block["bbox"]}],
                           "options": [], "marks": int(mark.group(1)) if mark else None,
                           "response_type": "unknown", "concept_ids": [],
                           "review_status": "review_required", "parser_status": "candidate"}
                continue
            if current is None:
                continue
            if block["page"] not in current["pages"]:
                current["pages"].append(block["page"])
            current["regions"].append({"page": block["page"], "bbox": block["bbox"]})
            for line in text.splitlines():
                option = re.match(r"^\s*([A-H])[.)]\s*(.+)$", line)
                if option:
                    current["options"].append({"label": option.group(1), "text": option.group(2)})
            if current["options"]:
                current["response_type"] = "single_select_candidate"
        if current:
            questions.append(current)
        result["questions"] = questions
    return result


def load_existing_mineru_result(root: Path, *, expected_pdf_sha256: str,
                                extract_questions: bool = False) -> dict:
    root = Path(root).expanduser().resolve(strict=True)
    if not re.fullmatch(r"[a-f0-9]{64}", expected_pdf_sha256):
        raise ValueError("expected original PDF SHA-256 required")
    manifest_path = root / "manifest.json"
    if manifest_path.is_symlink() or manifest_path.stat().st_size > 1_000_000:
        raise ValueError("unsafe MinerU manifest")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "done" or not isinstance(manifest.get("files"), dict):
        raise ValueError("MinerU result is not completed")
    def local(name):
        rel = _relative(name)
        target = root.joinpath(*rel.parts)
        if target.is_symlink() or not target.resolve(strict=True).is_relative_to(root) or not target.is_file():
            raise ValueError("MinerU result path escapes its scope")
        return target
    source = local(manifest["files"]["pdf"])
    if not source.read_bytes().startswith(b"%PDF-"):
        raise ValueError("original PDF missing")
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    if source_hash != expected_pdf_sha256:
        raise ValueError("original PDF checksum mismatch")
    archive = local(manifest["files"]["result_zip"])
    with zipfile.ZipFile(archive) as zipped:
        entries = zipped.infolist()
        if len(entries) > 1000 or sum(x.file_size for x in entries) > 50_000_000:
            raise ValueError("MinerU result archive exceeds safe bounds")
        for info in entries:
            _relative(info.filename.rstrip("/"))
            if info.file_size > (16_000_000 if info.filename.endswith("layout.json") else 10_000_000) or stat.S_ISLNK(info.external_attr >> 16):
                raise ValueError("unsafe MinerU archive entry")
        candidates = [x for x in entries if x.filename.endswith("layout.json")]
        if len(candidates) != 1:
            raise ValueError("exactly one structured layout.json required")
        raw = zipped.read(candidates[0])
        if len(raw) > 16_000_000:
            raise ValueError("MinerU layout exceeds limit")
        layout = json.loads(raw)
        result = normalize_mineru_layout(layout, extract_questions=extract_questions)
        assets = {x.filename for x in entries}
        for block in result["blocks"]:
            references = []
            for original_path in block["image_paths"]:
                candidates = [name for name in (original_path, "images/" + original_path) if name in assets]
                if len(candidates) != 1:
                    raise ValueError("MinerU crop missing or ambiguous in result archive")
                actual = candidates[0]
                references.append({"original_path":original_path,"archive_path":actual,
                                   "sha256":hashlib.sha256(zipped.read(actual)).hexdigest()})
            block["image_references"] = references
            block["image_paths"] = [reference["archive_path"] for reference in references]
            block["image_path"] = block["image_paths"][0] if references else None
    result.update(parser_origin="existing_mineru_result_replay", new_api_submission=False,
                  source_sha256=source_hash, manifest_status="done")
    return result


def mineru_configuration() -> dict:
    helper = Path.home() / ".codex" / "skills" / "pdf-rag-parser" / "scripts" / "parse_pdf_rag.py"
    return {"helper_found": helper.is_file(), "helper_path": str(helper) if helper.is_file() else None,
            "cli_found": shutil.which("mineru-open-api") is not None,
            "new_api_submissions": 0, "result_replay_supported": True,
            "network_execution": "disabled_by_this_adapter"}
