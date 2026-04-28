import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tradelens.calculations.scenarios import (
    calculate_expected_value,
    calculate_win_probability,
    validate_scenarios,
)
from tradelens.models import Scenario


class ScenariosTest(unittest.TestCase):
    def test_expected_value_requested_case(self):
        scenarios = [
            Scenario("base", 0.77, 800),
            Scenario("downside", 0.13, -200),
            Scenario("worst", 0.10, -300),
        ]
        self.assertEqual(calculate_expected_value(scenarios), 560)

    def test_win_probability_requested_case(self):
        scenarios = [
            Scenario("base", 0.77, 800),
            Scenario("downside", 0.13, -200),
            Scenario("worst", 0.10, -300),
        ]
        self.assertEqual(calculate_win_probability(scenarios), 0.77)

    def test_expected_value_returns_none_for_missing_probability(self):
        scenarios = [
            Scenario("base", None, 800),
            Scenario("downside", 1.0, -200),
        ]
        self.assertIsNone(calculate_expected_value(scenarios))

    def test_expected_value_returns_none_for_missing_profit_loss(self):
        scenarios = [
            Scenario("base", 0.5, None),
            Scenario("downside", 0.5, -200),
        ]
        self.assertIsNone(calculate_expected_value(scenarios))

    def test_validate_scenarios_returns_invalid_result_for_bad_probability_sum(self):
        result = validate_scenarios(
            [
                Scenario("base", 0.8, 100),
                Scenario("downside", 0.5, -50),
            ]
        )

        self.assertFalse(result.is_valid)
        self.assertEqual(result.probability_sum, 1.3)
        self.assertIn("outside recoverable range", result.error_message)

    def test_validate_scenarios_normalizes_recoverable_probability_sum(self):
        result = validate_scenarios(
            [
                Scenario("base", 0.76, 100),
                Scenario("downside", 0.09, -50),
                Scenario("worst", 0.10, -100),
            ]
        )

        self.assertTrue(result.is_valid)
        self.assertEqual(result.probability_sum, 0.95)
        self.assertAlmostEqual(sum(s.probability for s in result.normalized_scenarios), 1.0)
        self.assertEqual(result.scenario_confidence, "medium-low")


if __name__ == "__main__":
    unittest.main()
