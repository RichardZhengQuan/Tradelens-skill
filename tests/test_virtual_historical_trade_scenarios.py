import sys
import unittest
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tradelens.analysis.engine import AnalysisEngine
from tradelens.analysis.report_contract import (
    DISCLAIMER,
    find_forbidden_action_language,
    validate_report_contract,
)
from tradelens.analysis.report_writer import write_analysis_report
from tradelens.data.market_snapshot import (
    OptionChainSnapshot,
    OptionContractSnapshot,
    ProviderStatus,
    QuoteSnapshot,
)
from tradelens.data.provider_base import CAP_OPTION_CHAIN, CAP_QUOTE, MarketDataProvider
from tradelens.models import Scenario, TradeIntent, TradeTerm


class VirtualHistoricalProvider(MarketDataProvider):
    name = "VirtualHistoricalProvider"

    def __init__(
        self,
        *,
        as_of: datetime,
        price: Optional[float],
        option: Optional[OptionContractSnapshot] = None,
        note: str = "virtual historical fixture",
    ):
        self.as_of = as_of
        self.price = price
        self.option = option
        self.note = note

    def capabilities(self):
        return {CAP_QUOTE, CAP_OPTION_CHAIN}

    def get_quote(self, symbol):
        if self.price is None:
            return None, ProviderStatus(
                provider_name=self.name,
                capability=CAP_QUOTE,
                available=False,
                status="missing",
                error="virtual historical quote missing",
                fetched_at=self.as_of,
                data_time=self.as_of,
                data_quality="low",
                missing_fields=["underlying realtime/latest price", "quote timestamp"],
                notes=[self.note],
            )
        quote = QuoteSnapshot(
            symbol=symbol.upper(),
            price=self.price,
            session="regular",
            provider_name=self.name,
            source_type="virtual_historical_fixture",
            fetched_at=self.as_of,
            data_time=self.as_of,
            is_realtime=False,
            is_delayed=False,
            data_quality="high",
        )
        return quote, ProviderStatus(
            provider_name=self.name,
            capability=CAP_QUOTE,
            available=True,
            status="found",
            fetched_at=self.as_of,
            data_time=self.as_of,
            is_realtime=False,
            is_delayed=False,
            data_quality="high",
            notes=[self.note],
        )

    def get_option_chain(self, symbol, expiry=None):
        if self.option is None:
            return None, ProviderStatus(
                provider_name=self.name,
                capability=CAP_OPTION_CHAIN,
                available=False,
                status="missing",
                error="virtual historical option chain missing",
                fetched_at=self.as_of,
                data_time=self.as_of,
                data_quality="low",
                missing_fields=["option chain for relevant expiry"],
                notes=[self.note],
            )
        chain = OptionChainSnapshot(
            underlying_symbol=symbol.upper(),
            expiry=expiry or self.option.expiry,
            contracts=[self.option],
            provider_name=self.name,
            source_type="virtual_historical_fixture",
            fetched_at=self.as_of,
            data_time=self.as_of,
            is_realtime=False,
            is_delayed=False,
            data_quality="high",
        )
        return chain, ProviderStatus(
            provider_name=self.name,
            capability=CAP_OPTION_CHAIN,
            available=True,
            status="found",
            fetched_at=self.as_of,
            data_time=self.as_of,
            is_realtime=False,
            is_delayed=False,
            data_quality="high",
            notes=[self.note],
        )


@dataclass(frozen=True)
class HistoricalOutcomeCase:
    case_id: str
    symbol: str
    strategy_type: str
    question: str
    as_of: datetime
    price: float
    expiry: str
    strike: float
    option_type: str
    option_mark: float
    option_iv: float
    option_delta: float
    scenarios: tuple[Scenario, ...]
    capital_required: float
    position_fit: float
    market_regime: float
    options_structure: float
    psychology_rule_fit: float
    trade_intent: TradeIntent
    expected_judgment: str
    expected_score_range: tuple[float, float]
    later_outcome: str
    benchmark_status: str
    expected_report_snippets: tuple[str, ...] = field(default_factory=tuple)
    volume: int = 10000
    open_interest: int = 25000


