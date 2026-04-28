import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tradelens.calculations.scoring import (
    calculate_trade_score,
    label_trade_score,
    score_data_quality,
)
from tradelens.models import Scenario


class ScoringTest(unittest.TestCase):
    def test_score_label_mapping(self):
        self.assertEqual(label_trade_score(100), "good")
        self.assertEqual(label_trade_score(80), "good")
        self.assertEqual(label_trade_score(79), "mostly good")
        self.assertEqual(label_trade_score(65), "mostly good")
        self.assertEqual(label_trade_score(64), "neutral")
        self.assertEqual(label_trade_score(45), "neutral")
        self.assertEqual(label_trade_score(44), "mostly bad")
        self.assertEqual(label_trade_score(25), "mostly bad")
        self.assertEqual(label_trade_score(24), "bad")
        self.assertEqual(label_trade_score(90, unstable=True), "no clear edge")

    def test_data_quality_penalty_reduces_score(self):
        high = score_data_quality("high", missing_data_count=0, stale=False)
        low = score_data_quality("low", missing_data_count=3, stale=True)
        self.assertLess(low, high)

    def test_calculate_trade_score_uses_data_quality_penalty(self):
        scenarios = [
            Scenario("base", 0.77, 800),
            Scenario("downside", 0.13, -200),
            Scenario("worst", 0.10, -300),
        ]
        high_quality = calculate_trade_score(scenarios, data_quality="high", capital_required=10000)
        low_quality = calculate_trade_score(
            scenarios,
            data_quality="low",
            missing_data_count=3,
            capital_required=10000,
            stale_data=True,
        )
        self.assertLess(low_quality.score, high_quality.score)
        self.assertEqual(high_quality.expected_value, 560)
        self.assertEqual(high_quality.win_probability, 0.77)


if __name__ == "__main__":
    unittest.main()
