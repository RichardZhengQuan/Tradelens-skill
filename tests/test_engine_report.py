import sys
import tempfile
import unittest
import re
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tradelens.analysis.engine import AnalysisEngine
from tradelens.analysis.report_contract import find_forbidden_action_language, validate_report_contract
from tradelens.analysis.report_writer import STANDARD_DISCLAIMER, render_analysis_report, write_analysis_report
from tradelens.data.market_snapshot import ProviderStatus, QuoteSnapshot
from tradelens.data.provider_base import CAP_QUOTE, MarketDataProvider
from tradelens.data.provider_resolver import ProviderResolver, resolve_market_data_provider
from tradelens.data.providers.manual_provider import ManualMarketDataProvider
from tradelens.models import MarketSnapshot, Scenario, ScoreBreakdown, TradeIntent, TradeScore, TradeTerm
from tradelens.storage.history_store import HistoryStore


REQUESTED_SCENARIOS = [
    Scenario("base", 0.77, 800),
    Scenario("downside", 0.13, -200),
    Scenario("worst", 0.10, -300),
]

REQUIRED_REPORT_SECTIONS = [
    "## **Term-Aware Trade Judgment**",
    "## Why",
    "## What I Parsed",
    "## Key Numbers",
    "## Risk Check",
    "## Missing Data / Confirmation Needed",
    "## Data Used",
    "## Saved Status",
]

ALLOWED_TITLE_LABELS = "GOOD|MOSTLY GOOD|NEUTRAL|MOSTLY BAD|BAD|NO CLEAR EDGE"


class StubMarketDataProvider(MarketDataProvider):
    name = "stub"

    def __init__(self, quote=None):
        self.quote = quote

    def capabilities(self):
        return {CAP_QUOTE}

    def get_quote(self, symbol):
        if self.quote:
            return self.quote, ProviderStatus(
                provider_name=self.name,
                capability=CAP_QUOTE,
                available=True,
                status="found",
                data_quality=self.quote.data_quality,
                data_time=self.quote.data_time,
            )
        return None, ProviderStatus(
            provider_name=self.name,
            capability=CAP_QUOTE,
            available=False,
            status="missing",
            error="quote missing",
            missing_fields=["underlying realtime/latest price"],
        )


