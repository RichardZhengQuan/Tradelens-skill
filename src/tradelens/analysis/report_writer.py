"""Render deterministic analysis results to markdown."""

from __future__ import annotations

import re
from dataclasses import replace
from datetime import datetime
from typing import Optional

from tradelens.analysis.report_contract import (
    DISCLAIMER as STANDARD_DISCLAIMER,
    display_judgment,
    enforce_report_contract,
    ensure_report_disclaimer,
    normalize_trade_judgment,
    sanitize_report_text,
)
from tradelens.calculations.scenarios import describe_scenario_missing_data
from tradelens.data.market_snapshot import datetime_to_text
from tradelens.data.market_data import available_underlying_price
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
)
from tradelens.models import AnalysisResult, Scenario, TermScore, TradeScore, TradeTerm


def format_money(value: Optional[float]) -> str:
    if value is None:
        return "unknown"
    if value < 0:
        return f"-${abs(value):,.2f}"
    sign = "+" if value > 0 else ""
    return f"{sign}${value:,.2f}"


def format_probability(value: Optional[float]) -> str:
    if value is None:
        return "unknown"
    return f"{value:.0%}"


def _sanitize_report_text(value: object) -> str:
    return sanitize_report_text(value)


def _scenario_result_phrase(scenario: Optional[Scenario]) -> str:
    if scenario is None or scenario.profit_loss is None:
        return "an unknown outcome"
    amount = f"${abs(scenario.profit_loss):,.2f}"
    if scenario.profit_loss > 0:
        return f"earn about {amount}"
    if scenario.profit_loss < 0:
        return f"lose about {amount}"
    return "break even"


def _scenario_by_name(result: AnalysisResult, name: str, fallback_index: Optional[int] = None) -> Optional[Scenario]:
    for scenario in result.scenarios:
        if scenario.name.lower() == name.lower():
            return scenario
    if fallback_index is not None and 0 <= fallback_index < len(result.scenarios):
        return result.scenarios[fallback_index]
    return None


def _scenario_by_name_from_list(scenarios: list[Scenario], name: str, fallback_index: Optional[int] = None) -> Optional[Scenario]:
    for scenario in scenarios:
        if scenario.name.lower() == name.lower():
            return scenario
    if fallback_index is not None and 0 <= fallback_index < len(scenarios):
        return scenarios[fallback_index]
    return None


def _scenario_probability(scenario: Optional[Scenario]) -> str:
    if scenario is None or scenario.probability is None:
        return "unknown"
    return f"{format_probability(scenario.probability)} ({scenario.probability_type}, {scenario.estimate_label})"


def _scenario_probability_value(scenario: Optional[Scenario]) -> str:
    if scenario is None or scenario.probability is None:
        return "unknown"
    return format_probability(scenario.probability)


def _scenario_probability_type(scenario: Optional[Scenario]) -> str:
    if scenario is None or scenario.probability is None:
        return "unknown"
    return scenario.probability_type


def _scenario_estimate_label(scenario: Optional[Scenario]) -> str:
    if scenario is None or scenario.probability is None:
        return "unknown"
    return scenario.estimate_label


def _scenario_pl(scenario: Optional[Scenario]) -> str:
    return "unknown" if scenario is None else format_money(scenario.profit_loss)


def _render_items(items: list[str], empty: str = "not provided") -> str:
    if not items:
        return f"- {empty}"
    return "\n".join(f"- {_sanitize_report_text(item)}" for item in items)


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def _format_optional_number(value: Optional[float]) -> str:
    return "unknown" if value is None else f"{value:g}"


def _render_context_prices(context_prices: dict[str, Optional[float]]) -> str:
    rows = []
    for symbol in ("SPY", "QQQ", "SOXX"):
        rows.append(f"- {symbol}: {_format_optional_number(context_prices.get(symbol))}")
    return "\n".join(rows)


def _render_news(headlines: list[str]) -> str:
    if not headlines:
        return "- unknown"
    return "\n".join(f"- {headline}" for headline in headlines[:5])


def _freshness(data_time) -> str:
    return datetime_to_text(data_time)


def _status(value: bool) -> str:
    return "found" if value else "missing"


def _realtime_delay_note(snapshot: object) -> str:
    realtime = getattr(snapshot, "is_realtime", None)
    delayed = getattr(snapshot, "is_delayed", None)
    realtime_text = "unknown" if realtime is None else _yes_no(bool(realtime))
    delayed_text = "unknown" if delayed is None else _yes_no(bool(delayed))
    return f"realtime={realtime_text}; delayed={delayed_text}"


