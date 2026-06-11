"""Smart Fetch capability planning for market-data requests."""

from __future__ import annotations

from dataclasses import dataclass, field

from tradelens.data.provider_base import (
    CAP_ACCOUNT_SUMMARY,
    CAP_FEAR_GREED,
    CAP_INDEX_CONTEXT,
    CAP_NEWS,
    CAP_OPTION_CHAIN,
    CAP_OPTION_CONTRACT,
    CAP_OPTION_GREEKS,
    CAP_OPTION_IV,
    CAP_OPTION_OPEN_INTEREST,
    CAP_OPTION_VOLUME,
    CAP_POSITIONS,
    CAP_QUOTE,
    CAP_UVIX,
    CAP_VIX,
)

CAP_LOCAL_CONTEXT = "local_context"

ALL_MARKET_CAPABILITIES = {
    CAP_QUOTE,
    CAP_OPTION_CHAIN,
    CAP_OPTION_CONTRACT,
    CAP_OPTION_OPEN_INTEREST,
    CAP_OPTION_VOLUME,
    CAP_OPTION_GREEKS,
    CAP_OPTION_IV,
    CAP_NEWS,
    CAP_FEAR_GREED,
    CAP_VIX,
    CAP_UVIX,
    CAP_INDEX_CONTEXT,
    CAP_POSITIONS,
    CAP_ACCOUNT_SUMMARY,
}

OPTION_CAPABILITIES = {
    CAP_OPTION_CHAIN,
    CAP_OPTION_CONTRACT,
    CAP_OPTION_OPEN_INTEREST,
    CAP_OPTION_VOLUME,
    CAP_OPTION_GREEKS,
    CAP_OPTION_IV,
}


@dataclass(frozen=True)
class CapabilityPlan:
    required: set[str] = field(default_factory=set)
    optional: set[str] = field(default_factory=set)
    skipped: set[str] = field(default_factory=set)
    reason_by_capability: dict[str, str] = field(default_factory=dict)


def build_capability_plan(
    command: str,
    instrument_type: str | None = None,
    strategy_type: str | None = None,
    has_option_legs: bool = False,
    user_explicitly_requested: set[str] | None = None,
) -> CapabilityPlan:
    command_key = _normalize(command)
    instrument = _normalize(instrument_type or "")
    strategy = _normalize(strategy_type or "")
    explicit = {_normalize_capability(capability) for capability in (user_explicitly_requested or set())}
    required: set[str] = set()
    optional: set[str] = set()
    reasons: dict[str, str] = {}

    if _is_history_command(command_key):
        return _skip_all("not required for history command")

    if command_key in {"provider setup", "provider_setup", "setup"}:
        return _skip_all("not required for provider setup command")

    if command_key in {"provider test", "provider_test", "test"}:
        required.add(CAP_QUOTE)
        reasons[CAP_QUOTE] = "test quote requested for provider test command"
        return _final_plan(required, optional, reasons, default_skip_reason="not required for provider test command")

    if command_key in {"assets", "asset"}:
        required.update({CAP_ACCOUNT_SUMMARY, CAP_POSITIONS})
        reasons[CAP_ACCOUNT_SUMMARY] = "required for assets check provider account refresh"
        reasons[CAP_POSITIONS] = "required for assets check provider position refresh"
        return _final_plan(required, optional, reasons, default_skip_reason="not required for assets command")

    option_trade = has_option_legs or instrument in {"option", "options"} or _strategy_has_options(strategy)
    stock_only = instrument in {"stock", "stocks", "equity", "shares"} and not option_trade

    if option_trade:
        required.add(CAP_QUOTE)
        reasons[CAP_QUOTE] = "required for option trade underlying context"
        required.add(CAP_OPTION_CHAIN)
        reasons[CAP_OPTION_CHAIN] = "required for option trade when expiry/strike context is known or needed"
        optional.update({CAP_OPTION_OPEN_INTEREST, CAP_OPTION_GREEKS, CAP_OPTION_IV, CAP_VIX, CAP_UVIX, CAP_INDEX_CONTEXT})
        reasons.update(
            {
                CAP_OPTION_OPEN_INTEREST: "optional option context, fetched only when requested or cheap/cached",
                CAP_OPTION_GREEKS: "optional option context, fetched only when requested or cheap/cached",
                CAP_OPTION_IV: "optional option context, fetched only when requested or cheap/cached",
                CAP_VIX: "optional volatility context, fetched only when requested or cheap/cached",
                CAP_UVIX: "optional volatility context, fetched only when requested or cheap/cached",
                CAP_INDEX_CONTEXT: "optional index context, fetched only when requested or cheap/cached",
            }
        )
    elif stock_only or command_key in {"trade", "/trade", "tradelens trade"}:
        required.add(CAP_QUOTE)
        reasons[CAP_QUOTE] = "required for stock-only trade price context"
        optional.add(CAP_INDEX_CONTEXT)
        reasons[CAP_INDEX_CONTEXT] = "optional only if cheap/cached or directly relevant"

    for capability in explicit:
        mapped = _normalize_capability(capability)
        if mapped in ALL_MARKET_CAPABILITIES:
            required.add(mapped)
            reasons[mapped] = "explicitly requested by user"

    if CAP_OPTION_CONTRACT in required:
        required.add(CAP_OPTION_CHAIN)
        reasons.setdefault(CAP_OPTION_CHAIN, "required to locate requested option contract")

    if CAP_OPTION_OPEN_INTEREST in required or CAP_OPTION_GREEKS in required or CAP_OPTION_IV in required:
        required.add(CAP_OPTION_CHAIN)
        reasons.setdefault(CAP_OPTION_CHAIN, "required for requested option-chain detail")

    return _final_plan(required, optional - required, reasons, default_skip_reason="not requested")


