"""Code-backed local analysis engine."""

from __future__ import annotations

from typing import Iterable, Optional

from tradelens.calculations.scenarios import describe_scenario_missing_data, validate_scenarios
from tradelens.calculations.scoring import build_trade_score, calculate_trade_score
from tradelens.calculations.term_scoring import calculate_term_scores
from tradelens.data.market_data import available_underlying_price, classify_data_quality
from tradelens.data.provider_base import (
    CAP_FEAR_GREED,
    CAP_INDEX_CONTEXT,
    CAP_NEWS,
    CAP_OPTION_CHAIN,
    CAP_OPTION_OPEN_INTEREST,
    CAP_QUOTE,
    CAP_UVIX,
    CAP_VIX,
    MarketDataProvider,
)
from tradelens.data.provider_resolver import ProviderResolver
from tradelens.models import AnalysisResult, Scenario, TradeIntent


def _data_quality_downgrade_reason(snapshot, classified_data_quality: str, max_age_minutes: Optional[int]) -> str:
    if snapshot.data_quality == classified_data_quality:
        return ""
    timestamp = snapshot.quote_timestamp if snapshot.quote_timestamp not in ("unknown", "", None) else snapshot.last_updated
    if available_underlying_price(snapshot) is None:
        return "underlying realtime/latest price is missing"
    if timestamp in ("unknown", "", None) and max_age_minutes is not None:
        return "price timestamp is missing while a freshness limit is required"
    if max_age_minutes is not None:
        return f"market data is older than the configured {max_age_minutes}-minute freshness limit"
    return "provider quality was reclassified by local data checks"


def _lowest_quality(*qualities: str) -> str:
    order = {"high": 3, "medium": 2, "low": 1, "unusable": 0}
    normalized = [quality if quality in order else "low" for quality in qualities]
    return min(normalized, key=lambda quality: order[quality])


def _market_data_missing(
    snapshot,
    option_expiry: Optional[str] = None,
    option_strike: Optional[float] = None,
    option_type: Optional[str] = None,
) -> list[str]:
    missing = list(snapshot.missing_data)
    if available_underlying_price(snapshot) is None:
        missing.append("underlying realtime/latest price")
    if snapshot.quote_timestamp in ("unknown", "", None) and snapshot.last_updated in ("unknown", "", None):
        missing.append("quote timestamp")
    if option_expiry and snapshot.option_chain is None:
        missing.append("option chain for relevant expiry")
    if option_expiry and option_strike is not None and option_type and snapshot.option_quote is None:
        missing.append("option mark/bid/ask/open interest/volume/IV/delta")
    if snapshot.volatility_price is None:
        missing.append("VIX or UVIX volatility context")
    if not snapshot.news_headlines:
        missing.append("newest company news")
    for context_symbol in ("SPY", "QQQ", "SOXX"):
        if snapshot.context_prices.get(context_symbol) is None:
            missing.append(f"{context_symbol} latest context")
    return _ordered_unique(missing)


def _ordered_unique(items: list[str]) -> list[str]:
    seen = set()
    unique = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


def _default_risk_assessment(data_quality: str, missing_data: list[str]) -> list[str]:
    risks = [
        "scenario profit/loss estimates may differ from realized outcomes",
        "options assignment, volatility, and liquidity risks are not fully checked without complete options-chain data",
    ]
    if data_quality != "high":
        risks.append(f"market-data confidence is {data_quality}")
    if missing_data:
        risks.append("missing inputs weaken the scenario profile")
    return risks


def _default_decision_checklist(missing_data: list[str]) -> list[str]:
    checklist = [
        "scenario probabilities and profit/loss estimates are internally consistent",
        "position size fits the user's written exposure limits",
        "assignment, capped-upside, and expiration risks fit the intended term",
    ]
    if missing_data:
        checklist.append("missing data is understood before the user makes their own decision")
    return checklist


