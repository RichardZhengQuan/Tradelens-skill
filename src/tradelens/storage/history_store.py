"""Analysis history storage."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from tradelens.analysis.report_contract import (
    enforce_report_contract,
    ensure_report_disclaimer,
    is_full_analysis_report,
    is_probable_analysis_report,
)
from tradelens.analysis.report_writer import mark_report_saved


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
        stored_body = mark_report_saved(body, str(path)) if "## Saved Status" in body or "## **Saved Status**" in body else body
        if is_full_analysis_report(stored_body):
            stored_body = enforce_report_contract(stored_body)
        elif is_probable_analysis_report(stored_body):
            stored_body = ensure_report_disclaimer(stored_body)
        stored_body = _redact_secrets(stored_body)
        path.write_text(stored_body.rstrip() + "\n", encoding="utf-8")
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
        text = path.read_text(encoding="utf-8")
        if is_full_analysis_report(text):
            return enforce_report_contract(text)
        if is_probable_analysis_report(text):
            return ensure_report_disclaimer(text)
        return text

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


def _redact_secrets(text: str) -> str:
    secret_line = re.compile(
        r"(?im)^.*(?:api[_ -]?key|secret|token|password|2fa|sms code|recovery code)\s*[:=]\s*[A-Za-z0-9_\-./+=]{8,}.*$"
    )
    return secret_line.sub("[secret redacted]", text)
