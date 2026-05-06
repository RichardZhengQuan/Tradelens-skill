"""Append-first markdown storage."""

from __future__ import annotations

from pathlib import Path


class MarkdownStore:
    def __init__(self, root: Path):
        self.root = Path(root)

    def path(self, relative_path: str) -> Path:
        return self.root / relative_path

    def read(self, relative_path: str) -> str:
        path = self.path(relative_path)
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def append(self, relative_path: str, content: str) -> Path:
        path = self.path(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        existing = path.read_text(encoding="utf-8") if path.exists() else ""
        separator = "\n\n" if existing and not existing.endswith("\n\n") else ""
        path.write_text(f"{existing}{separator}{content.rstrip()}\n", encoding="utf-8")
        return path

