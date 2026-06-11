"""Code-backed local analysis engine."""

from __future__ import annotations

import re
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
    CAP_OPTION_GREEKS,
    CAP_OPTION_IV,
    CAP_OPTION_OPEN_INTEREST,
    CAP_QUOTE,
    CAP_UVIX,
    CAP_VIX,
    MarketDataProvider,
)
from tradelens.data.capability_planner import build_capability_plan
from tradelens.data.provider_resolver import ProviderResolver
from tradelens.models import AnalysisResult, OrderLine, Scenario, TradeIntent
from tradelens.parsers.text_parser import parse_order_lines


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


def _meaningful_order_lines(order_lines: list[OrderLine]) -> list[OrderLine]:
    return [
        order
        for order in order_lines
        if order.action != "unknown"
        or order.quantity is not None
        or order.instrument != "unknown"
        or order.symbol != "unknown"
    ]


def _is_stock_proposal(order: OrderLine, symbol: str) -> bool:
    return order.instrument == "stock" and order.symbol.upper() == symbol.upper()


def _proposed_stock_missing_data(order_lines: list[OrderLine], symbol: str) -> list[str]:
    if not any(_is_stock_proposal(order, symbol) for order in order_lines):
        return []
    return [
        "realtime bid/ask",
        "order type",
        "entry price",
        "trade intent",
        "account percentage",
        "cash usage",
    ]


def _stock_proposal_context(
    order_lines: list[OrderLine],
    symbol: str,
    existing_related_exposure: list[str],
) -> tuple[list[str], list[str], list[str], list[str]]:
    stock_orders = [order for order in order_lines if _is_stock_proposal(order, symbol)]
    if not stock_orders:
        return [], [], [], []
    quantity_text = ", ".join(
        f"{order.quantity:g} share stock proposal" if order.quantity is not None else "stock proposal"
        for order in stock_orders
    )
    facts = [
        f"parsed proposed stock order for {symbol.upper()}: {quantity_text}",
        "order type: unknown",
        "entry price: unknown",
        "intent: unknown",
    ]
    inferences = [
        "proposed stock order requires concentration, cash usage, account percentage, and term-fit checks",
    ]
    risks = [
        "concentration risk: proposed stock exposure may increase single-symbol exposure",
        "cash usage and account percentage are not confirmed",
    ]
    if existing_related_exposure:
        joined = "; ".join(existing_related_exposure)
        facts.append(f"existing related exposure: {joined}")
        risks.append(f"concentration risk: proposed stock exposure overlaps with existing related exposure ({joined})")
        inferences.append("existing related exposure can weaken position fit for the same symbol")
    assumptions = [
        "proposed stock text is analysis-only unless the user confirms it as an executed or planned trade to journal",
    ]
    return facts, inferences, risks, assumptions


def _has_option_order(order: OrderLine) -> bool:
    return order.instrument == "option" or order.option_type in {"call", "put", "c", "p"}


def _has_option_proposal_context(order_lines: list[OrderLine], question: str, has_option_context: bool) -> bool:
    if has_option_context or any(_has_option_order(order) for order in order_lines):
        return True
    return bool(re.search(r"(?i)\b(put|call)\b|期权", question or ""))


def _duplicate_option_exposure_context(
    symbol: str,
    question: str,
    option_strike: Optional[float],
    option_type: Optional[str],
    related_exposure: list[str],
) -> tuple[list[str], list[str], list[str], list[str], list[str]]:
    if not related_exposure:
        return [], [], [], [], []
    joined = "; ".join(related_exposure)
    contract_text = f"{option_strike:g}{(option_type or '').upper()}" if option_strike is not None else "option contract"
    facts = [
        f"existing related exposure: {joined}",
        f"possible duplicate {symbol.upper()} {contract_text} exposure requires confirmation",
    ]
    inferences = [
        "the proposed option may be a new second contract or may refer to the existing related position",
        "duplicate short-option exposure would weaken position fit and assignment-risk profile",
    ]
    risks = [
        f"duplicate exposure risk: related {symbol.upper()} option exposure is already present",
        "assignment exposure may be larger than the draft trade text implies",
    ]
    assumptions = [
        "the option proposal remains analysis-only until the user confirms whether it is new, existing, or already planned to journal",
    ]
    missing = [
        "confirmation whether this is a new second contract or the existing option position",
        "option premium",
        "assignment plan",
    ]
    return facts, inferences, risks, assumptions, missing


def _infer_instrument_type(order_lines: list[OrderLine], has_option_context: bool) -> str:
    if has_option_context or any(_has_option_order(order) for order in order_lines):
        return "option"
    if any(order.instrument == "stock" for order in order_lines):
        return "stock"
    return "unknown"