def _table_cell(value: object) -> str:
    text = _sanitize_report_text(value)
    return text.replace("\n", " ").replace("|", "/")


def _term_score_why(score: TermScore) -> str:
    why = score.reason or "no term-specific edge identified"
    risk = score.main_risk or "standard trade risk"
    if risk != "standard trade risk" and risk not in why:
        why = f"{why}; main risk: {risk}"
    return why


def _selected_contract(result: AnalysisResult):
    bundle = result.market_data_bundle
    chain = bundle.option_chain if bundle else None
    if chain is None or not chain.contracts:
        return None
    for contract in chain.contracts:
        if getattr(contract, "selected", False):
            return contract
    return chain.contracts[0]


def _render_option_quote(result: AnalysisResult) -> str:
    quote = result.market_snapshot.option_quote
    if quote is None:
        return """- Option mark: unknown
- Option bid: unknown
- Option ask: unknown
- Open interest: unknown
- Volume: unknown
- IV: unknown
- Delta: unknown"""
    return f"""- Option mark: {_format_optional_number(quote.mark)}
- Option bid: {_format_optional_number(quote.bid)}
- Option ask: {_format_optional_number(quote.ask)}
- Open interest: {"unknown" if quote.open_interest is None else quote.open_interest}
- Volume: {"unknown" if quote.volume is None else quote.volume}
- IV: {_format_optional_number(quote.iv)}
- Delta: {_format_optional_number(quote.delta)}"""


def _ordered_unique(items: list[str]) -> list[str]:
    seen = set()
    unique = []
    for item in items:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


def _combined_missing_data(result: AnalysisResult) -> list[str]:
    return _ordered_unique(list(result.missing_data) + describe_scenario_missing_data(result.scenarios))


def _confidence(result: AnalysisResult) -> str:
    classified = result.classified_data_quality or result.market_snapshot.data_quality
    if result.trade_judgment == "no clear edge" or result.trade_score.stability == "unstable":
        return "Low"
    if _combined_missing_data(result):
        return "Low"
    if classified == "high":
        return "High"
    return "Medium"


def render_trade_score(score: TradeScore) -> str:
    b = score.breakdown
    base = _scenario_by_name_from_list(score.scenarios, "base", 0)
    downside = _scenario_by_name_from_list(score.scenarios, "downside", 1)
    worst = _scenario_by_name_from_list(score.scenarios, "worst", 2)
    explanation = _render_items(score.notes, empty="not provided")
    return f"""## Trade Judgment Details
- trade_judgment: {normalize_trade_judgment(score.label)}
- score: {score.score:.0f}/100
- score stability: {score.stability}
- probability sources:
  - market-implied probability: label separately when used
  - scenario probability: label separately when used
  - user-defined probability: label separately when used
- estimated scenarios:
  - base case probability:
    - value: {_scenario_probability_value(base)}
    - probability type: {_scenario_probability_type(base)}
    - estimate label: {_scenario_estimate_label(base)}
  - base case profit/loss: {_scenario_pl(base)}
  - downside case probability:
    - value: {_scenario_probability_value(downside)}
    - probability type: {_scenario_probability_type(downside)}
    - estimate label: {_scenario_estimate_label(downside)}
  - downside case profit/loss: {_scenario_pl(downside)}
  - worst reasonable case probability:
    - value: {_scenario_probability_value(worst)}
    - probability type: {_scenario_probability_type(worst)}
    - estimate label: {_scenario_estimate_label(worst)}
  - worst reasonable case profit/loss: {_scenario_pl(worst)}
- estimated expected value:
  - probability-weighted expected return: {format_money(score.expected_value)}
  - max reasonable gain: {format_money(score.max_reasonable_gain)}
  - max reasonable loss: {format_money(score.max_reasonable_loss)}
  - capital required: {format_money(score.capital_required)}
  - return on capital if calculable: {"unknown" if score.return_on_capital is None else f"{score.return_on_capital:.1%}"}
- score breakdown:
  - Reward / Risk: {b.reward_risk:.0f}/25
  - Probability Setup: {b.probability_setup:.0f}/20
  - Position Fit: {b.position_fit:.0f}/20
  - Market Regime: {b.market_regime:.0f}/15
  - Options Structure: {b.options_structure:.0f}/15
  - Psychology / Rule Fit: {b.psychology_rule_fit:.0f}/10
  - Data Quality Adjustment: {b.data_quality_adjustment:.0f}
- score explanation:
{explanation}
"""


def _contains_cjk(text: str) -> bool:
    return bool(re.search(r"[\u3400-\u9fff]", text or ""))


