"""Deterministic trade-quality scoring helpers."""

from __future__ import annotations

from dataclasses import replace
from typing import Iterable, Optional

from tradelens.calculations.positions import return_on_capital
from tradelens.calculations.scenarios import (
    calculate_expected_value,
    calculate_win_probability,
    describe_scenario_missing_data,
    reasonable_gain_loss,
    validate_scenarios,
)
from tradelens.models import Scenario, ScoreBreakdown, TradeScore


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def score_reward_risk(expected_value: Optional[float], max_loss: Optional[float], max_gain: Optional[float]) -> float:
    if expected_value is None or max_loss is None or max_gain is None:
        return 5
    if max_loss >= 0:
        return 25 if expected_value > 0 else 10
    reward_risk = max_gain / abs(max_loss) if max_loss else 0
    base = 10 if expected_value > 0 else 3
    return clamp(base + reward_risk * 5, 0, 25)


def score_probability_setup(win_probability: Optional[float], data_quality: str = "medium") -> float:
    if win_probability is None:
        return 4
    quality_factor = {"high": 1.0, "medium": 0.8, "low": 0.55}.get(data_quality, 0.55)
    return clamp(win_probability * 20 * quality_factor, 0, 20)


def score_data_quality(data_quality: str, missing_data_count: int = 0, stale: bool = False) -> float:
    base = {"high": 0, "medium": -5, "low": -12}.get(data_quality, -12)
    missing_penalty = min(missing_data_count * 2, 8)
    stale_penalty = 5 if stale else 0
    return clamp(base - missing_penalty - stale_penalty, -20, 0)


def label_trade_score(score: float, unstable: bool = False) -> str:
    if unstable:
        return "no clear edge"
    if score >= 80:
        return "good"
    if score >= 65:
        return "mostly good"
    if score >= 45:
        return "neutral"
    if score >= 25:
        return "mostly bad"
    return "bad"


def bounded_breakdown(breakdown: ScoreBreakdown) -> ScoreBreakdown:
    return replace(
        breakdown,
        reward_risk=clamp(breakdown.reward_risk, 0, 25),
        probability_setup=clamp(breakdown.probability_setup, 0, 20),
        position_fit=clamp(breakdown.position_fit, 0, 20),
        market_regime=clamp(breakdown.market_regime, 0, 15),
        options_structure=clamp(breakdown.options_structure, 0, 15),
        psychology_rule_fit=clamp(breakdown.psychology_rule_fit, 0, 10),
        data_quality_adjustment=clamp(breakdown.data_quality_adjustment, -20, 0),
    )


def total_score(breakdown: ScoreBreakdown) -> float:
    b = bounded_breakdown(breakdown)
    return clamp(
        b.reward_risk
        + b.probability_setup
        + b.position_fit
        + b.market_regime
        + b.options_structure
        + b.psychology_rule_fit
        + b.data_quality_adjustment,
        0,
        100,
    )


