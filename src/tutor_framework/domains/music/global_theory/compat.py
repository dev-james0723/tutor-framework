"""Explicit read-only bridge to a caller-selected frozen Caplin baseline."""
from __future__ import annotations

import hashlib
from pathlib import Path


class CaplinCompatibility:
    def __init__(self, root: Path, *, enabled: bool, allowed_files: tuple[str, ...],
                 provenance_id: str, tenant_id: str):
        if type(enabled) is not bool or not enabled or not provenance_id or not tenant_id or not allowed_files:
            raise ValueError("Caplin access requires explicit scope, tenant, and provenance")
        self.root = Path(root).expanduser().resolve(strict=True)
        if self.root.name != "caplin-baseline":
            raise ValueError("only frozen Caplin baseline is accepted")
        self.allowed_files = frozenset(allowed_files)
        self.provenance_id = provenance_id
        self.tenant_id = tenant_id

    def read(self, relative_path: str, *, tenant_id: str) -> dict:
        if tenant_id != self.tenant_id or relative_path not in self.allowed_files:
            raise ValueError("Caplin scope or tenant mismatch")
        relative = Path(relative_path)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("unsafe Caplin path")
        path = self.root / relative
        if path.is_symlink() or not path.resolve().is_relative_to(self.root) or not path.is_file():
            raise ValueError("Caplin file missing or outside frozen baseline")
        content = path.read_bytes()
        return {"content": content, "sha256": hashlib.sha256(content).hexdigest(),
                "relative_path": relative_path, "provenance_id": self.provenance_id,
                "tenant_id": self.tenant_id, "persistence": "none"}
