"""Analysis history storage."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from tradelens.analysis.report_writer import ensure_report_disclaimer


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "analysis"


class HistoryStore:
    def __init__(self, history_dir: Path):
        self.history_dir = Path(history_dir)
        self.history_dir.mkdir(parents=True, exist_ok=True)

    def save(self, name: str, body: str, created_at: datetime) -> Path:
        stem = f"{created_at.strftime('%Y%m%d-%H%M%S')}-{slugify(name)}"
        path = self.history_dir / f"{stem}.md"
        suffix = 2
        while path.exists():
            path = self.history_dir / f"{stem}-{suffix}.md"
            suffix += 1
        path.write_text(body.rstrip() + "\n", encoding="utf-8")
        return path

    def list_all(self) -> List[Path]:
        return sorted(self.history_dir.glob("*.md"), reverse=True)

    def find(self, name: str) -> Path | None:
        target = slugify(name)
        for path in self.list_all():
            if path.name == name or path.stem == name or path.stem.endswith(target) or target in path.stem:
                return path
        return None

    def detail(self, name: str) -> str:
        path = self.find(name)
        if path is None:
            raise FileNotFoundError(f"No analysis history record matched: {name}")
        return ensure_report_disclaimer(path.read_text(encoding="utf-8"))

    def feedback_ratio(self) -> Dict[str, float]:
        total = 0
        accurate = 0
        not_accurate = 0
        no_feedback = 0
        for path in self.history_dir.glob("*.md"):
            total += 1
            text = path.read_text(encoding="utf-8").lower()
            if "feedback: accurate" in text:
                accurate += 1
            elif "feedback: not accurate" in text:
                not_accurate += 1
            else:
                no_feedback += 1
        feedback_count = accurate + not_accurate
        ratio = accurate / feedback_count if feedback_count else 0.0
        return {
            "total_analysis_count": total,
            "feedback_count": feedback_count,
            "accurate_count": accurate,
            "not_accurate_count": not_accurate,
            "no_feedback_count": no_feedback,
            "accuracy_ratio": ratio,
        }
