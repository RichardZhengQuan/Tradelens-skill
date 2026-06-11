"""Deterministic TradeLens report contract enforcement."""

from __future__ import annotations

import os
import re
from typing import Iterable


DISCLAIMER = (
    "Not financial advice. This assessment is based only on information you provided, local TradeLens records, "
    "and available public/provider data; missing or stale data may change the result."
)

ALLOWED_JUDGMENTS = {
    "good",
    "mostly good",
    "neutral",
    "mostly bad",
    "bad",
    "no clear edge",
}

DISPLAY_JUDGMENTS = {
    "GOOD",
    "MOSTLY GOOD",
    "NEUTRAL",
    "MOSTLY BAD",
    "BAD",
    "NO CLEAR EDGE",
}

FORBIDDEN_ACTION_PATTERNS = [
    # English
    r"\byou should\b",
    r"\bi recommend\b",
    r"\brecommend(ed|ation)?\b",
    r"\bsuggest(ed|ion|ions|ing)?\b",
    r"\bbest action\b",
    r"\bpreferred action\b",
    r"\bsuggested action\b",
    r"\bfinal action\b",
    r"\bdo not buy\b",
    r"\bdo not sell\b",
    r"\bdo not wait\b",
    r"\bwait\b",
    r"\bbuy now\b",
    r"\bsell now\b",
    r"\broll\b",
    r"\bclose\b",
    r"\bhold\b",
    # Field-like action outputs
    r"\bfinal_action\b",
    r"\bpreferred_action\b",
    r"\brecommended_action\b",
    r"\bsuggested_action\b",
    r"\bbest_action\b",
    r"\bdecision_gate\b",
    # Chinese action-advice patterns
    r"建议",
    r"我建议",
    r"不要买",
    r"不要卖",
    r"别买",
    r"别卖",
    r"先别",
    r"等待",
    r"观望",
    r"加仓",
    r"减仓",
    r"平仓",
    r"止盈",
    r"止损",
    r"可以考虑",
    r"更合理的下一步",
    r"下一步",
    r"直接再卖",
    r"直接买",
    r"直接卖",
    # Older localized action terms already covered by tests.
    r"买入",
    r"卖出",
    r"持有",
    r"滚仓",
    r"加对冲",
]

REQUIRED_SECTIONS = [
    "## **Term-Aware Trade Judgment**",
    "## Why",
    "## What I Parsed",
    "## Key Numbers",
    "## Risk Check",
    "## Missing Data / Confirmation Needed",
    "## Data Used",
    "## Saved Status",
]

_DISPLAY_JUDGMENT_RE = "|".join(sorted(DISPLAY_JUDGMENTS, key=len, reverse=True))
_TITLE_RE = re.compile(rf"^# \*\*({_DISPLAY_JUDGMENT_RE}) — .+\*\*$")
_STRICT_VALUES = {"1", "true", "yes", "on", "test"}

_SANITIZER_REPLACEMENTS = [
    (
        r"先别直接再卖第二张[。.]?",
        "As a second short put, this setup is MOSTLY BAD because it would double assignment exposure.",
    ),
    (
        r"我建议\s*wait\s*/?\s*不直接加仓[。.]?",
        "This trade has NO CLEAR EDGE because related exposure may already cover the same idea.",
    ),
    (
        r"可以考虑更低\s*strike\s*或\s*put\s*spread\s*限定风险[。.]?",
        "The trade quality would improve if assignment exposure were lower or downside risk were more limited.",
    ),
    (
        r"不要买\s*100\s*股[。.]?",
        "Buying 100 shares is MOSTLY BAD for short-term account structure because it concentrates single-symbol exposure.",
    ),
    (r"\byou should\b", "this trade profile"),
    (r"\bi recommend\b", "trade quality indicates"),
    (r"\brecommend(ed|ation)?\b", "trade-quality assessment"),
    (r"\bsuggest(ed|ion|ions|ing)?\b", "trade-quality condition"),
    (r"\bbest action\b", "trade-quality assessment"),
    (r"\bpreferred action\b", "trade-quality assessment"),
    (r"\bsuggested action\b", "trade-quality assessment"),
    (r"\bfinal action\b", "trade-quality assessment"),
    (r"\bdo not buy\b", "the entry profile has weak trade quality"),
    (r"\bdo not sell\b", "the sale profile has weak trade quality"),
    (r"\bdo not wait\b", "the timing profile has weak trade quality"),
    (r"\bwait\b", "no clear edge"),
    (r"\bbuy now\b", "immediate entry profile"),
    (r"\bsell now\b", "immediate exit profile"),
    (r"\broll\b", "option-adjustment profile"),
    (r"\bclose\b", "position-exit profile"),
    (r"\bhold\b", "longer-term exposure profile"),
    (r"\bfinal_action\b", "trade_quality_summary"),
    (r"\bpreferred_action\b", "trade_quality_summary"),
    (r"\brecommended_action\b", "trade_quality_summary"),
    (r"\bsuggested_action\b", "trade_quality_summary"),
    (r"\bbest_action\b", "trade_quality_summary"),
    (r"\bdecision_gate\b", "confirmation_needed"),
    (r"我建议", "本次交易质量显示"),
    (r"建议", "交易质量显示"),
    (r"不要买", "买方结构质量偏弱"),
    (r"不要卖", "卖方结构质量偏弱"),
    (r"别买", "买方结构质量偏弱"),
    (r"别卖", "卖方结构质量偏弱"),
    (r"先别", "该结构目前"),
    (r"等待", "无明确优势"),
    (r"观望", "无明确优势"),
    (r"加仓", "增加仓位暴露"),
    (r"减仓", "降低仓位暴露"),
    (r"平仓", "退出仓位结构"),
    (r"止盈", "盈亏管理条件"),
    (r"止损", "风险限制条件"),
    (r"可以考虑", "交易质量会改善如果"),
    (r"更合理的下一步", "更清晰的质量改善条件"),
    (r"下一步", "后续质量条件"),
    (r"直接再卖", "第二张合约结构"),
    (r"直接买", "买方结构"),
    (r"直接卖", "卖方结构"),
    (r"买入", "stock-entry structure"),
    (r"卖出", "sale-structure"),
    (r"持有", "longer-term exposure profile"),
    (r"滚仓", "option-adjustment profile"),
    (r"加对冲", "hedge-structure exposure"),
]


