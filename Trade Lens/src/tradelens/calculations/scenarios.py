"""Scenario validation, win probability, and expected-value helpers."""

from __future__ import annotations

from dataclasses import replace
from typing import Iterable, List, Optional, Tuple

from tradelens.models import Scenario, ScenarioValidationResult


def validate_scenarios(scenarios: Iterable[Scenario], tolerance: float = 0.02) -> ScenarioValidationResult:
    scenario_list = list(scenarios)
    if not scenario_list:
        return ScenarioValidationResult(
            is_valid=False,
            probability_sum=None,
            normalized_scenarios=[],
            error_message="at least one scenario is required",
            scenario_confidence="low",
        )

    missing = describe_scenario_missing_data(scenario_list)
    if missing:
        return ScenarioValidationResult(
            is_valid=False,
            probability_sum=None,
            normalized_scenarios=[],
            error_message=missing[0],
            scenario_confidence="low",
        )

    probabilities = []
    for scenario in scenario_list:
        if scenario.probability < 0 or scenario.probability > 1:
            return ScenarioValidationResult(
                is_valid=False,
                probability_sum=None,
                normalized_scenarios=[],
                error_message=f"scenario {scenario.name!r} probability must be between 0 and 1",
                scenario_confidence="low",
            )
        probabilities.append(scenario.probability)

    total = sum(probabilities)
    if abs(total - 1.0) <= tolerance:
        return ScenarioValidationResult(
            is_valid=True,
            probability_sum=total,
            normalized_scenarios=scenario_list,
            scenario_confidence="normal",
        )

    if 0.90 <= total <= 1.10:
        confidence = "medium-low" if abs(total - 1.0) <= 0.0500001 else "low"
        normalized = [
            replace(
                scenario,
                probability=scenario.probability / total,  # type: ignore[operator]
                estimate_label=f"{confidence} confidence normalized scenario estimate",
            )
            for scenario in scenario_list
        ]
        return ScenarioValidationResult(
            is_valid=True,
            probability_sum=total,
            warnings=[
                f"scenario probabilities sum to {total:.4f}; normalized to 1.0000",
                f"scenario confidence marked {confidence}",
            ],
            normalized_scenarios=normalized,
            scenario_confidence=confidence,
        )

    return ScenarioValidationResult(
        is_valid=False,
        probability_sum=total,
        normalized_scenarios=[],
        error_message=(
            f"scenario probabilities sum to {total:.4f}, outside recoverable range 0.9000 to 1.1000"
        ),
        scenario_confidence="low",
    )


def describe_scenario_missing_data(scenarios: Iterable[Scenario]) -> List[str]:
    scenario_list = list(scenarios)
    if not scenario_list:
        return ["scenario data: at least one scenario is required"]

    missing: List[str] = []
    for scenario in scenario_list:
        name = scenario.name or "unnamed"
        if scenario.probability is None:
            missing.append(f"scenario {name!r} probability")
        if scenario.profit_loss is None:
            missing.append(f"scenario {name!r} profit/loss")
    return missing


def scenarios_are_complete(scenarios: Iterable[Scenario]) -> bool:
    return not describe_scenario_missing_data(scenarios)


def calculate_expected_value(scenarios: Iterable[Scenario]) -> Optional[float]:
    scenario_list = list(scenarios)
    if describe_scenario_missing_data(scenario_list):
        return None
    validation = validate_scenarios(scenario_list)
    if not validation.is_valid:
        return None
    scenario_list = validation.normalized_scenarios
    return sum(s.probability * s.profit_loss for s in scenario_list)  # type: ignore[operator]


def calculate_win_probability(scenarios: Iterable[Scenario]) -> Optional[float]:
    scenario_list = list(scenarios)
    if describe_scenario_missing_data(scenario_list):
        return None
    validation = validate_scenarios(scenario_list)
    if not validation.is_valid:
        return None
    scenario_list = validation.normalized_scenarios
    return sum(s.probability for s in scenario_list if (s.profit_loss or 0) > 0)  # type: ignore[operator]


def calculate_expected_value_or_none(scenarios: Iterable[Scenario]) -> Optional[float]:
    return calculate_expected_value(scenarios)


def calculate_win_probability_or_none(scenarios: Iterable[Scenario]) -> Optional[float]:
    return calculate_win_probability(scenarios)


def reasonable_gain_loss(scenarios: Iterable[Scenario]) -> Tuple[Optional[float], Optional[float]]:
    values = [s.profit_loss for s in scenarios if s.profit_loss is not None]
    if not values:
        return None, None
    return max(values), min(values)


# Backward-compatible wrapper from the first skeleton.
def expected_value(scenarios: Iterable[Scenario]) -> Optional[float]:
    return calculate_expected_value_or_none(scenarios)