def _result_uses_chinese(result: AnalysisResult) -> bool:
    text = "\n".join(
        [result.question]
        + result.visible_facts
        + result.user_claims
        + result.ai_inferences
        + result.assumptions
        + [line.notes for line in result.order_lines]
    )
    return _contains_cjk(text)


def _term_label(term: TradeTerm, bilingual: bool = False) -> str:
    labels = {
        TradeTerm.INTRADAY: "Intraday",
        TradeTerm.SHORT_TERM: "Short-term",
        TradeTerm.MEDIUM_TERM: "Medium-term",
        TradeTerm.LONG_TERM: "Long-term",
        TradeTerm.CUSTOM: "Custom",
        TradeTerm.UNKNOWN: "Unknown",
    }
    if bilingual:
        labels = {
            TradeTerm.INTRADAY: "日内 / Intraday",
            TradeTerm.SHORT_TERM: "短线 / Short-term",
            TradeTerm.MEDIUM_TERM: "中线 / Medium-term",
            TradeTerm.LONG_TERM: "长期 / Long-term",
            TradeTerm.CUSTOM: "自定义 / Custom",
            TradeTerm.UNKNOWN: "未知 / Unknown",
        }
    return labels.get(term, term.value)


def render_term_scores(term_scores: list, bilingual: bool = False) -> str:
    by_term = {score.term: score for score in term_scores}
    rows = []
    for term in (TradeTerm.INTRADAY, TradeTerm.SHORT_TERM, TradeTerm.MEDIUM_TERM, TradeTerm.LONG_TERM):
        score = by_term.get(term)
        if score is None:
            rows.append(f"| {_term_label(term, bilingual)} | NO CLEAR EDGE |  | term judgment unavailable |")
            continue
        marker = " (intended)" if score.is_intended_term else ""
        rows.append(
            f"| {_term_label(score.term, bilingual)}{marker} | {display_judgment(score.label)} | {score.score:.0f}/100 | {_table_cell(_term_score_why(score))} |"
        )
    for score in term_scores:
        if score.term not in {TradeTerm.INTRADAY, TradeTerm.SHORT_TERM, TradeTerm.MEDIUM_TERM, TradeTerm.LONG_TERM}:
            marker = " (intended)" if score.is_intended_term else ""
            rows.append(
                f"| {_term_label(score.term, bilingual)}{marker} | {display_judgment(score.label)} | {score.score:.0f}/100 | {_table_cell(_term_score_why(score))} |"
            )
    body = "\n".join(rows)
    return f"""## **Term-Aware Trade Judgment**

| Term | Judgment | Score | Why |
|---|---|---:|---|
{body}
"""


def _term_score(term_scores: list, term: TradeTerm) -> Optional[TermScore]:
    for score in term_scores:
        if score.term == term:
            return score
    return None


def _intended_term_score(result: AnalysisResult) -> Optional[TermScore]:
    for score in result.term_scores:
        if score.is_intended_term:
            return score
    return None


def _final_conclusion_line(result: AnalysisResult) -> str:
    return f"{display_judgment(result.trade_judgment)} — {result.trade_score.score:.0f}/100."


def _term_conclusion(result: AnalysisResult) -> str:
    short = _term_score(result.term_scores, TradeTerm.SHORT_TERM)
    long = _term_score(result.term_scores, TradeTerm.LONG_TERM)
    intended = _intended_term_score(result)

    lines = []
    if short and long and short.label != long.label:
        lines.append(
            f"This trade is {normalize_trade_judgment(short.label)} for short-term and {normalize_trade_judgment(long.label)} for long-term."
        )
    if intended:
        lines.append(
            f"The intended term is {_term_label(intended.term)}; that term-aware judgment is {normalize_trade_judgment(intended.label)} with a score of {intended.score:.0f}."
        )
    elif result.trade_intent.intended_term == TradeTerm.UNKNOWN:
        lines.append(
            "The intended trade term is unknown, so this analysis compares intraday, short-term, medium-term, and long-term trade quality."
        )
    return "\n\n".join(lines)


def _stock_quantity(result: AnalysisResult) -> Optional[float]:
    for order in result.order_lines:
        if order.symbol.upper() == result.symbol.upper() and order.instrument == "stock" and order.quantity is not None:
            return order.quantity
    match = re.search(r"(?i)(\d+(?:\.\d+)?)\s*(?:shares?|stocks?|股)", result.question)
    if match:
        return float(match.group(1))
    return None


def _format_quantity(value: Optional[float]) -> str:
    if value is None:
        return "unknown"
    return f"{value:g}"