class AnalysisEngine:
    """Builds deterministic analysis results from supplied local data."""

    def __init__(
        self,
        market_data_provider: Optional[MarketDataProvider] = None,
        provider_resolver: Optional[ProviderResolver] = None,
    ):
        if provider_resolver is not None:
            self.provider_resolver = provider_resolver
        elif isinstance(market_data_provider, ProviderResolver):
            self.provider_resolver = market_data_provider
        elif market_data_provider is not None:
            self.provider_resolver = ProviderResolver(configured_providers=[market_data_provider])
        else:
            self.provider_resolver = ProviderResolver()

    def analyze_trade(
        self,
        symbol: str,
        question: str,
        scenarios: Iterable[Scenario],
        capital_required: Optional[float] = None,
        position_fit: float = 10,
        market_regime: float = 8,
        options_structure: float = 8,
        psychology_rule_fit: float = 5,
        max_data_age_minutes: Optional[int] = None,
        trade_intent: Optional[TradeIntent] = None,
        strategy_type: str = "unknown",
        option_expiry: Optional[str] = None,
        option_strike: Optional[float] = None,
        option_type: Optional[str] = None,
    ) -> AnalysisResult:
        scenario_list = list(scenarios)
        market_data_bundle = self.provider_resolver.resolve_market_data(
            symbol,
            expiry=option_expiry,
            required_capabilities=[
                CAP_QUOTE,
                CAP_OPTION_CHAIN,
                CAP_OPTION_OPEN_INTEREST,
                CAP_NEWS,
                CAP_VIX,
                CAP_UVIX,
                CAP_FEAR_GREED,
                CAP_INDEX_CONTEXT,
            ],
            strike=option_strike,
            option_type=option_type,
        )
        snapshot = self.provider_resolver.to_market_snapshot(market_data_bundle)
        freshness_quality = classify_data_quality(snapshot, max_age_minutes=max_data_age_minutes)
        classified_data_quality = _lowest_quality(
            market_data_bundle.classified_data_quality,
            freshness_quality,
        )
        data_quality_reason = _data_quality_downgrade_reason(
            snapshot,
            classified_data_quality,
            max_data_age_minutes,
        ) or market_data_bundle.data_quality_reason or ""
        scenario_validation = validate_scenarios(scenario_list)
        timestamp = snapshot.quote_timestamp if snapshot.quote_timestamp not in ("unknown", "", None) else snapshot.last_updated
        has_timestamp = timestamp not in ("unknown", "", None)
        stale_data = has_timestamp and classified_data_quality == "low"
        hard_missing_data = []
        if available_underlying_price(snapshot) is None:
            hard_missing_data.append("underlying realtime/latest price")
        hard_missing_data.extend(describe_scenario_missing_data(scenario_list))
        if scenario_validation.error_message:
            hard_missing_data.append(f"scenario estimate: {scenario_validation.error_message}")
        missing_data = _ordered_unique(market_data_bundle.missing_data + hard_missing_data)
        missing_data.extend(f"scenario estimate: {warning}" for warning in scenario_validation.warnings)
        missing_count = len(hard_missing_data)
        unstable = classified_data_quality == "low" or missing_count > 0 or not scenario_validation.is_valid

        trade_score = calculate_trade_score(
            scenario_list,
            data_quality=classified_data_quality,
            missing_data_count=missing_count,
            capital_required=capital_required,
            position_fit=position_fit,
            market_regime=market_regime,
            options_structure=options_structure,
            psychology_rule_fit=psychology_rule_fit,
            stale_data=stale_data,
            unstable=unstable,
        )
        expected_value = trade_score.expected_value
        win_probability = trade_score.win_probability
        intent = trade_intent or TradeIntent()
        term_scores = calculate_term_scores(
            base_score=trade_score.score,
            intent=intent,
            strategy_type=strategy_type,
            data_is_weak=unstable,
        )
        trade_judgment = "no clear edge" if unstable else trade_score.label
        return AnalysisResult(
            symbol=symbol.upper(),
            question=question,
            market_snapshot=snapshot,
            scenarios=trade_score.scenarios,
            expected_value=expected_value,
            win_probability=win_probability,
            trade_score=trade_score,
            term_scores=term_scores,
            trade_intent=intent,
            trade_judgment=trade_judgment,
            market_data_bundle=market_data_bundle,
            classified_data_quality=classified_data_quality,
            data_quality_downgrade_reason=data_quality_reason,
            scenario_validation=scenario_validation,
            risk_assessment=_default_risk_assessment(classified_data_quality, missing_data),
            decision_checklist=_default_decision_checklist(missing_data),
            invalidation_conditions=[
                "scenario probabilities, scenario profit/loss values, or market data differ materially from the supplied local data",
                "missing data becomes available and changes reward/risk, probability, or position fit",
                "user background rules or position constraints conflict with the trade",
            ],
            what_would_make_this_trade_bad=[
                "expected value turns negative after corrected probabilities or profit/loss inputs",
                "classified data quality remains low for the timeframe being evaluated",
                "the trade conflicts with assignment, upside-capping, or exposure rules",
            ],
            what_would_make_this_trade_better=[
                "fresh market data confirms the underlying price and options context",
                "scenario estimates are complete and probability-weighted edge remains positive",
                "the intended term aligns with the strongest term-aware score",
            ],
            user_decision_notes=[
                "Trade Lens evaluates quality and risk; the user owns any trading choice.",
            ],
            missing_data=missing_data,
            visible_facts=[
                f"symbol supplied: {symbol.upper()}",
                f"market data source: {snapshot.source}",
                f"underlying latest price: {available_underlying_price(snapshot) if available_underlying_price(snapshot) is not None else 'unknown'}",
                f"market session: {snapshot.session}",
                f"quote timestamp: {timestamp}",
            ],
            user_claims=[f"user question: {question}"],
            ai_inferences=[f"data quality classified as {classified_data_quality}"],
            assumptions=[
                "position fit, market regime, options structure, and psychology scores use supplied arguments or local defaults"
            ],
        )

    # Backward-compatible helper from the first skeleton.
    def generate(
        self,
        question,
        symbol,
        breakdown,
        scenarios,
        capital_required=None,
        unstable=False,
        option_expiry: Optional[str] = None,
        option_strike: Optional[float] = None,
        option_type: Optional[str] = None,
    ):
        from tradelens.analysis.report_writer import write_analysis_report

        scenario_list = list(scenarios)
        market_data_bundle = self.provider_resolver.resolve_market_data(
            symbol,
            expiry=option_expiry,
            required_capabilities=[
                CAP_QUOTE,
                CAP_OPTION_CHAIN,
                CAP_OPTION_OPEN_INTEREST,
                CAP_NEWS,
                CAP_VIX,
                CAP_UVIX,
                CAP_FEAR_GREED,
                CAP_INDEX_CONTEXT,
            ],
            strike=option_strike,
            option_type=option_type,
        )
        snapshot = self.provider_resolver.to_market_snapshot(market_data_bundle)
        classified_data_quality = _lowest_quality(market_data_bundle.classified_data_quality, classify_data_quality(snapshot))
        data_quality_reason = _data_quality_downgrade_reason(snapshot, classified_data_quality, None) or market_data_bundle.data_quality_reason or ""
        scenario_validation = validate_scenarios(scenario_list)
        hard_missing_data = []
        if available_underlying_price(snapshot) is None:
            hard_missing_data.append("underlying realtime/latest price")
        hard_missing_data.extend(describe_scenario_missing_data(scenario_list))
        if scenario_validation.error_message:
            hard_missing_data.append(f"scenario estimate: {scenario_validation.error_message}")
        missing_data = _ordered_unique(market_data_bundle.missing_data + hard_missing_data)
        missing_data.extend(f"scenario estimate: {warning}" for warning in scenario_validation.warnings)
        trade_score = build_trade_score(
            breakdown=breakdown,
            scenarios=scenario_list,
            capital_required=capital_required,
            unstable=unstable,
        )
        intent = TradeIntent()
        data_is_weak = (
            unstable
            or trade_score.stability == "unstable"
            or bool(hard_missing_data)
            or classified_data_quality == "low"
        )
        term_scores = calculate_term_scores(
            base_score=trade_score.score,
            intent=intent,
            data_is_weak=data_is_weak,
        )
        result = AnalysisResult(
            symbol=symbol.upper(),
            question=question,
            market_snapshot=snapshot,
            scenarios=trade_score.scenarios,
            expected_value=trade_score.expected_value,
            win_probability=trade_score.win_probability,
            trade_score=trade_score,
            term_scores=term_scores,
            trade_intent=intent,
            trade_judgment="no clear edge" if data_is_weak else trade_score.label,
            market_data_bundle=market_data_bundle,
            classified_data_quality=classified_data_quality,
            data_quality_downgrade_reason=data_quality_reason,
            scenario_validation=scenario_validation,
            risk_assessment=_default_risk_assessment(classified_data_quality, missing_data),
            decision_checklist=_default_decision_checklist(missing_data),
            invalidation_conditions=[
                "scenario probabilities, scenario profit/loss values, or market data differ materially from the supplied local data",
                "missing data becomes available and changes reward/risk, probability, or position fit",
                "user background rules or position constraints conflict with the trade",
            ],
            what_would_make_this_trade_bad=[
                "expected value turns negative after corrected probabilities or profit/loss inputs",
                "classified data quality remains low for the timeframe being evaluated",
                "the trade conflicts with assignment, upside-capping, or exposure rules",
            ],
            what_would_make_this_trade_better=[
                "fresh market data confirms the underlying price and options context",
                "scenario estimates are complete and probability-weighted edge remains positive",
                "the intended term aligns with the strongest term-aware score",
            ],
            user_decision_notes=[
                "Trade Lens evaluates quality and risk; the user owns any trading choice.",
            ],
            missing_data=missing_data,
            visible_facts=[
                f"symbol supplied: {symbol.upper()}",
                f"market data source: {snapshot.source}",
                f"underlying latest price: {available_underlying_price(snapshot) if available_underlying_price(snapshot) is not None else 'unknown'}",
            ],
            user_claims=[f"user question: {question}"],
            ai_inferences=[f"data quality classified as {classified_data_quality}"],
            assumptions=[
                "the supplied score breakdown is treated as already reviewed local input"
            ],
        )
        return write_analysis_report(result)
