import re
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tradelens.analysis.engine import AnalysisEngine
from tradelens.analysis.report_contract import (
    DISCLAIMER,
    REQUIRED_SECTIONS,
    ReportContractViolation,
    find_forbidden_action_language,
    sanitize_report_text,
    validate_report_contract,
)
from tradelens.analysis.report_writer import write_analysis_report
from tradelens.data.providers.manual_provider import ManualMarketDataProvider
from tradelens.models import MarketSnapshot, Scenario
from tradelens.storage.history_store import HistoryStore


SCENARIOS = [
    Scenario("base", 0.55, 180),
    Scenario("downside", 0.35, -400),
    Scenario("worst", 0.10, -1200),
]

FORBIDDEN_ENGLISH = [
    "wait",
    "you should",
    "i recommend",
    "recommend",
    "preferred action",
    "suggested action",
    "best action",
    "do not buy",
    "do not sell",
]

FORBIDDEN_CHINESE = [
    "建议",
    "我建议",
    "先别",
    "不要买",
    "不要卖",
    "等待",
    "观望",
    "加仓",
    "减仓",
    "平仓",
    "可以考虑",
    "下一步",
    "直接再卖",
    "直接买",
    "直接卖",
]

ALLOWED_TITLE_LABELS = "GOOD|MOSTLY GOOD|NEUTRAL|MOSTLY BAD|BAD|NO CLEAR EDGE"


class ReportContractTest(unittest.TestCase):
    def _provider(self):
        return ManualMarketDataProvider(
            snapshot=MarketSnapshot(
                symbol="NVDA",
                source="manual",
                last_updated=datetime.now(timezone.utc).isoformat(),
                regular_hours_price=210,
                data_quality="high",
            )
        )

    def _report(self, question="Evaluate this trade", **kwargs):
        result = AnalysisEngine(self._provider()).analyze_trade(
            symbol="NVDA",
            question=question,
            scenarios=SCENARIOS,
            max_data_age_minutes=15,
            **kwargs,
        )
        return write_analysis_report(result), result

    def assertContractSafe(self, report):
        validate_report_contract(report)
        self.assertFalse(find_forbidden_action_language(report))

    def test_generated_report_contains_disclaimer_once_before_term_judgment(self):
        report, _ = self._report()

        self.assertEqual(report.count(DISCLAIMER), 1)
        self.assertLess(report.index(DISCLAIMER), report.index("## **Term-Aware Trade Judgment**"))
        self.assertContractSafe(report)

    def test_saved_analysis_history_file_contains_disclaimer(self):
        report, result = self._report()

        with tempfile.TemporaryDirectory() as tmp:
            path = HistoryStore(Path(tmp)).save("NVDA report", report, result.created_at)
            saved = path.read_text(encoding="utf-8")

        self.assertEqual(saved.count(DISCLAIMER), 1)
        self.assertLess(saved.index(DISCLAIMER), saved.index("## **Term-Aware Trade Judgment**"))
        self.assertContractSafe(saved)

    def test_history_detail_output_contains_disclaimer_once(self):
        report, result = self._report()

        with tempfile.TemporaryDirectory() as tmp:
            store = HistoryStore(Path(tmp))
            store.save("NVDA report", report, result.created_at)
            detail = store.detail("NVDA report")

        self.assertEqual(detail.count(DISCLAIMER), 1)
        self.assertContractSafe(detail)

    def test_forbidden_english_action_language_is_removed_from_final_report(self):
        report, _ = self._report(
            "you should wait; I recommend; preferred action; suggested action; best action; do not buy; do not sell"
        )
        lowered = report.lower()

        for phrase in FORBIDDEN_ENGLISH:
            self.assertNotIn(phrase, lowered)
        self.assertContractSafe(report)

    def test_forbidden_chinese_action_language_is_removed_from_final_report(self):
        report, _ = self._report(
            "我建议先别直接再卖第二张，可以考虑更低 strike 或 put spread 限定风险，等待观望，不要买，不要卖，下一步加仓减仓平仓"
        )

        for phrase in FORBIDDEN_CHINESE:
            self.assertNotIn(phrase, report)
        self.assertContractSafe(report)

    def test_validate_report_contract_raises_on_unsanitized_action_advice(self):
        bad_report = f"""# **NO CLEAR EDGE — Bad draft**

{DISCLAIMER}

you should wait

## **Term-Aware Trade Judgment**

| Term | Judgment | Score | Why |
|---|---|---:|---|
| Intraday | NO CLEAR EDGE | 0/100 | draft |
| Short-term | NO CLEAR EDGE | 0/100 | draft |
| Medium-term | NO CLEAR EDGE | 0/100 | draft |
| Long-term | NO CLEAR EDGE | 0/100 | draft |

## Why
## What I Parsed
## Key Numbers
## Risk Check
## Missing Data / Confirmation Needed
## Data Used
## Saved Status
"""

        with self.assertRaises(ReportContractViolation):
            validate_report_contract(bad_report)

    def test_sanitizer_rewrites_exact_bad_examples_to_quality_language(self):
        bad_text = "\n".join(
            [
                "先别直接再卖第二张。",
                "我建议 wait / 不直接加仓。",
                "可以考虑更低 strike 或 put spread 限定风险。",
                "不要买 100 股。",
            ]
        )
        sanitized = sanitize_report_text(bad_text)

        self.assertIn("As a second short put, this setup is MOSTLY BAD", sanitized)
        self.assertIn("This trade has NO CLEAR EDGE", sanitized)
        self.assertIn("The trade quality would improve", sanitized)
        self.assertIn("Buying 100 shares is MOSTLY BAD", sanitized)
        for phrase in FORBIDDEN_CHINESE + ["wait"]:
            self.assertNotIn(phrase, sanitized)

    def test_required_structure_is_enforced(self):
        report, _ = self._report()
        sections = re.findall(r"^## .+$", report, flags=re.MULTILINE)

        self.assertRegex(report.splitlines()[0], rf"^# \*\*({ALLOWED_TITLE_LABELS}) — .+\*\*$")
        self.assertEqual(sections, REQUIRED_SECTIONS)
        self.assertLess(report.index("## **Term-Aware Trade Judgment**"), report.index("## Why"))
        self.assertLess(report.index(DISCLAIMER), report.index("## **Term-Aware Trade Judgment**"))
        self.assertNotIn("Trade Score", report[: report.index("## **Term-Aware Trade Judgment**")])
        self.assertNotIn("Overall score", report[: report.index("## **Term-Aware Trade Judgment**")])
        self.assertContractSafe(report)

    def test_exact_nvda_short_put_regression_is_contract_safe(self):
        report, result = self._report(
            "卖 nvda 这周到期的 put，207.5，一张",
            option_expiry="2026-05-01",
            option_strike=207.5,
            option_type="put",
            strategy_type="cash-secured put",
            existing_related_exposure=["NVDA 2026-05-01 207.50 short put"],
        )

        self.assertIn(DISCLAIMER, report)
        self.assertEqual(result.trade_judgment, "no clear edge")
        self.assertRegex(report.splitlines()[0], rf"^# \*\*({ALLOWED_TITLE_LABELS}) — .+\*\*$")
        self.assertIn("## **Term-Aware Trade Judgment**", report)
        self.assertIn("new second contract or the existing option position", report)
        self.assertNotIn("先别", report)
        self.assertNotIn("建议", report)
        self.assertNotIn("wait", report.lower())
        self.assertContractSafe(report)


if __name__ == "__main__":
    unittest.main()