def _dt(year: int, month: int, day: int) -> datetime:
    return datetime(year, month, day, 20, 0, tzinfo=timezone.utc)


def _option(case: HistoricalOutcomeCase) -> OptionContractSnapshot:
    suffix = f"{case.as_of:%y%m%d}{case.option_type[:1].upper()}{int(case.strike * 1000):08d}"
    return OptionContractSnapshot(
        symbol=f"{case.symbol}{suffix}",
        underlying_symbol=case.symbol,
        option_type=case.option_type,
        strike=case.strike,
        expiry=case.expiry,
        bid=round(case.option_mark * 0.96, 2),
        ask=round(case.option_mark * 1.04, 2),
        mark=case.option_mark,
        volume=case.volume,
        open_interest=case.open_interest,
        iv=case.option_iv,
        delta=case.option_delta,
        provider_name="VirtualHistoricalProvider",
        source_type="historical_outcome_fixture",
        fetched_at=case.as_of,
        data_time=case.as_of,
        data_quality="high",
    )


BENCHMARK_CASES = (
    HistoricalOutcomeCase(
        case_id="NVDA-2024-covered-call",
        symbol="NVDA",
        strategy_type="covered call",
        question="Evaluate historical NVDA covered call income setup",
        as_of=_dt(2024, 6, 21),
        price=130.00,
        expiry="2024-06-28",
        strike=135,
        option_type="call",
        option_mark=1.90,
        option_iv=0.55,
        option_delta=0.32,
        scenarios=(
            Scenario("base", 0.75, 260, "scenario", "historical benchmark estimate"),
            Scenario("downside", 0.18, -220, "scenario", "historical benchmark estimate"),
            Scenario("worst", 0.07, -1100, "scenario", "historical benchmark estimate"),
        ),
        capital_required=13000,
        position_fit=20,
        market_regime=15,
        options_structure=15,
        psychology_rule_fit=10,
        trade_intent=TradeIntent(
            intended_term=TradeTerm.SHORT_TERM,
            primary_goal="income",
            must_preserve_long_term_position="yes",
            willing_to_cap_upside="no",
        ),
        expected_judgment="mostly good",
        expected_score_range=(77, 80),
        later_outcome="short-term premium capture was reasonable; long-term upside-capping risk still mattered later in 2024",
        benchmark_status="pass",
        expected_report_snippets=(
            "| Short-term (intended) | GOOD |",
            "| Long-term | MOSTLY BAD |",
            "main risk: may cap long-term upside",
        ),
        volume=12000,
        open_interest=43000,
    ),
    HistoricalOutcomeCase(
        case_id="AMD-2023-LEAPS",
        symbol="AMD",
        strategy_type="LEAPS long call",
        question="Evaluate historical AMD LEAPS setup after 2023 semiconductor pullback",
        as_of=_dt(2023, 10, 31),
        price=98.50,
        expiry="2025-01-17",
        strike=120,
        option_type="call",
        option_mark=18.40,
        option_iv=0.48,
        option_delta=0.58,
        scenarios=(
            Scenario("base", 0.68, 1800, "scenario", "historical benchmark estimate"),
            Scenario("downside", 0.22, -800, "scenario", "historical benchmark estimate"),
            Scenario("worst", 0.10, -2500, "scenario", "historical benchmark estimate"),
        ),
        capital_required=1840,
        position_fit=18,
        market_regime=14,
        options_structure=14,
        psychology_rule_fit=8,
        trade_intent=TradeIntent(intended_term=TradeTerm.LONG_TERM, primary_goal="long-term directional exposure"),
        expected_judgment="mostly good",
        expected_score_range=(72, 75),
        later_outcome="AMD later rallied with the 2024 AI semiconductor cycle, supporting the long-term directional thesis",
        benchmark_status="pass",
        expected_report_snippets=(
            "| Long-term (intended) | GOOD |",
            "LEAPS structure can fit a longer-term directional thesis",
        ),
    ),
    HistoricalOutcomeCase(
        case_id="INTC-2024-PMCC",
        symbol="INTC",
        strategy_type="PMCC",
        question="Evaluate historical INTC PMCC-style setup before 2024 downside break",
        as_of=_dt(2024, 7, 26),
        price=31.00,
        expiry="2025-01-17",
        strike=35,
        option_type="call",
        option_mark=3.20,
        option_iv=0.42,
        option_delta=0.45,
        scenarios=(
            Scenario("base", 0.42, 120, "scenario", "historical benchmark estimate"),
            Scenario("downside", 0.38, -500, "scenario", "historical benchmark estimate"),
            Scenario("worst", 0.20, -1100, "scenario", "historical benchmark estimate"),
        ),
        capital_required=320,
        position_fit=5,
        market_regime=3,
        options_structure=5,
        psychology_rule_fit=4,
        trade_intent=TradeIntent(
            intended_term=TradeTerm.MEDIUM_TERM,
            primary_goal="leveraged recovery exposure",
            must_preserve_long_term_position="yes",
            willing_to_cap_upside="no",
        ),
        expected_judgment="bad",
        expected_score_range=(21, 24),
        later_outcome="INTC later broke lower after 2024 disappointment, matching the weak setup judgment",
        benchmark_status="pass",
        expected_report_snippets=("main risk: may cap upside beyond the immediate income window",),
        volume=8000,
        open_interest=18000,
    ),
    HistoricalOutcomeCase(
        case_id="TSLA-2022-CSP",
        symbol="TSLA",
        strategy_type="cash-secured put",
        question="Evaluate historical TSLA cash-secured put risk setup",
        as_of=_dt(2022, 10, 14),
        price=90.00,
        expiry="2022-10-21",
        strike=85,
        option_type="put",
        option_mark=2.50,
        option_iv=0.82,
        option_delta=-0.28,
        scenarios=(
            Scenario("base", 0.70, 250, "scenario", "historical benchmark estimate"),
            Scenario("downside", 0.20, -600, "scenario", "historical benchmark estimate"),
            Scenario("worst", 0.10, -2500, "scenario", "historical benchmark estimate"),
        ),
        capital_required=8500,
        position_fit=10,
        market_regime=5,
        options_structure=8,
        psychology_rule_fit=4,
        trade_intent=TradeIntent(
            intended_term=TradeTerm.MEDIUM_TERM,
            primary_goal="premium income",
            willing_to_accept_assignment="no",
        ),
        expected_judgment="mostly bad",
        expected_score_range=(35, 38),
        later_outcome="TSLA weakness and volatility persisted, so assignment conflict and downside risk dominated",
        benchmark_status="pass",
        expected_report_snippets=(
            "| Medium-term (intended) | BAD |",
            "main risk: assignment does not fit stated intent",
        ),
        volume=18000,
        open_interest=52000,
    ),
    HistoricalOutcomeCase(
        case_id="GME-2021-strangle",
        symbol="GME",
        strategy_type="strangle",
        question="Evaluate historical GME short-volatility strangle setup during meme volatility",
        as_of=_dt(2021, 1, 29),
        price=325.00,
        expiry="2021-02-05",
        strike=500,
        option_type="call",
        option_mark=45.00,
        option_iv=6.50,
        option_delta=0.22,
        scenarios=(
            Scenario("base", 0.35, 600, "scenario", "historical benchmark estimate"),
            Scenario("downside", 0.30, -1400, "scenario", "historical benchmark estimate"),
            Scenario("worst", 0.35, -4500, "scenario", "historical benchmark estimate"),
        ),
        capital_required=12000,
        position_fit=3,
        market_regime=2,
        options_structure=3,
        psychology_rule_fit=2,
        trade_intent=TradeIntent(intended_term=TradeTerm.SHORT_TERM, primary_goal="short volatility"),
        expected_judgment="bad",
        expected_score_range=(13, 16),
        later_outcome="later path remained disorderly enough that undefined short volatility was directionally poor",
        benchmark_status="pass",
        expected_report_snippets=(
            "short volatility can benefit from near-term decay",
            "short volatility may be too compressed for intraday risk",
        ),
        volume=90000,
        open_interest=60000,
    ),
    HistoricalOutcomeCase(
        case_id="NVDA-2023-CSP",
        symbol="NVDA",
        strategy_type="cash-secured put",
        question="Evaluate historical NVDA cash-secured put setup during 2023 AI trend",
        as_of=_dt(2023, 5, 26),
        price=38.90,
        expiry="2023-06-16",
        strike=35,
        option_type="put",
        option_mark=1.05,
        option_iv=0.62,
        option_delta=-0.24,
        scenarios=(
            Scenario("base", 0.78, 450, "scenario", "historical benchmark estimate"),
            Scenario("downside", 0.17, -600, "scenario", "historical benchmark estimate"),
            Scenario("worst", 0.05, -1800, "scenario", "historical benchmark estimate"),
        ),
        capital_required=3500,
        position_fit=18,
        market_regime=13,
        options_structure=13,
        psychology_rule_fit=8,
        trade_intent=TradeIntent(
            intended_term=TradeTerm.MEDIUM_TERM,
            primary_goal="accumulation income",
            willing_to_accept_assignment="yes",
        ),
        expected_judgment="mostly good",
        expected_score_range=(69, 72),
        later_outcome="NVDA continued higher in the AI trend, making assignment-acceptable CSP exposure directionally reasonable",
        benchmark_status="pass",
        expected_report_snippets=(
            "| Medium-term (intended) | MOSTLY GOOD |",
            "assignment can fit a longer-term accumulation plan",
        ),
        volume=25000,
        open_interest=70000,
    ),
    HistoricalOutcomeCase(
        case_id="AMD-2022-strangle",
        symbol="AMD",
        strategy_type="strangle",
        question="Evaluate historical AMD short-volatility strangle setup in 2022 drawdown",
        as_of=_dt(2022, 5, 4),
        price=95.00,
        expiry="2022-05-20",
        strike=110,
        option_type="call",
        option_mark=3.10,
        option_iv=0.75,
        option_delta=0.25,
        scenarios=(
            Scenario("base", 0.45, 280, "scenario", "historical benchmark estimate"),
            Scenario("downside", 0.35, -900, "scenario", "historical benchmark estimate"),
            Scenario("worst", 0.20, -2400, "scenario", "historical benchmark estimate"),
        ),
        capital_required=6500,
        position_fit=8,
        market_regime=5,
        options_structure=6,
        psychology_rule_fit=5,
        trade_intent=TradeIntent(intended_term=TradeTerm.SHORT_TERM, primary_goal="short volatility"),
        expected_judgment="mostly bad",
        expected_score_range=(28, 31),
        later_outcome="AMD remained vulnerable during the 2022 semiconductor drawdown, making undefined short volatility weak",
        benchmark_status="pass",
        expected_report_snippets=(
            "| Short-term (intended) | MOSTLY BAD |",
            "short volatility can benefit from near-term decay",
        ),
        volume=14000,
        open_interest=38000,
    ),
    HistoricalOutcomeCase(
        case_id="GME-2021-LEAPS",
        symbol="GME",
        strategy_type="LEAPS long call",
        question="Evaluate historical GME LEAPS setup after meme squeeze",
        as_of=_dt(2021, 6, 8),
        price=300.00,
        expiry="2023-01-20",
        strike=400,
        option_type="call",
        option_mark=120.00,
        option_iv=2.10,
        option_delta=0.46,
        scenarios=(
            Scenario("base", 0.30, 1500, "scenario", "historical benchmark estimate"),
            Scenario("downside", 0.40, -2500, "scenario", "historical benchmark estimate"),
            Scenario("worst", 0.30, -8000, "scenario", "historical benchmark estimate"),
        ),
        capital_required=12000,
        position_fit=2,
        market_regime=2,
        options_structure=2,
        psychology_rule_fit=2,
        trade_intent=TradeIntent(intended_term=TradeTerm.LONG_TERM, primary_goal="long-term directional exposure"),
        expected_judgment="bad",
        expected_score_range=(10, 13),
        later_outcome="later GME price action did not justify the expensive long-dated call profile",
        benchmark_status="pass",
        expected_report_snippets=(
            "| Long-term (intended) | BAD |",
            "LEAPS structure can fit a longer-term directional thesis",
        ),
        volume=20000,
        open_interest=42000,
    ),
)