class ReportContractViolation(ValueError):
    """Raised when a report cannot satisfy the fixed TradeLens contract."""

    def __init__(self, violations: Iterable[str]):
        self.violations = list(violations)
        super().__init__("; ".join(self.violations))


def normalize_trade_judgment(value: str) -> str:
    normalized = (value or "no clear edge").strip().lower()
    return normalized if normalized in ALLOWED_JUDGMENTS else "no clear edge"


def display_judgment(value: str) -> str:
    return normalize_trade_judgment(value).upper()


def strict_report_contract_enabled() -> bool:
    return os.environ.get("TRADELENS_STRICT_REPORT_CONTRACT", "").strip().lower() in _STRICT_VALUES


def ensure_report_disclaimer(report: str) -> str:
    """Insert the standard disclaimer immediately after the title, exactly once."""

    if not report:
        return DISCLAIMER + "\n"
    lines = [line for line in report.splitlines() if line.strip() != DISCLAIMER]
    if lines and lines[0].startswith("# "):
        title = lines[0]
        rest = lines[1:]
        while rest and not rest[0].strip():
            rest.pop(0)
        lines = [title, "", DISCLAIMER, ""] + rest
    else:
        while lines and not lines[0].strip():
            lines.pop(0)
        lines = [DISCLAIMER, ""] + lines
    return "\n".join(lines).rstrip() + "\n"


def sanitize_report_text(text: object) -> str:
    """Rewrite action-advice wording into neutral trade-quality language."""

    sanitized = "unknown" if text in (None, "") else str(text)
    for pattern, replacement in _SANITIZER_REPLACEMENTS:
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
    return sanitized


def find_forbidden_action_language(report: str) -> list[str]:
    return [
        pattern
        for pattern in FORBIDDEN_ACTION_PATTERNS
        if re.search(pattern, report or "", flags=re.IGNORECASE)
    ]


def validate_report_contract(report: str) -> None:
    violations: list[str] = []
    text = report or ""
    lines = text.splitlines()
    first_line = lines[0] if lines else ""

    if not _TITLE_RE.match(first_line):
        violations.append("title must start with an allowed display judgment")

    disclaimer_count = text.count(DISCLAIMER)
    if disclaimer_count != 1:
        violations.append(f"disclaimer must appear exactly once, found {disclaimer_count}")

    term_index = text.find("## **Term-Aware Trade Judgment**")
    disclaimer_index = text.find(DISCLAIMER)
    if term_index == -1:
        violations.append("Term-Aware Trade Judgment section is missing")
    elif disclaimer_index == -1 or disclaimer_index > term_index:
        violations.append("disclaimer must appear before Term-Aware Trade Judgment")

    actual_sections = re.findall(r"^## .+$", text, flags=re.MULTILINE)
    if actual_sections != REQUIRED_SECTIONS:
        violations.append("required sections must appear in exact contract order")

    if term_index != -1:
        prefix = text[:term_index]
        score_before_term_patterns = [
            r"(?im)^##\s*Trade Score\b",
            r"(?i)\boverall score\b",
            r"(?i)\btrade score\b",
            r"(?im)^-\s*score:\s*\d+",
        ]
        for pattern in score_before_term_patterns:
            if re.search(pattern, prefix):
                violations.append("single score appears before term-aware judgment")
                break

    forbidden = find_forbidden_action_language(text)
    if forbidden:
        violations.append("forbidden action-advice language found: " + ", ".join(forbidden))

    if violations:
        raise ReportContractViolation(violations)