def _has_stock_proposal(result: AnalysisResult) -> bool:
    return any(order.instrument == "stock" and order.symbol.upper() == result.symbol.upper() for order in result.order_lines)


def _has_concentration_risk(result: AnalysisResult) -> bool:
    haystack = "\n".join(
        result.risk_assessment
        + result.visible_facts
        + result.user_claims
        + result.ai_inferences
        + result.assumptions
        + result.missing_data
    ).lower()
    return "concentration" in haystack or "集中" in haystack or "short put" in haystack


def _has_duplicate_option_exposure_risk(result: AnalysisResult) -> bool:
    haystack = "\n".join(
        result.risk_assessment
        + result.visible_facts
        + result.ai_inferences
        + result.assumptions
        + result.missing_data
    ).lower()
    return "duplicate" in haystack and "option" in haystack


def _render_order_lines(result: AnalysisResult) -> str:
    if not result.order_lines:
        return "- none"
    rows = []
    for order in result.order_lines:
        rows.append(
            "- "
            + "; ".join(
                [
                    f"id={_table_cell(order.order_line_id)}",
                    f"symbol={_table_cell(order.symbol)}",
                    f"action_text={_table_cell(order.action)}",
                    f"quantity={_format_optional_number(order.quantity)}",
                    f"instrument={_table_cell(order.instrument)}",
                    f"order_type={_table_cell('unknown')}",
                    f"entry_price={_format_optional_number(order.order_price or order.filled_price)}",
                ]
            )
        )
    return "\n".join(rows)


def _title_reason(result: AnalysisResult) -> str:
    judgment = normalize_trade_judgment(result.trade_judgment)
    if _has_stock_proposal(result) and _has_concentration_risk(result):
        quantity = _format_quantity(_stock_quantity(result))
        if _result_uses_chinese(result):
            return f"{quantity} 股 {result.symbol.upper()} 仓位暴露过于集中"
        return f"{quantity}-share {result.symbol.upper()} stock proposal creates concentrated exposure"
    if judgment == "no clear edge" and _has_duplicate_option_exposure_risk(result):
        return f"Existing {result.symbol.upper()} option exposure may already cover this idea"
    if judgment == "no clear edge":
        return "Trade details not confirmed" if _combined_missing_data(result) else "No clear term edge confirmed"
    reasons = {
        "good": "Scenario profile supports trade quality",
        "mostly good": "Constructive setup with remaining risk",
        "neutral": "Trade quality is mixed",
        "mostly bad": "Risk profile is weak",
        "bad": "Risk/reward profile is poor",
    }
    return reasons[judgment]


def _summary_lines(result: AnalysisResult, confidence: str) -> str:
    lines = []
    if _has_duplicate_option_exposure_risk(result):
        lines.append(
            "This proposed trade has no clear edge until it is confirmed whether it is a new second contract or the existing option position."
        )
        lines.append(
            "If it is a second contract at the same strike, the trade quality weakens because assignment exposure would increase."
        )
        lines.append(
            "The trade quality would improve only if position size, premium, and assignment plan are confirmed."
        )
    elif _has_stock_proposal(result) and _has_concentration_risk(result):
        if _result_uses_chinese(result):
            lines.append("这笔交易的主要问题是仓位结构：相关标的暴露可能过于集中。")
        else:
            lines.append("The main issue is concentration risk and position fit, not the symbol alone.")
    else:
        term_conclusion = _term_conclusion(result)
        if term_conclusion:
            lines.extend(term_conclusion.split("\n\n")[:2])
        else:
            lines.append("Overall judgment is a summary of the term-aware judgments below.")
    if len(lines) < 2 and _combined_missing_data(result):
        if _result_uses_chinese(result):
            lines.append(f"Confidence is {confidence}; 缺失或低质量输入会削弱本次判断。")
        else:
            lines.append(f"Confidence is {confidence}; missing or low-quality inputs weaken the judgment.")
    elif len(lines) < 2:
        lines.append(f"Confidence is {confidence} based on supplied scenarios and market-data quality.")
    lines.append(f"trade_judgment: {normalize_trade_judgment(result.trade_judgment)}")
    lines.append(f"score stability: {result.trade_score.stability}")
    return "\n".join(_sanitize_report_text(line) for line in lines[:4])