class EngineReportTest(unittest.TestCase):
    def _fresh_provider(self):
        return ManualMarketDataProvider(
            snapshot=MarketSnapshot(
                symbol="NVDA",
                source="manual",
                last_updated=datetime.now(timezone.utc).isoformat(),
                regular_hours_price=100,
                data_quality="high",
            )
        )

    def test_stale_high_quality_snapshot_gets_data_penalty(self):
        provider = ManualMarketDataProvider(
            snapshot=MarketSnapshot(
                symbol="NVDA",
                source="manual",
                last_updated="2020-01-01T00:00:00+00:00",
                regular_hours_price=100,
                data_quality="high",
            )
        )
        result = AnalysisEngine(provider).analyze_trade(
            symbol="NVDA",
            question="Should I take this trade?",
            scenarios=REQUESTED_SCENARIOS,
            max_data_age_minutes=15,
        )

        self.assertEqual(result.trade_score.breakdown.data_quality_adjustment, -17)
        self.assertEqual(result.trade_score.label, "no clear edge")
        self.assertEqual(result.trade_judgment, "no clear edge")
        self.assertEqual(result.classified_data_quality, "low")

        report = write_analysis_report(result)
        self.assertIn("- Raw provider data quality: high", report)
        self.assertIn("- Classified data quality: low", report)
        self.assertIn("- Reason for downgrade: market data is older than the configured 15-minute freshness limit", report)

    def test_report_includes_required_evaluation_sections(self):
        result = AnalysisEngine(self._fresh_provider()).analyze_trade(
            symbol="NVDA",
            question="Should I take this trade?",
            scenarios=REQUESTED_SCENARIOS,
            max_data_age_minutes=15,
        )
        report = write_analysis_report(result)
        sections = re.findall(r"^## .+$", report, flags=re.MULTILINE)

        self.assertEqual(sections, REQUIRED_REPORT_SECTIONS)
        self.assertRegex(report.splitlines()[0], rf"^# \*\*({ALLOWED_TITLE_LABELS}) — .+\*\*$")
        self.assertIn("trade_judgment:", report)
        self.assertNotIn("- trade_verdict:", report)
        self.assertLess(report.index("## **Term-Aware Trade Judgment**"), report.index("## Why"))

    def test_every_generated_analysis_report_contains_disclaimer_once_near_top(self):
        result = AnalysisEngine(self._fresh_provider()).analyze_trade(
            symbol="NVDA",
            question="Evaluate this trade",
            scenarios=REQUESTED_SCENARIOS,
            max_data_age_minutes=15,
        )
        report = write_analysis_report(result)

        self.assertIn(STANDARD_DISCLAIMER, report)
        self.assertLess(report.index(STANDARD_DISCLAIMER), report.index("## **Term-Aware Trade Judgment**"))
        self.assertEqual(report.count(STANDARD_DISCLAIMER), 1)

    def test_legacy_render_analysis_report_low_quality_forces_no_clear_edge(self):
        report = render_analysis_report(
            TradeScore(
                label="good",
                score=95,
                stability="stable",
                breakdown=ScoreBreakdown(),
                scenarios=REQUESTED_SCENARIOS,
                expected_value=700,
                win_probability=0.77,
            ),
            question="Legacy caller score",
            symbol="NVDA",
        )

        self.assertTrue(report.splitlines()[0].startswith("# **NO CLEAR EDGE"))
        self.assertIn("trade_judgment: no clear edge", report)
        self.assertNotRegex(report.splitlines()[0], r"# \*\*(GOOD|MOSTLY GOOD)")

    def test_legacy_render_analysis_report_passes_report_contract(self):
        report = render_analysis_report(
            TradeScore("mostly good", 75, "stable", ScoreBreakdown(), REQUESTED_SCENARIOS),
            question="Legacy caller score",
            symbol="NVDA",
        )

        validate_report_contract(report)

    def test_legacy_render_analysis_report_includes_disclaimer_and_term_judgment_near_top(self):
        report = render_analysis_report(
            TradeScore("good", 90, "stable", ScoreBreakdown(), REQUESTED_SCENARIOS),
            question="Legacy caller score",
            symbol="NVDA",
        )

        self.assertIn(STANDARD_DISCLAIMER, report)
        self.assertEqual(report.count(STANDARD_DISCLAIMER), 1)
        self.assertLess(report.index(STANDARD_DISCLAIMER), report.index("## **Term-Aware Trade Judgment**"))

    def test_legacy_render_analysis_report_contains_no_action_advice(self):
        report = render_analysis_report(
            TradeScore("good", 90, "stable", ScoreBreakdown(), REQUESTED_SCENARIOS),
            question="you should wait; best action recommend; do not buy",
            symbol="NVDA",
        )

        self.assertFalse(find_forbidden_action_language(report))

    def test_report_does_not_include_action_recommendation_language(self):
        result = AnalysisEngine(self._fresh_provider()).analyze_trade(
            symbol="NVDA",
            question="you should buy, you should sell, you should wait; do not buy; do not sell; do not wait; best action recommend",
            scenarios=REQUESTED_SCENARIOS,
            max_data_age_minutes=15,
        )
        report = write_analysis_report(result)

        forbidden = [
            "best action",
            "preferred action",
            "suggested action",
            "recommended action",
            "decision gate",
            "you should",
            "do not buy",
            "do not sell",
            "do not wait",
            "you should buy",
            "you should sell",
            "you should wait",
            "wait",
            "recommend",
        ]
        for phrase in forbidden:
            self.assertNotIn(phrase, report.lower())
        self.assertFalse(hasattr(result, "trade_verdict"))
        self.assertFalse(hasattr(result, "final_action"))
        self.assertFalse(hasattr(result, "suggested_action"))
        self.assertFalse(hasattr(result, "decision_gate"))

    def test_unconfigured_provider_reports_realtime_unavailable(self):
        result = AnalysisEngine(ManualMarketDataProvider()).analyze_trade(
            symbol="NVDA",
            question="Evaluate this trade",
            scenarios=REQUESTED_SCENARIOS,
            max_data_age_minutes=15,
        )
        report = write_analysis_report(result)

        self.assertIn("## Data Used", report)
        self.assertIn("**Market data status**", report)
        self.assertIn("| Underlying price | missing | missing |", report)
        self.assertIn("- Fallback path used:", report)
        self.assertIn("realtime data unavailable", report)
        self.assertIn("- Underlying latest price: unknown", report)
        self.assertIn("## Missing Data / Confirmation Needed", report)

    def test_provider_price_and_quote_timestamp_render(self):
        timestamp = datetime.now(timezone.utc)
        provider = StubMarketDataProvider(
            QuoteSnapshot(
                symbol="NVDA",
                price=123.45,
                session="regular",
                data_time=timestamp,
                data_quality="high",
                provider_name="stub quote",
                source_type="test",
            )
        )
        result = AnalysisEngine(provider).analyze_trade(
            symbol="NVDA",
            question="Evaluate this trade",
            scenarios=REQUESTED_SCENARIOS,
            max_data_age_minutes=15,
        )
        report = write_analysis_report(result)

        self.assertIn("- Underlying latest price: 123.45", report)
        self.assertIn(f"- Quote timestamp: {timestamp.isoformat()}", report)
        self.assertIn("| Underlying price | found | stub quote |", report)
        self.assertEqual(report.count(STANDARD_DISCLAIMER), 1)

    def test_missing_options_data_is_listed_when_option_context_requested(self):
        timestamp = datetime.now(timezone.utc)
        provider = StubMarketDataProvider(
            QuoteSnapshot(
                symbol="NVDA",
                price=123.45,
                data_time=timestamp,
                data_quality="high",
                provider_name="stub quote",
                source_type="test",
            )
        )
        result = AnalysisEngine(provider).analyze_trade(
            symbol="NVDA",
            question="Evaluate option trade",
            scenarios=REQUESTED_SCENARIOS,
            max_data_age_minutes=15,
            option_expiry="20260501",
            option_strike=200,
            option_type="put",
        )
        report = write_analysis_report(result)

        self.assertIn("option chain for relevant expiry", report)
        self.assertIn("option mark/bid/ask/open interest/volume/IV/delta", report)

    def test_analysis_never_invents_realtime_price(self):
        result = AnalysisEngine(ManualMarketDataProvider()).analyze_trade(
            symbol="NVDA",
            question="Evaluate this trade",
            scenarios=REQUESTED_SCENARIOS,
            max_data_age_minutes=15,
        )
        report = write_analysis_report(result)

        self.assertIsNone(result.market_snapshot.regular_hours_price)
        self.assertIsNone(result.market_snapshot.premarket_price)
        self.assertIsNone(result.market_snapshot.after_hours_price)
        self.assertIsNone(result.market_snapshot.twenty_four_hour_price)
        self.assertIn("- Underlying latest price: unknown", report)

    def test_provider_resolver_prefers_configured_then_manual_or_web(self):
        configured = ManualMarketDataProvider(name="configured")

        configured_resolver = resolve_market_data_provider(configured_provider=configured)
        self.assertIsInstance(configured_resolver, ProviderResolver)
        self.assertEqual(configured_resolver.configured_providers[0], configured)
        self.assertIsInstance(resolve_market_data_provider(allow_web=False), ProviderResolver)
        self.assertIsInstance(resolve_market_data_provider(allow_web=True), ProviderResolver)

    def test_recoverable_probability_sum_095_produces_report(self):
        result = AnalysisEngine(self._fresh_provider()).analyze_trade(
            symbol="NVDA",
            question="Evaluate this trade",
            scenarios=[
                Scenario("base", 0.76, 800),
                Scenario("downside", 0.09, -200),
                Scenario("worst", 0.10, -300),
            ],
            max_data_age_minutes=15,
        )
        report = write_analysis_report(result)

        self.assertIsNotNone(result.expected_value)
        self.assertEqual(result.scenario_validation.probability_sum, 0.95)
        self.assertIn("- Probability sum: 0.9500.", report)
        self.assertIn("normalized to 1.0000", report)

    def test_recoverable_probability_sum_110_produces_report(self):
        result = AnalysisEngine(self._fresh_provider()).analyze_trade(
            symbol="NVDA",
            question="Evaluate this trade",
            scenarios=[
                Scenario("base", 0.80, 800),
                Scenario("downside", 0.20, -200),
                Scenario("worst", 0.10, -300),
            ],
            max_data_age_minutes=15,
        )
        report = write_analysis_report(result)

        self.assertIsNotNone(result.expected_value)
        self.assertAlmostEqual(result.scenario_validation.probability_sum, 1.10)
        self.assertIn("- Probability sum: 1.1000.", report)
        self.assertIn("normalized to 1.0000", report)

    def test_invalid_probability_sum_returns_no_clear_edge_report(self):
        result = AnalysisEngine(self._fresh_provider()).analyze_trade(
            symbol="NVDA",
            question="Evaluate this trade",
            scenarios=[
                Scenario("base", 0.80, 800),
                Scenario("downside", 0.20, -200),
                Scenario("worst", 0.30, -300),
            ],
            max_data_age_minutes=15,
        )
        report = write_analysis_report(result)

        self.assertIsNone(result.expected_value)
        self.assertEqual(result.trade_judgment, "no clear edge")
        self.assertIn("trade_judgment: no clear edge", report)
        self.assertIn("outside recoverable range", report)

    def test_structured_trade_judgment_is_lowercase(self):
        result = AnalysisEngine(self._fresh_provider()).analyze_trade(
            symbol="NVDA",
            question="Evaluate this trade",
            scenarios=REQUESTED_SCENARIOS,
            max_data_age_minutes=15,
        )
        report = write_analysis_report(result)

        self.assertEqual(result.trade_judgment, result.trade_judgment.lower())
        self.assertRegex(report, r"(?m)^trade_judgment: (good|mostly good|neutral|mostly bad|bad|no clear edge)$")
        self.assertNotRegex(report, r"(?m)^trade_judgment: [A-Z ]+$")

    def test_report_title_uses_allowed_trade_judgment_label(self):
        result = AnalysisEngine(self._fresh_provider()).analyze_trade(
            symbol="NVDA",
            question="Evaluate this trade",
            scenarios=REQUESTED_SCENARIOS,
            max_data_age_minutes=15,
        )
        report = write_analysis_report(result)

        self.assertRegex(report.splitlines()[0], rf"^# \*\*({ALLOWED_TITLE_LABELS}) — .+\*\*$")

    def test_term_aware_trade_judgment_appears_near_top(self):
        result = AnalysisEngine(self._fresh_provider()).analyze_trade(
            symbol="NVDA",
            question="Evaluate this trade",
            scenarios=REQUESTED_SCENARIOS,
            max_data_age_minutes=15,
        )
        report = write_analysis_report(result)

        self.assertLess(report.index("## **Term-Aware Trade Judgment**"), report.index("## Why"))
        self.assertIn("| Term | Judgment | Score | Why |", report)

    def test_overall_score_is_not_shown_before_term_aware_judgments(self):
        result = AnalysisEngine(self._fresh_provider()).analyze_trade(
            symbol="NVDA",
            question="Evaluate this trade",
            scenarios=REQUESTED_SCENARIOS,
            max_data_age_minutes=15,
        )
        report = write_analysis_report(result)

        self.assertIn("## **Term-Aware Trade Judgment**", report)
        self.assertLess(
            report.index("## **Term-Aware Trade Judgment**"),
            report.index("- Overall score summary:"),
        )

    def test_ambiguous_trade_uses_no_clear_edge_not_wait(self):
        result = AnalysisEngine(self._fresh_provider()).analyze_trade(
            symbol="NVDA",
            question="Evaluate this trade",
            scenarios=[
                Scenario("base", None, 800),
                Scenario("downside", 0.23, -200),
                Scenario("worst", 0.10, -300),
            ],
            max_data_age_minutes=15,
        )
        report = write_analysis_report(result)

        self.assertTrue(report.splitlines()[0].startswith("# **NO CLEAR EDGE"))
        self.assertIn("trade_judgment: no clear edge", report)
        self.assertNotIn("WAIT", report)
        self.assertNotIn("wait", report.lower())

    def test_missing_scenario_probability_does_not_crash(self):
        result = AnalysisEngine(self._fresh_provider()).analyze_trade(
            symbol="NVDA",
            question="Should I take this trade?",
            scenarios=[
                Scenario("base", None, 800),
                Scenario("downside", 0.23, -200),
                Scenario("worst", 0.10, -300),
            ],
            max_data_age_minutes=15,
        )
        report = write_analysis_report(result)

        self.assertIn("scenario 'base' probability", result.missing_data)
        self.assertIsNone(result.expected_value)
        self.assertEqual(result.trade_score.label, "no clear edge")
        self.assertEqual(result.trade_judgment, "no clear edge")
        self.assertIn("trade_judgment: no clear edge", report)
        self.assertIn("- Confidence: Low", report)

    def test_missing_scenario_profit_loss_does_not_crash(self):
        result = AnalysisEngine(self._fresh_provider()).analyze_trade(
            symbol="NVDA",
            question="Should I take this trade?",
            scenarios=[
                Scenario("base", 0.77, None),
                Scenario("downside", 0.13, -200),
                Scenario("worst", 0.10, -300),
            ],
            max_data_age_minutes=15,
        )
        report = write_analysis_report(result)

        self.assertIn("scenario 'base' profit/loss", result.missing_data)
        self.assertIsNone(result.win_probability)
        self.assertEqual(result.trade_score.label, "no clear edge")
        self.assertEqual(result.trade_judgment, "no clear edge")
        self.assertIn("trade_judgment: no clear edge", report)
        self.assertIn("- Confidence: Low", report)

    def test_incomplete_scenario_data_produces_no_clear_edge_low_confidence(self):
        result = AnalysisEngine(self._fresh_provider()).analyze_trade(
            symbol="NVDA",
            question="Should I take this trade?",
            scenarios=[
                Scenario("base", None, None),
                Scenario("downside", 0.50, -200),
                Scenario("worst", 0.50, -300),
            ],
            max_data_age_minutes=15,
        )
        report = write_analysis_report(result)

        self.assertEqual(result.trade_score.label, "no clear edge")
        self.assertEqual(result.trade_score.stability, "unstable")
        self.assertIsNone(result.expected_value)
        self.assertIn("- Confidence: Low", report)

    def test_generate_honors_supplied_score_breakdown(self):
        report = AnalysisEngine(self._fresh_provider()).generate(
            question="Score this trade",
            symbol="NVDA",
            breakdown=ScoreBreakdown(
                reward_risk=25,
                probability_setup=20,
                position_fit=20,
                market_regime=15,
                options_structure=15,
                psychology_rule_fit=10,
                data_quality_adjustment=0,
            ),
            scenarios=REQUESTED_SCENARIOS,
            capital_required=10000,
        )

        self.assertRegex(report.splitlines()[0], r"^# \*\*GOOD — .+\*\*$")
        self.assertIn("trade_judgment: good", report)

    def test_report_prioritizes_intended_term_in_final_conclusion(self):
        provider = ManualMarketDataProvider(
            snapshot=MarketSnapshot(
                symbol="NVDA",
                source="manual",
                last_updated=datetime.now(timezone.utc).isoformat(),
                regular_hours_price=100,
                data_quality="high",
            )
        )
        result = AnalysisEngine(provider).analyze_trade(
            symbol="NVDA",
            question="Covered call for income?",
            scenarios=REQUESTED_SCENARIOS,
            capital_required=10000,
            position_fit=20,
            market_regime=15,
            options_structure=15,
            psychology_rule_fit=10,
            max_data_age_minutes=15,
            trade_intent=TradeIntent(
                intended_term=TradeTerm.SHORT_TERM,
                primary_goal="income",
                must_preserve_long_term_position="yes",
                willing_to_cap_upside="no",
            ),
            strategy_type="covered call",
        )
        report = write_analysis_report(result)

        self.assertIn("The intended term is Short-term; that term-aware judgment is good with a score of 100.", report)
        self.assertIn("This trade is good for short-term and neutral for long-term.", report)

    def test_chinese_input_report_follows_exact_required_section_order(self):
        result = AnalysisEngine(self._fresh_provider()).analyze_trade(
            symbol="NVDA",
            question="现在买入 NVDA 100 股",
            scenarios=REQUESTED_SCENARIOS,
            position_fit=2,
            market_regime=6,
            options_structure=4,
            psychology_rule_fit=3,
            max_data_age_minutes=15,
            existing_related_exposure=["NVDA 2026-05-01 207.50 short put"],
        )
        report = write_analysis_report(result)
        sections = re.findall(r"^## .+$", report, flags=re.MULTILINE)

        self.assertEqual(sections, REQUIRED_REPORT_SECTIONS)
        self.assertLess(report.index("## **Term-Aware Trade Judgment**"), report.index("## Why"))
        self.assertIn("| Intraday |", report)
        self.assertRegex(report.splitlines()[0], rf"^# \*\*({ALLOWED_TITLE_LABELS}) — .+\*\*$")
        self.assertNotIn("买入", report)
        self.assertNotIn("等待", report)

    def test_mixed_chinese_english_input_report_follows_exact_required_section_order(self):
        result = AnalysisEngine(self._fresh_provider()).analyze_trade(
            symbol="NVDA",
            question="@buy nvda now, 100 stocks；已有 NVDA short put",
            scenarios=REQUESTED_SCENARIOS,
            position_fit=2,
            market_regime=6,
            options_structure=4,
            psychology_rule_fit=3,
            max_data_age_minutes=15,
            existing_related_exposure=["NVDA 2026-05-01 207.50 short put"],
        )
        report = write_analysis_report(result)
        sections = re.findall(r"^## .+$", report, flags=re.MULTILINE)

        self.assertEqual(sections, REQUIRED_REPORT_SECTIONS)
        self.assertLess(report.index("## **Term-Aware Trade Judgment**"), report.index("## Why"))
        self.assertNotIn("## **Summary**", report)

    def test_report_does_not_include_removed_action_fields(self):
        result = AnalysisEngine(self._fresh_provider()).analyze_trade(
            symbol="NVDA",
            question="preferred_action recommended_action best_action final_action decision_gate you should do not buy do not sell do not wait wait",
            scenarios=REQUESTED_SCENARIOS,
            max_data_age_minutes=15,
        )
        report = write_analysis_report(result).lower()

        forbidden = [
            "preferred action",
            "preferred_action",
            "recommended action",
            "recommended_action",
            "best action",
            "best_action",
            "final_action",
            "decision_gate",
            "you should",
            "do not buy",
            "do not sell",
            "do not wait",
            "wait",
        ]
        for phrase in forbidden:
            self.assertNotIn(phrase, report)

    def test_proposed_stock_purchase_with_existing_short_put_includes_concentration_risk(self):
        result = AnalysisEngine(self._fresh_provider()).analyze_trade(
            symbol="NVDA",
            question="@buy nvda now, 100 stocks",
            scenarios=REQUESTED_SCENARIOS,
            position_fit=2,
            market_regime=6,
            options_structure=4,
            psychology_rule_fit=3,
            max_data_age_minutes=15,
            existing_related_exposure=["NVDA 2026-05-01 207.50 short put"],
        )
        report = write_analysis_report(result)

        self.assertEqual(result.order_lines[0].symbol, "NVDA")
        self.assertEqual(result.order_lines[0].instrument, "stock")
        self.assertEqual(result.order_lines[0].quantity, 100)
        self.assertIn("concentration risk", report.lower())
        self.assertIn("short put", report)
        self.assertIn("realtime bid/ask", report)
        self.assertIn("- Trade log updated: no", report)

    def test_proposed_stock_analysis_save_does_not_update_trade_log(self):
        result = AnalysisEngine(self._fresh_provider()).analyze_trade(
            symbol="NVDA",
            question="@buy nvda now, 100 stocks",
            scenarios=REQUESTED_SCENARIOS,
            position_fit=2,
            market_regime=6,
            options_structure=4,
            psychology_rule_fit=3,
            max_data_age_minutes=15,
            existing_related_exposure=["NVDA 2026-05-01 207.50 short put"],
        )
        report = write_analysis_report(result)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            trade_log = root / "trade.md"
            trade_log.write_text("existing trade log\n", encoding="utf-8")
            saved_path = HistoryStore(root / "analysis_history").save("NVDA proposed stock", report, result.created_at)

            self.assertEqual(trade_log.read_text(encoding="utf-8"), "existing trade log\n")
            saved = saved_path.read_text(encoding="utf-8")

        self.assertIn("- Analysis saved: yes", saved)
        self.assertIn("- Trade log updated: no", saved)
        self.assertIn("trade log requires explicit user confirmation", saved)


if __name__ == "__main__":
    unittest.main()