def _final_plan(
    required: set[str],
    optional: set[str],
    reasons: dict[str, str],
    default_skip_reason: str,
) -> CapabilityPlan:
    skipped = ALL_MARKET_CAPABILITIES - required - optional
    reason_by_capability = dict(reasons)
    for capability in skipped:
        reason_by_capability.setdefault(capability, default_skip_reason)
    return CapabilityPlan(required=required, optional=optional, skipped=skipped, reason_by_capability=reason_by_capability)


def _skip_all(reason: str) -> CapabilityPlan:
    return CapabilityPlan(
        required=set(),
        optional=set(),
        skipped=set(ALL_MARKET_CAPABILITIES),
        reason_by_capability={capability: reason for capability in ALL_MARKET_CAPABILITIES},
    )


def _normalize(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace("/", "").replace("_", " ")


def _normalize_capability(value: str) -> str:
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "oi": CAP_OPTION_OPEN_INTEREST,
        "open_interest": CAP_OPTION_OPEN_INTEREST,
        "option_oi": CAP_OPTION_OPEN_INTEREST,
        "iv": CAP_OPTION_IV,
        "option_iv": CAP_OPTION_IV,
        "greeks": CAP_OPTION_GREEKS,
        "option_greeks": CAP_OPTION_GREEKS,
        "option_data": CAP_OPTION_CHAIN,
        "option_contract": CAP_OPTION_CONTRACT,
        "feargreed": CAP_FEAR_GREED,
        "fear_and_greed": CAP_FEAR_GREED,
        "fear_greed": CAP_FEAR_GREED,
        "earnings": CAP_NEWS,
        "fomc": CAP_NEWS,
        "catalyst": CAP_NEWS,
        "sentiment": CAP_FEAR_GREED,
        "indexes": CAP_INDEX_CONTEXT,
        "indices": CAP_INDEX_CONTEXT,
        "market_context": CAP_INDEX_CONTEXT,
    }
    return aliases.get(normalized, normalized)


def _is_history_command(command: str) -> bool:
    return command in {"history", "history all", "history name", "history feedback", "analysis ratio", "stats"}


def _strategy_has_options(strategy: str) -> bool:
    option_terms = (
        "option",
        "call",
        "put",
        "covered call",
        "cash secured put",
        "csp",
        "pmcc",
        "leaps",
        "spread",
        "calendar",
        "condor",
        "strangle",
        "straddle",
    )
    return any(term in strategy for term in option_terms)