def render_market_data_status(result: AnalysisResult) -> str:
    snapshot = result.market_snapshot
    bundle = result.market_data_bundle
    quote = bundle.quote if bundle else None
    chain = bundle.option_chain if bundle else None
    contract = _selected_contract(result)
    news = bundle.news if bundle else None
    volatility = bundle.volatility if bundle else None
    index_context = bundle.index_context if bundle else None
    fallback = " > ".join(bundle.fallback_path_used) if bundle and bundle.fallback_path_used else snapshot.fallback_used
    quote_provider = quote.provider_name if quote else snapshot.stock_price_provider
    chain_provider = chain.provider_name if chain else snapshot.options_provider
    news_provider = news.provider_name if news else snapshot.news_provider
    volatility_provider = volatility.provider_name if volatility else snapshot.volatility_provider
    rows = [
        _capability_row(
            result,
            CAP_QUOTE,
            "Underlying price",
            _status(quote is not None and quote.price is not None),
            quote_provider,
            _freshness(quote.data_time if quote else None),
            quote.data_quality if quote else "low",
            f"price={_format_optional_number(quote.price if quote else available_underlying_price(snapshot))}; session={quote.session if quote else snapshot.session}; {_realtime_delay_note(quote) if quote else 'realtime=unknown; delayed=unknown'}",
        ),
        _capability_row(
            result,
            CAP_OPTION_CHAIN,
            "Option chain",
            _status(chain is not None and bool(chain.contracts)),
            chain_provider,
            _freshness(chain.data_time if chain else None),
            chain.data_quality if chain else "low",
            f"contracts available; {_realtime_delay_note(chain)}" if chain and chain.contracts else "option chain for relevant expiry missing",
        ),
        _capability_row(
            result,
            _first_skipped_capability(result, (CAP_OPTION_GREEKS, CAP_OPTION_IV, CAP_OPTION_CHAIN)),
            "Greeks / IV",
            _status(contract is not None and (contract.iv is not None or contract.delta is not None)),
            chain_provider,
            _freshness(contract.data_time if contract else None),
            contract.data_quality if contract else "low",
            f"IV={_format_optional_number(contract.iv if contract else None)}; delta={_format_optional_number(contract.delta if contract else None)}",
        ),
        _capability_row(
            result,
            _first_skipped_capability(result, (CAP_OPTION_OPEN_INTEREST, CAP_OPTION_CHAIN)),
            "Open interest",
            _status(contract is not None and contract.open_interest is not None),
            chain_provider,
            _freshness(contract.data_time if contract else None),
            contract.data_quality if contract else "low",
            f"open_interest={_table_cell(contract.open_interest if contract else None)}",
        ),
        _capability_row(
            result,
            _first_skipped_capability(result, (CAP_VIX, CAP_UVIX)),
            "VIX / UVIX",
            _status(volatility is not None and (volatility.vix is not None or volatility.uvix is not None)),
            volatility_provider,
            _freshness(volatility.data_time if volatility else None),
            volatility.data_quality if volatility else "low",
            f"VIX={_format_optional_number(volatility.vix if volatility else None)}; UVIX={_format_optional_number(volatility.uvix if volatility else None)}",
        ),
        _capability_row(
            result,
            CAP_FEAR_GREED,
            "Fear & Greed",
            _status(volatility is not None and volatility.fear_greed is not None),
            volatility_provider if volatility and volatility.fear_greed is not None else "CNN Fear & Greed / manual / missing",
            _freshness(volatility.data_time if volatility else None),
            volatility.data_quality if volatility else "low",
            f"value={_format_optional_number(volatility.fear_greed if volatility else None)}; label={_table_cell(volatility.fear_greed_label if volatility else None)}",
        ),
        _capability_row(
            result,
            CAP_NEWS,
            "News",
            _status(news is not None and bool(news.headlines)),
            news_provider,
            _freshness(news.data_time if news else None),
            news.data_quality if news else "low",
            f"{len(news.headlines) if news else 0} headline(s)",
        ),
        _capability_row(
            result,
            CAP_INDEX_CONTEXT,
            "SPY / QQQ / SOXX",
            _status(index_context is not None and any((index_context.spy, index_context.qqq, index_context.soxx))),
            index_context.provider_name if index_context else "missing",
            _freshness(index_context.fetched_at if index_context else None),
            index_context.data_quality if index_context else "low",
            "index context available" if index_context else "index context missing",
        ),
    ]
    table = "\n".join(
        f"| {_table_cell(data)} | {_table_cell(status)} | {_table_cell(provider)} | {_table_cell(freshness)} | {_table_cell(quality)} | {_table_cell(notes)} |"
        for data, status, provider, freshness, quality, notes in rows
    )
    missing = _render_items(_combined_missing_data(result), empty="none")
    return f"""## Market Data Status
| Data | Status | Provider / Source | Freshness | Quality | Notes |
|---|---|---|---|---|---|
{table}

- Raw provider data quality: {bundle.raw_data_quality if bundle else snapshot.data_quality}
- Classified data quality: {result.classified_data_quality or snapshot.data_quality}
- Reason for downgrade: {result.data_quality_downgrade_reason or "none"}
- Fallback path used: {fallback}
- Missing data:
{missing}
- Underlying latest price: {_format_optional_number(available_underlying_price(snapshot))}
- Market session: {snapshot.session}
- Quote timestamp: {snapshot.quote_timestamp if snapshot.quote_timestamp not in ("", None) else "unknown"}
- Options:
{_render_option_quote(result)}
- Volatility: {snapshot.volatility_symbol} {_format_optional_number(snapshot.volatility_price)}
- SPY / QQQ / SOXX latest context:
{_render_context_prices(snapshot.context_prices)}
- Newest company news:
{_render_news(snapshot.news_headlines)}
"""