REQUIRED_SYMBOLS = {"NVDA", "AMD", "INTC", "TSLA", "GME"}
REQUIRED_STRATEGY_TERMS = ("strangle", "cash-secured put", "covered call", "leaps", "pmcc")


def _run_benchmark_case(case: HistoricalOutcomeCase):
    provider_note = f"{case.case_id}; later outcome: {case.later_outcome}"
    result = AnalysisEngine(
        VirtualHistoricalProvider(as_of=case.as_of, price=case.price, option=_option(case), note=provider_note)
    ).analyze_trade(
        symbol=case.symbol,
        question=case.question,
        scenarios=case.scenarios,
        capital_required=case.capital_required,
        position_fit=case.position_fit,
        market_regime=case.market_regime,
        options_structure=case.options_structure,
        psychology_rule_fit=case.psychology_rule_fit,
        trade_intent=case.trade_intent,
        strategy_type=case.strategy_type,
        option_expiry=case.expiry,
        option_strike=case.strike,
        option_type=case.option_type,
    )
    return result, write_analysis_report(result)


def _term_signature(result):
    return [
        (
            score.term.value,
            score.label,
            round(score.score, 4),
            score.reason,
            score.main_risk,
            score.is_intended_term,
        )
        for score in result.term_scores
    ]


def _directionally_reasonable(case: HistoricalOutcomeCase, judgment: str) -> bool:
    if case.benchmark_status == "pass":
        return judgment == case.expected_judgment
    if case.benchmark_status == "ambiguous":
        return judgment in {"neutral", "no clear edge"}
    return False