def _explicit_requested_capabilities(question: str) -> set[str]:
    lowered = question.lower()
    requested = set()
    if any(term in lowered for term in ("check news", "news", "earnings", "fomc", "catalyst")):
        requested.add(CAP_NEWS)
    if "fear" in lowered and "greed" in lowered:
        requested.add(CAP_FEAR_GREED)
    if "open interest" in lowered or " oi" in f" {lowered}":
        requested.add(CAP_OPTION_OPEN_INTEREST)
    if "iv" in lowered or "implied volatility" in lowered:
        requested.add(CAP_OPTION_IV)
    if "greek" in lowered or "delta" in lowered:
        requested.add(CAP_OPTION_GREEKS)
    if "vix" in lowered:
        requested.add(CAP_VIX)
    if "uvix" in lowered:
        requested.add(CAP_UVIX)
    if any(term in lowered for term in ("spy", "qqq", "soxx", "index context", "sector context")):
        requested.add(CAP_INDEX_CONTEXT)
    return requested


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
        order_lines: Optional[list[OrderLine]] = None,
        existing_related_exposure: Optional[list[str]] = None,
        analysis_saved: bool = False,
        analysis_path: str = "",
        trade_log_updated: bool = False,
        saved_status_reason: str = "",
    ) -> AnalysisResult:
        scenario_list = list(scenarios)
        parsed_order_lines = _meaningful_order_lines(order_lines if order_lines is not None else parse_order_lines(question))
        related_exposure = existing_related_exposure or []
        has_option_context = bool(option_expiry or option_strike is not None or option_type)
        inferred_instrument_type = _infer_instrument_type(parsed_order_lines, has_option_context)
        explicit_requested_capabilities = _explicit_requested_capabilities(question)
        has_stock_concentration = any(_is_stock_proposal(order, symbol) for order in parsed_order_lines) and bool(
            related_exposure
        )
        has_duplicate_option_exposure = (
            _has_option_proposal_context(parsed_order_lines, question, has_option_context) and bool(related_exposure)
        )
        if has_stock_concentration:
            position_fit = min(position_fit, 0)
            market_regime = min(market_regime, 4)
            options_structure = min(options_structure, 0)
            psychology_rule_fit = min(psychology_rule_fit, 2)
        if has_duplicate_option_exposure:
            position_fit = min(position_fit, 4)
            options_structure = min(options_structure, 4)
            psychology_rule_fit = min(psychology_rule_fit, 3)
        market_data_bundle = self.provider_resolver.resolve_market_data(
            symbol,
            expiry=option_expiry,
            strike=option_strike,
            option_type=option_type,
            command="trade",
            instrument_type=inferred_instrument_type,
            strategy_type=strategy_type,
            has_option_legs=has_option_context,
            user_explicitly_requested=explicit_requested_capabilities,
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
        proposed_stock_missing_data = _proposed_stock_missing_data(parsed_order_lines, symbol)
        (
            duplicate_option_facts,
            duplicate_option_inferences,
            duplicate_option_risks,
            duplicate_option_assumptions,
            duplicate_option_missing_data,
        ) = _duplicate_option_exposure_context(symbol, question, option_strike, option_type, related_exposure)
        hard_missing_data.extend(duplicate_option_missing_data)
        missing_data = _ordered_unique(market_data_bundle.missing_data + hard_missing_data + proposed_stock_missing_data)
        missing_data.extend(f"scenario estimate: {warning}" for warning in scenario_validation.warnings)
        missing_count = len(hard_missing_data) + len(proposed_stock_missing_data)
        unstable = classified_data_quality == "low" or bool(hard_missing_data) or not scenario_validation.is_valid

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
        proposal_facts, proposal_inferences, proposal_risks, proposal_assumptions = _stock_proposal_context(
            parsed_order_lines,
            symbol,
            related_exposure,
        )
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
            risk_assessment=_default_risk_assessment(classified_data_quality, missing_data) + proposal_risks + duplicate_option_risks,
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
            ]
            + proposal_facts
            + duplicate_option_facts,
            user_claims=[f"user question: {question}"],
            ai_inferences=[f"data quality classified as {classified_data_quality}"]
            + proposal_inferences
            + duplicate_option_inferences,
            assumptions=[
                "position fit, market regime, options structure, and psychology scores use supplied arguments or local defaults"
            ]
            + proposal_assumptions
            + duplicate_option_assumptions,
            order_lines=parsed_order_lines,
            analysis_saved=analysis_saved,
            analysis_path=analysis_path,
            trade_log_updated=trade_log_updated,
            saved_status_reason=saved_status_reason
            or "analysis generated as a draft; trade log requires explicit user confirmation",
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
            strike=option_strike,
            option_type=option_type,
            command="trade",
            instrument_type="option" if option_expiry or option_strike is not None or option_type else "unknown",
            has_option_legs=bool(option_expiry or option_strike is not None or option_type),
            user_explicitly_requested=_explicit_requested_capabilities(str(question)),
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