def _first_skipped_capability(result: AnalysisResult, capabilities: tuple[str, ...]) -> str:
    skipped = result.market_data_bundle.skipped_capabilities if result.market_data_bundle else {}
    for capability in capabilities:
        if capability in skipped:
            return capability
    return capabilities[0]


def _capability_row(
    result: AnalysisResult,
    capability: str,
    data: str,
    status: str,
    provider: str,
    freshness: str,
    quality: str,
    notes: str,
) -> tuple[str, str, str, str, str, str]:
    skipped = result.market_data_bundle.skipped_capabilities if result.market_data_bundle else {}
    reason = skipped.get(capability)
    if reason:
        return data, "not required", "Smart Fetch", "not applicable", "not applicable", reason
    plan = result.market_data_bundle.capability_plan if result.market_data_bundle else None
    if plan and capability in plan.optional and status == "missing":
        return data, "not requested", "Smart Fetch", "not applicable", "not applicable", plan.reason_by_capability.get(capability, "not requested")
    return data, status, provider, freshness, quality, notes


def render_provider_attempts(result: AnalysisResult) -> str:
    bundle = result.market_data_bundle
    if not bundle or not bundle.provider_statuses:
        rows = "| unknown | none | missing | no provider attempts recorded |"
    else:
        rows = "\n".join(
            f"| {_table_cell(status.capability)} | {_table_cell(status.provider_name)} | {_table_cell(status.status)} | {_table_cell(status.error or '; '.join(status.notes) or 'none')} |"
            for status in bundle.provider_statuses
        )
    return f"""## Provider Attempts
| Capability | Attempted Provider | Result | Error / Note |
|---|---|---|---|
{rows}
"""


def render_opend_provider_status(result: AnalysisResult) -> str:
    bundle = result.market_data_bundle
    setup = bundle.opend_provider_setup_result if bundle else None
    statuses = bundle.provider_statuses if bundle else []
    provider_type = setup.provider_type if setup else _opend_provider_type_from_statuses(statuses)
    host = setup.host if setup else "127.0.0.1"
    port = setup.port if setup else 11111
    read_only = setup.read_only if setup else True
    trading_enabled = setup.trading_enabled if setup else False
    password_stored = setup.password_stored if setup else False
    opend_reachable = setup.opend_reachable if setup else False
    process_detected = setup.opend_process_detected if setup else False
    port_reachable = setup.opend_port_reachable if setup else False
    direct_quote_success = setup.direct_opend_quote_success if setup else False
    python_executable = setup.python_executable if setup else "unknown"
    sdk_installed = setup.sdk_installed if setup else False
    sdk_connection_success = setup.sdk_connection_success if setup else False
    test_quote = "success" if setup and setup.test_quote_success else "failed"
    sdk_label = "futu-api installed" if provider_type == "Futu OpenD" else "SDK installed"
    rows = [
        ("Provider type", provider_type),
        ("OpenD verified data source", _yes_no(opend_reachable)),
        ("OpenD process detected", _yes_no(process_detected)),
        ("OpenD port reachable", _yes_no(port_reachable)),
        ("Direct OpenD quote test", "success" if direct_quote_success else "fail"),
        ("Python executable used", python_executable),
        (sdk_label, _yes_no(sdk_installed)),
        ("SDK connection test", "success" if sdk_connection_success else "fail"),
        ("Host", host),
        ("Port", port),
        ("Read-only mode", _yes_no(read_only)),
        ("Trading enabled", _yes_no(trading_enabled)),
        ("Password stored", _yes_no(password_stored)),
        ("Test quote", test_quote),
    ]
    table = "\n".join(f"| {_table_cell(item)} | {_table_cell(status)} |" for item, status in rows)
    return f"""## OpenD Provider Status
| Item | Status |
|---|---|
{table}
"""


