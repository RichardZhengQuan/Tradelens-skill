"""Deterministic term-aware trade scoring."""

from __future__ import annotations

from typing import Iterable, List, Optional

from tradelens.calculations.scoring import clamp, label_trade_score
from tradelens.models import TermScore, TradeIntent, TradeTerm


DEFAULT_TERMS = [
    TradeTerm.INTRADAY,
    TradeTerm.SHORT_TERM,
    TradeTerm.MEDIUM_TERM,
    TradeTerm.LONG_TERM,
]


def classify_term_label(score: float, unstable: bool = False) -> str:
    return label_trade_score(score, unstable=unstable)


def _is_yes(value: str) -> bool:
    return value.strip().lower() == "yes"


def _is_no(value: str) -> bool:
    return value.strip().lower() == "no"


def _strategy_contains(strategy_type: str, terms: Iterable[str]) -> bool:
    normalized = strategy_type.lower()
    return any(term in normalized for term in terms)


def adjust_score_by_term(
    base_score: float,
    term: TradeTerm,
    intent: Optional[TradeIntent] = None,
    strategy_type: str = "unknown",
    data_is_weak: bool = False,
) -> TermScore:
    intent = intent or TradeIntent()
    adjustment = 0.0
    reasons: List[str] = []
    risks: List[str] = []

    caps_upside = _strategy_contains(strategy_type, ["covered call", "pmcc", "short call", "roll"])
    csp = _strategy_contains(strategy_type, ["cash-secured put", "cash secured put", "csp"])
    leaps = _strategy_contains(strategy_type, ["leaps", "long call", "long put"])
    short_vol = _strategy_contains(strategy_type, ["short volatility", "strangle", "iron condor", "short put", "short call"])

    if caps_upside:
        if term == TradeTerm.SHORT_TERM:
            adjustment += 6
            reasons.append("short-term income structure can be useful")
        if term == TradeTerm.MEDIUM_TERM:
            adjustment -= 8
            risks.append("may cap upside beyond the immediate income window")
        if term == TradeTerm.LONG_TERM:
            adjustment -= 28
            risks.append("may cap long-term upside and damage core exposure")
        if _is_yes(intent.must_preserve_long_term_position) or _is_no(intent.willing_to_cap_upside):
            if term in {TradeTerm.MEDIUM_TERM, TradeTerm.LONG_TERM}:
                adjustment -= 12
                risks.append("conflicts with preserving long-term core position")

    if csp:
        if _is_no(intent.willing_to_accept_assignment):
            adjustment -= 18
            risks.append("assignment does not fit stated intent")
        elif _is_yes(intent.willing_to_accept_assignment) and term in {TradeTerm.MEDIUM_TERM, TradeTerm.LONG_TERM}:
            adjustment += 4
            reasons.append("assignment can fit a longer-term accumulation plan")

    if leaps:
        if term in {TradeTerm.INTRADAY, TradeTerm.SHORT_TERM}:
            adjustment -= 18
            risks.append("LEAPS structure is usually inefficient for very short terms")
        if term == TradeTerm.LONG_TERM:
            adjustment += 6
            reasons.append("LEAPS structure can fit a longer-term directional thesis")

    if short_vol:
        if term == TradeTerm.INTRADAY:
            adjustment -= 10
            risks.append("short volatility may be too compressed for intraday risk")
        if term == TradeTerm.SHORT_TERM:
            adjustment += 3
            reasons.append("short volatility can benefit from near-term decay")

    if term == intent.intended_term:
        adjustment += 3
        reasons.append("matches user's intended term")

    if data_is_weak:
        adjustment -= 8
        risks.append("term score weakened by missing or low-confidence data")

    score = clamp(base_score + adjustment, 0, 100)
    unstable = data_is_weak and term == intent.intended_term
    label = classify_term_label(score, unstable=unstable)
    return TermScore(
        term=term,
        score=score,
        label=label,
        reason="; ".join(reasons) if reasons else "no term-specific edge identified",
        main_risk="; ".join(risks) if risks else "standard trade risk",
        is_intended_term=term == intent.intended_term,
    )


def calculate_term_scores(
    base_score: float,
    intent: Optional[TradeIntent] = None,
    strategy_type: str = "unknown",
    data_is_weak: bool = False,
) -> List[TermScore]:
    intent = intent or TradeIntent()
    terms = list(DEFAULT_TERMS)
    if intent.intended_term == TradeTerm.CUSTOM:
        terms.append(TradeTerm.CUSTOM)
    return [
        adjust_score_by_term(
            base_score=base_score,
            term=term,
            intent=intent,
            strategy_type=strategy_type,
            data_is_weak=data_is_weak,
        )
        for term in terms
    ]