def enforce_report_contract(report: str, *, strict: bool | None = None) -> str:
    """Apply deterministic contract fixes, then validate or return a safe fallback."""

    strict = strict_report_contract_enabled() if strict is None else strict
    sanitized = ensure_report_disclaimer(sanitize_report_text(report))
    try:
        validate_report_contract(sanitized)
        return sanitized
    except ReportContractViolation:
        if strict:
            raise
    fallback = contract_safe_fallback_report()
    validate_report_contract(fallback)
    return fallback


def is_full_analysis_report(report: str) -> bool:
    text = report or ""
    return text.startswith("# **") and all(section in text for section in REQUIRED_SECTIONS)


def is_probable_analysis_report(report: str) -> bool:
    return (report or "").lstrip().startswith("# **")


def contract_safe_fallback_report() -> str:
    return f"""# **NO CLEAR EDGE — Report contract fallback**

{DISCLAIMER}

The generated draft could not be published without violating TradeLens report rules.
This fallback treats the setup as no clear edge until inputs, market data, and exposure fit are confirmed.
trade_judgment: no clear edge
score stability: unstable

## **Term-Aware Trade Judgment**

| Term | Judgment | Score | Why |
|---|---|---:|---|
| Intraday | NO CLEAR EDGE | 0/100 | Contract-safe fallback has insufficient intraday evidence |
| Short-term | NO CLEAR EDGE | 0/100 | Contract-safe fallback has insufficient short-term evidence |
| Medium-term | NO CLEAR EDGE | 0/100 | Contract-safe fallback has insufficient medium-term evidence |
| Long-term | NO CLEAR EDGE | 0/100 | Contract-safe fallback has insufficient long-term evidence |

## Why
- The previous draft failed deterministic report validation.
- Trade quality cannot be scored from the safe fallback alone.

## What I Parsed
- Confirmation status: analysis draft only.
- Related symbol: unknown.
- User question: unavailable in contract-safe fallback.
- Visible facts:
- none
- User claims:
- none
- Parsed order lines:
- none
- AI inferences:
- prior draft was not contract-safe
- Assumptions:
- missing or unsafe wording weakens the evaluation

## Key Numbers
- Overall score summary: 0/100 after the term-aware judgments above.
- Expected value: unknown.
- Win probability: unknown.
- Max reasonable gain: unknown.
- Max reasonable loss: unknown.
- Capital required: unknown.
- Return on capital: unknown.
- Underlying price: unknown.
- Option mechanics:
- unknown

## Risk Check
- Top risks:
- missing confirmed trade details
- missing market data
- Missing confirmed exposure fit weakens trade quality.
- This trade becomes worse if:
- confirmed exposure is larger than assumed
- This trade becomes better if:
- assignment exposure is lower or downside risk is more limited
- Invalidation conditions:
- confirmed inputs materially differ from the draft

## Missing Data / Confirmation Needed
- Missing data:
- original contract-safe inputs
- Score notes:
- fallback generated by deterministic report contract enforcement
- Confirmation needed: trade details, position size, premium, expiry, strike, market data, and exposure fit.
- Confidence: Low

## Data Used
- Analysis time: unknown
- Raw provider data quality: low
- Classified data quality: low
- Reason for downgrade: contract fallback
- Fallback path used: contract fallback
- Data quality adjustment: -20

**Market data status**
| Data | Status | Provider / Source | Freshness | Quality | Notes |
|---|---|---|---|---|---|
| Underlying price | missing | missing | unknown | low | contract fallback |

**OpenD provider status**
| Item | Status |
|---|---|
| Provider type | unknown |
| OpenD reachable | no |
| Host | 127.0.0.1 |
| Port | 11111 |
| Read-only mode | yes |
| Trading enabled | no |
| Password stored | no |
| Test quote | failed |

**Provider attempts**
| Capability | Attempted Provider | Result | Error / Note |
|---|---|---|---|
| unknown | none | missing | contract fallback |

## Saved Status
- Analysis saved: no
- Analysis path: not saved
- Trade log updated: no
- Reason: contract-safe fallback generated
- Feedback status: no feedback
"""