def _opend_provider_type_from_statuses(statuses) -> str:
    for status in statuses:
        if status.provider_name == "FutuOpenDProvider" or status.provider_name == "FutuProvider":
            return "Futu OpenD"
        if status.provider_name == "MoomooOpenDProvider":
            return "Moomoo OpenD"
        if status.provider_name == "OpenDProvider":
            return "unknown"
    return "unknown"


def render_saved_status(
    analysis_saved: bool = False,
    analysis_path: str = "",
    trade_log_updated: bool = False,
    reason: str = "",
    feedback_status: str = "no feedback",
) -> str:
    return f"""## Saved Status
- Analysis saved: {_yes_no(analysis_saved)}
- Analysis path: {_table_cell(analysis_path or "not saved")}
- Trade log updated: {_yes_no(trade_log_updated)}
- Reason: {_sanitize_report_text(reason or "analysis generated as a draft; trade log requires explicit user confirmation")}
- Feedback status: {_table_cell(feedback_status or "no feedback")}
"""


def mark_report_saved(
    report: str,
    analysis_path: str,
    trade_log_updated: bool = False,
    reason: str = "analysis_history record saved; trade log requires explicit user confirmation",
    feedback_status: str = "no feedback",
) -> str:
    if "## Saved Status" not in report and "## **Saved Status**" not in report:
        return report
    saved_status = render_saved_status(
        analysis_saved=True,
        analysis_path=analysis_path,
        trade_log_updated=trade_log_updated,
        reason=reason,
        feedback_status=feedback_status,
    ).rstrip()
    pattern = re.compile(r"^## (?:\*\*)?Saved Status(?:\*\*)?\n.*\Z", re.MULTILINE | re.DOTALL)
    return pattern.sub(saved_status, report.rstrip()) + "\n"