def calculate_trade_score(
    scenarios: Iterable[Scenario],
    data_quality: str = "medium",
    missing_data_count: int = 0,
    capital_required: Optional[float] = None,
    position_fit: float = 10,
    market_regime: float = 8,
    options_structure: float = 8,
    psychology_rule_fit: float = 5,
    stale_data: bool = False,
    unstable: bool = False,
) -> TradeScore:
    scenario_list = list(scenarios)
    missing_scenario_data = describe_scenario_missing_data(scenario_list)
    validation = validate_scenarios(scenario_list) if not missing_scenario_data else None
    validation_notes = []
    if validation:
        validation_notes.extend(validation.warnings)
        if validation.error_message:
            validation_notes.append(validation.error_message)
    if missing_scenario_data or (validation and not validation.is_valid):
        notes = missing_scenario_data + validation_notes
        breakdown = ScoreBreakdown(
            reward_risk=0,
            probability_setup=0,
            position_fit=position_fit,
            market_regime=market_regime,
            options_structure=options_structure,
            psychology_rule_fit=psychology_rule_fit,
            data_quality_adjustment=score_data_quality(
                data_quality,
                missing_data_count + len(missing_scenario_data),
                stale_data,
            ),
        )
        score = total_score(breakdown)
        return TradeScore(
            label="no clear edge",
            score=score,
            stability="unstable",
            breakdown=bounded_breakdown(breakdown),
            scenarios=scenario_list,
            expected_value=None,
            win_probability=None,
            max_reasonable_gain=None,
            max_reasonable_loss=None,
            capital_required=capital_required,
            return_on_capital=None,
            notes=notes,
        )

    scenario_list = validation.normalized_scenarios if validation else scenario_list
    ev = calculate_expected_value(scenario_list)
    win_prob = calculate_win_probability(scenario_list)
    max_gain, max_loss = reasonable_gain_loss(scenario_list)
    breakdown = ScoreBreakdown(
        reward_risk=score_reward_risk(ev, max_loss, max_gain),
        probability_setup=score_probability_setup(win_prob, data_quality=data_quality),
        position_fit=position_fit,
        market_regime=market_regime,
        options_structure=options_structure,
        psychology_rule_fit=psychology_rule_fit,
        data_quality_adjustment=score_data_quality(data_quality, missing_data_count, stale_data),
    )
    score = total_score(breakdown)
    roc = return_on_capital(ev, capital_required) if capital_required else None
    return TradeScore(
        label=label_trade_score(score, unstable=unstable),
        score=score,
        stability="unstable" if unstable else "stable",
        breakdown=bounded_breakdown(breakdown),
        scenarios=scenario_list,
        expected_value=ev,
        win_probability=win_prob,
        max_reasonable_gain=max_gain,
        max_reasonable_loss=max_loss,
        capital_required=capital_required,
        return_on_capital=roc,
        notes=validation_notes,
    )


# Backward-compatible wrappers from the first skeleton.
def score_label(score: float, unstable: bool = False) -> str:
    return label_trade_score(score, unstable=unstable)


def build_trade_score(
    breakdown: ScoreBreakdown,
    scenarios: Iterable[Scenario],
    capital_required: Optional[float] = None,
    unstable: bool = False,
) -> TradeScore:
    scenario_list = list(scenarios)
    missing_scenario_data = describe_scenario_missing_data(scenario_list)
    validation = validate_scenarios(scenario_list) if not missing_scenario_data else None
    validation_notes = []
    if validation:
        validation_notes.extend(validation.warnings)
        if validation.error_message:
            validation_notes.append(validation.error_message)
    if missing_scenario_data or (validation and not validation.is_valid):
        notes = missing_scenario_data + validation_notes
        incomplete_breakdown = replace(
            breakdown,
            reward_risk=0,
            probability_setup=0,
            data_quality_adjustment=-20,
        )
        score = total_score(incomplete_breakdown)
        return TradeScore(
            label="no clear edge",
            score=score,
            stability="unstable",
            breakdown=bounded_breakdown(incomplete_breakdown),
            scenarios=scenario_list,
            expected_value=None,
            win_probability=None,
            max_reasonable_gain=None,
            max_reasonable_loss=None,
            capital_required=capital_required,
            return_on_capital=None,
            notes=notes,
        )

    scenario_list = validation.normalized_scenarios if validation else scenario_list
    ev = calculate_expected_value(scenario_list)
    win_prob = calculate_win_probability(scenario_list)
    max_gain, max_loss = reasonable_gain_loss(scenario_list)
    score = total_score(breakdown)
    roc = return_on_capital(ev, capital_required) if capital_required else None
    return TradeScore(
        label=label_trade_score(score, unstable=unstable),
        score=score,
        stability="unstable" if unstable else "stable",
        breakdown=bounded_breakdown(breakdown),
        scenarios=scenario_list,
        expected_value=ev,
        win_probability=win_prob,
        max_reasonable_gain=max_gain,
        max_reasonable_loss=max_loss,
        capital_required=capital_required,
        return_on_capital=roc,
        notes=validation_notes,
    )