class VirtualHistoricalTradeScenarioTest(unittest.TestCase):
    def assertJudgmentFirstSourceAttributedAndSafe(self, report: str):
        validate_report_contract(report)
        self.assertFalse(find_forbidden_action_language(report))
        self.assertTrue(report.splitlines()[0].startswith("# **"))
        self.assertEqual(report.count(DISCLAIMER), 1)
        self.assertLess(report.index(DISCLAIMER), report.index("## **Term-Aware Trade Judgment**"))
        self.assertLess(report.index("## **Term-Aware Trade Judgment**"), report.index("## Why"))
        self.assertNotRegex(report[: report.index("## **Term-Aware Trade Judgment**")], r"(?i)trade score|overall score")
        self.assertIn("**Market data status**", report)
        self.assertIn("**Provider attempts**", report)
        self.assertIn("VirtualHistoricalProvider", report)

    def test_historical_outcome_benchmark_matrix_covers_required_cases(self):
        self.assertGreaterEqual(len(BENCHMARK_CASES), 8)
        self.assertTrue(REQUIRED_SYMBOLS.issubset({case.symbol for case in BENCHMARK_CASES}))
        strategy_text = " ".join(case.strategy_type.lower() for case in BENCHMARK_CASES)
        for term in REQUIRED_STRATEGY_TERMS:
            self.assertIn(term, strategy_text)
        counts = {status: sum(1 for case in BENCHMARK_CASES if case.benchmark_status == status) for status in ("pass", "ambiguous", "fail")}
        self.assertEqual(counts, {"pass": 8, "ambiguous": 0, "fail": 0})

    def test_historical_outcome_benchmark_is_stable_and_directionally_reasonable(self):
        for case in BENCHMARK_CASES:
            with self.subTest(case=case.case_id):
                first_result, first_report = _run_benchmark_case(case)
                second_result, second_report = _run_benchmark_case(case)

                self.assertEqual(first_result.trade_judgment, case.expected_judgment)
                self.assertEqual(second_result.trade_judgment, case.expected_judgment)
                self.assertEqual(round(first_result.trade_score.score, 4), round(second_result.trade_score.score, 4))
                self.assertGreaterEqual(first_result.trade_score.score, case.expected_score_range[0])
                self.assertLessEqual(first_result.trade_score.score, case.expected_score_range[1])
                self.assertEqual(_term_signature(first_result), _term_signature(second_result))
                self.assertTrue(_directionally_reasonable(case, first_result.trade_judgment), case.later_outcome)

                for snippet in case.expected_report_snippets:
                    self.assertIn(snippet, first_report)
                    self.assertIn(snippet, second_report)

                self.assertIn(case.case_id, first_report)
                self.assertIn("later outcome:", first_report)
                self.assertIn("| Underlying price | found | VirtualHistoricalProvider |", first_report)
                self.assertIn("realtime=no; delayed=no", first_report)
                self.assertJudgmentFirstSourceAttributedAndSafe(first_report)

    def test_historical_covered_call_is_short_term_good_but_long_term_weak(self):
        as_of = datetime(2024, 6, 21, 20, 0, tzinfo=timezone.utc)
        option = OptionContractSnapshot(
            symbol="NVDA240628C00135000",
            underlying_symbol="NVDA",
            option_type="call",
            strike=135,
            expiry="2024-06-28",
            bid=1.80,
            ask=2.00,
            mark=1.90,
            volume=12000,
            open_interest=43000,
            iv=0.55,
            delta=0.32,
            provider_name="VirtualHistoricalProvider",
            source_type="virtual_historical_fixture",
            fetched_at=as_of,
            data_time=as_of,
            data_quality="high",
        )

        result = AnalysisEngine(
            VirtualHistoricalProvider(as_of=as_of, price=130.00, option=option, note="NVDA post-split weekly covered-call fixture")
        ).analyze_trade(
            symbol="NVDA",
            question="Evaluate historical NVDA covered call income setup",
            scenarios=[
                Scenario("base", 0.75, 260, "scenario", "virtual historical scenario estimate"),
                Scenario("downside", 0.18, -220, "scenario", "virtual historical scenario estimate"),
                Scenario("worst", 0.07, -1100, "scenario", "virtual historical scenario estimate"),
            ],
            capital_required=13000,
            position_fit=20,
            market_regime=15,
            options_structure=15,
            psychology_rule_fit=10,
            trade_intent=TradeIntent(
                intended_term=TradeTerm.SHORT_TERM,
                primary_goal="income",
                must_preserve_long_term_position="yes",
                willing_to_cap_upside="no",
            ),
            strategy_type="covered call",
            option_expiry="2024-06-28",
            option_strike=135,
            option_type="call",
        )
        report = write_analysis_report(result)

        self.assertEqual(result.trade_judgment, "mostly good")
        self.assertAlmostEqual(result.expected_value, 78.4)
        self.assertIn("| Short-term (intended) | GOOD |", report)
        self.assertIn("| Long-term | MOSTLY BAD |", report)
        self.assertIn("main risk: may cap long-term upside", report)
        self.assertIn("| Underlying price | found | VirtualHistoricalProvider |", report)
        self.assertIn("| Option chain | found | VirtualHistoricalProvider |", report)
        self.assertIn("realtime=no; delayed=no", report)
        self.assertJudgmentFirstSourceAttributedAndSafe(report)

    def test_historical_cash_secured_put_surfaces_assignment_intent_conflict(self):
        as_of = datetime(2022, 10, 14, 20, 0, tzinfo=timezone.utc)
        option = OptionContractSnapshot(
            symbol="TSLA221021P00085000",
            underlying_symbol="TSLA",
            option_type="put",
            strike=85,
            expiry="2022-10-21",
            bid=2.35,
            ask=2.65,
            mark=2.50,
            volume=18000,
            open_interest=52000,
            iv=0.82,
            delta=-0.28,
            provider_name="VirtualHistoricalProvider",
            source_type="virtual_historical_fixture",
            fetched_at=as_of,
            data_time=as_of,
            data_quality="high",
        )

        result = AnalysisEngine(
            VirtualHistoricalProvider(as_of=as_of, price=90.00, option=option, note="TSLA 2022 drawdown CSP fixture")
        ).analyze_trade(
            symbol="TSLA",
            question="Evaluate historical TSLA cash-secured put risk setup",
            scenarios=[
                Scenario("base", 0.70, 250, "scenario", "virtual historical scenario estimate"),
                Scenario("downside", 0.20, -600, "scenario", "virtual historical scenario estimate"),
                Scenario("worst", 0.10, -2500, "scenario", "virtual historical scenario estimate"),
            ],
            capital_required=8500,
            position_fit=10,
            market_regime=5,
            options_structure=8,
            psychology_rule_fit=4,
            trade_intent=TradeIntent(
                intended_term=TradeTerm.MEDIUM_TERM,
                primary_goal="premium income",
                willing_to_accept_assignment="no",
            ),
            strategy_type="cash-secured put",
            option_expiry="2022-10-21",
            option_strike=85,
            option_type="put",
        )
        report = write_analysis_report(result)

        self.assertEqual(result.trade_judgment, "mostly bad")
        self.assertAlmostEqual(result.expected_value, -195.0)
        self.assertIn("| Medium-term (intended) | BAD |", report)
        self.assertIn("main risk: assignment does not fit stated intent", report)
        self.assertIn("- Expected value: -$195.00.", report)
        self.assertJudgmentFirstSourceAttributedAndSafe(report)

    def test_historical_trade_with_missing_quote_forces_no_clear_edge_without_fake_price(self):
        as_of = datetime(2021, 1, 29, 20, 0, tzinfo=timezone.utc)

        result = AnalysisEngine(
            VirtualHistoricalProvider(as_of=as_of, price=None, option=None, note="missing quote historical fixture")
        ).analyze_trade(
            symbol="GME",
            question="Evaluate historical GME option setup with incomplete fixture data",
            scenarios=[
                Scenario("base", 0.50, 400, "scenario", "virtual historical scenario estimate"),
                Scenario("downside", 0.30, -700, "scenario", "virtual historical scenario estimate"),
                Scenario("worst", 0.20, -2200, "scenario", "virtual historical scenario estimate"),
            ],
            capital_required=5000,
            strategy_type="long call",
            option_expiry="2021-02-05",
            option_strike=80,
            option_type="call",
        )
        report = write_analysis_report(result)

        self.assertEqual(result.trade_judgment, "no clear edge")
        self.assertIsNone(result.market_snapshot.regular_hours_price)
        self.assertTrue(report.splitlines()[0].startswith("# **NO CLEAR EDGE"))
        self.assertIn("underlying realtime/latest price", report)
        self.assertIn("option chain for relevant expiry", report)
        self.assertIn("- Underlying latest price: unknown", report)
        self.assertIn("| quote | VirtualHistoricalProvider | missing | virtual historical quote missing |", report)
        self.assertJudgmentFirstSourceAttributedAndSafe(report)


if __name__ == "__main__":
    unittest.main()