def write_analysis_report(result: AnalysisResult) -> str:
    base = _scenario_by_name(result, "base", 0)
    downside = _scenario_by_name(result, "downside", 1)
    worst = _scenario_by_name(result, "worst", 2)
    snapshot = result.market_snapshot
    term_block = render_term_scores(result.term_scores, bilingual=False)
    market_status_block = render_market_data_status(result).replace("## Market Data Status\n", "").strip()
    opend_status_block = render_opend_provider_status(result).replace("## OpenD Provider Status\n", "").strip()
    provider_attempts_block = render_provider_attempts(result).replace("## Provider Attempts\n", "").strip()
    missing = _render_items(_combined_missing_data(result), empty="none")
    risk_assessment = _render_items(result.risk_assessment, empty="not provided")
    invalidation_conditions = _render_items(result.invalidation_conditions, empty="not provided")
    bad_conditions = _render_items(result.what_would_make_this_trade_bad, empty="not provided")
    better_conditions = _render_items(result.what_would_make_this_trade_better, empty="not provided")
    score_notes = _render_items(result.trade_score.notes, empty="none")
    confidence = _confidence(result)
    validation = result.scenario_validation
    probability_sum = "unknown" if validation is None or validation.probability_sum is None else f"{validation.probability_sum:.4f}"
    scenario_confidence = "unknown" if validation is None else validation.scenario_confidence
    scenario_warnings = _render_items(validation.warnings if validation else [], empty="none")
    scenario_error = validation.error_message if validation and validation.error_message else "none"
    raw_quality = snapshot.data_quality
    classified_quality = result.classified_data_quality or raw_quality
    downgrade_reason = result.data_quality_downgrade_reason or "none"
    judgment = normalize_trade_judgment(result.trade_judgment)
    summary = _summary_lines(result, confidence)
    title_reason = _sanitize_report_text(_title_reason(result))
    visible_facts = _render_items(result.visible_facts, empty="none")
    user_claims = _render_items(result.user_claims, empty="none")
    ai_inferences = _render_items(result.ai_inferences, empty="none")
    assumptions = _render_items(result.assumptions, empty="none")
    order_lines = _render_order_lines(result)
    fallback_path = (
        " > ".join(result.market_data_bundle.fallback_path_used)
        if result.market_data_bundle and result.market_data_bundle.fallback_path_used
        else snapshot.fallback_used
    )
    report = f"""# **{display_judgment(judgment)} — {title_reason}**

{summary}

{term_block}

## Why
- Scenario profile: estimated {_scenario_probability_value(base)} chance to {_scenario_result_phrase(base)}, {_scenario_probability_value(downside)} chance to {_scenario_result_phrase(downside)}, and {_scenario_probability_value(worst)} chance to {_scenario_result_phrase(worst)}.
- Estimated EV: {format_money(result.expected_value)}.
- Probability sum: {probability_sum}.
- Scenario confidence: {scenario_confidence}.
- Scenario warnings:
{scenario_warnings}
- Scenario error: {scenario_error}.

## What I Parsed
- Confirmation status: local analysis draft; extracted screenshot fields require user confirmation before saving.
- Related symbol: {_table_cell(result.symbol)}
- User question: {_table_cell(result.question)}
- Visible facts:
{visible_facts}
- User claims:
{user_claims}
- Parsed order lines:
{order_lines}
- AI inferences:
{ai_inferences}
- Assumptions:
{assumptions}

## Key Numbers
- Overall score summary: {result.trade_score.score:.0f}/100 after the term-aware judgments above.
- Expected value: {format_money(result.expected_value)}.
- Win probability: {format_probability(result.win_probability)}.
- Max reasonable gain: {format_money(result.trade_score.max_reasonable_gain)}.
- Max reasonable loss: {format_money(result.trade_score.max_reasonable_loss)}.
- Capital required: {format_money(result.trade_score.capital_required)}.
- Return on capital: {"unknown" if result.trade_score.return_on_capital is None else f"{result.trade_score.return_on_capital:.1%}"}.
- Underlying price: {_format_optional_number(available_underlying_price(snapshot))}.
- Option mechanics:
{_render_option_quote(result)}

## Risk Check
- Top risks:
{risk_assessment}
- Trade quality worsens if:
{bad_conditions}
- Trade quality improves if:
{better_conditions}
- Invalidation conditions:
{invalidation_conditions}

## Missing Data / Confirmation Needed
- Missing data:
{missing}
- Score notes:
{score_notes}
- Confirmation needed: confirm any extracted order, account, position, price, expiry, strike, premium, and scenario fields before saving them as durable records.
- Confidence: {confidence}

## Data Used
- Analysis time: {result.created_at.isoformat()}
- Raw provider data quality: {_table_cell(raw_quality)}
- Classified data quality: {_table_cell(classified_quality)}
- Reason for downgrade: {_table_cell(downgrade_reason)}
- Fallback path used: {_table_cell(fallback_path)}
- Data quality adjustment: {result.trade_score.breakdown.data_quality_adjustment:.0f}

**Market data status**
{market_status_block}

**OpenD provider status**
{opend_status_block}

**Provider attempts**
{provider_attempts_block}

{render_saved_status(
        analysis_saved=result.analysis_saved,
        analysis_path=result.analysis_path,
        trade_log_updated=result.trade_log_updated,
        reason=result.saved_status_reason,
        feedback_status=result.feedback_status,
    ).rstrip()}
"""
    return enforce_report_contract(report)


# Backward-compatible wrapper from the first skeleton.
def render_analysis_report(
    trade_score: TradeScore,
    question: str = "unknown",
    symbol: str = "unknown",
    created_at: Optional[datetime] = None,
) -> str:
    from tradelens.models import MarketSnapshot

    missing_data = ["market snapshot not supplied"]
    safe_score = _legacy_safe_trade_score(trade_score, missing_data)
    result = AnalysisResult(
        symbol=symbol,
        question=question,
        market_snapshot=MarketSnapshot(symbol=symbol),
        scenarios=safe_score.scenarios,
        expected_value=safe_score.expected_value,
        win_probability=safe_score.win_probability,
        trade_score=safe_score,
        term_scores=[],
        trade_judgment="no clear edge",
        classified_data_quality="low",
        data_quality_downgrade_reason="legacy report wrapper lacks structured market data proof",
        missing_data=missing_data,
        created_at=created_at or datetime.utcnow(),
    )
    return enforce_report_contract(write_analysis_report(result))


def _legacy_safe_trade_score(trade_score: TradeScore, missing_data: list[str]) -> TradeScore:
    notes = list(trade_score.notes)
    notes.append("legacy report wrapper lacks structured market data proof; judgment forced to no clear edge")
    notes.extend(missing_data)
    return replace(
        trade_score,
        label="no clear edge",
        score=0,
        stability="unstable",
        expected_value=None,
        win_probability=None,
        max_reasonable_gain=None,
        max_reasonable_loss=None,
        capital_required=None,
        return_on_capital=None,
        notes=_ordered_unique(notes),
    )
