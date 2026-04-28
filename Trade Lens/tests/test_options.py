import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tradelens.calculations.options import (
    cash_secured_put_breakeven,
    cash_secured_put_max_loss,
    covered_call_breakeven,
    covered_call_max_profit,
    distance_to_strike_pct,
    option_intrinsic_value,
    option_moneyness,
    short_call_assignment_risk,
)


class OptionsTest(unittest.TestCase):
    def test_option_intrinsic_value(self):
        self.assertEqual(option_intrinsic_value(120, 100, "call"), 20)
        self.assertEqual(option_intrinsic_value(80, 100, "put"), 20)
        self.assertEqual(option_intrinsic_value(100, 120, "call"), 0)

    def test_option_moneyness_for_call_and_put(self):
        self.assertEqual(option_moneyness(130, 100, "call"), "ITM")
        self.assertEqual(option_moneyness(70, 100, "call"), "OTM")
        self.assertEqual(option_moneyness(70, 100, "put"), "ITM")
        self.assertEqual(option_moneyness(130, 100, "put"), "OTM")

    def test_distance_to_strike_pct(self):
        self.assertAlmostEqual(distance_to_strike_pct(100, 110), 0.10)
        self.assertAlmostEqual(distance_to_strike_pct(100, 90), -0.10)

    def test_strategy_helpers(self):
        self.assertEqual(covered_call_breakeven(200, 5), 195)
        self.assertEqual(covered_call_max_profit(200, 220, 5), 2500)
        self.assertEqual(cash_secured_put_breakeven(100, 4), 96)
        self.assertEqual(cash_secured_put_max_loss(100, 4), 9600)

    def test_short_call_assignment_risk(self):
        self.assertEqual(short_call_assignment_risk(110, 100, 3), "high")
        self.assertEqual(short_call_assignment_risk(80, 100, 30), "normal")


if __name__ == "__main__":
    unittest.main()

