import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tradelens.calculations.term_scoring import (
    calculate_term_scores,
    classify_term_label,
)
from tradelens.models import TradeIntent, TradeTerm


class TermScoringTest(unittest.TestCase):
    def test_label_mapping(self):
        self.assertEqual(classify_term_label(90), "good")
        self.assertEqual(classify_term_label(82), "good")
        self.assertEqual(classify_term_label(45), "neutral")

    def test_covered_call_can_be_good_short_term_bad_long_term(self):
        intent = TradeIntent(
            intended_term=TradeTerm.SHORT_TERM,
            primary_goal="income",
            must_preserve_long_term_position="yes",
            willing_to_cap_upside="no",
        )
        scores = calculate_term_scores(
            base_score=82,
            intent=intent,
            strategy_type="covered call",
            data_is_weak=False,
        )
        by_term = {score.term: score for score in scores}
        self.assertEqual(by_term[TradeTerm.SHORT_TERM].label, "good")
        self.assertEqual(by_term[TradeTerm.LONG_TERM].label, "mostly bad")
        self.assertTrue(by_term[TradeTerm.SHORT_TERM].is_intended_term)

    def test_weak_data_can_force_no_clear_edge_for_intended_term(self):
        intent = TradeIntent(intended_term=TradeTerm.MEDIUM_TERM)
        scores = calculate_term_scores(
            base_score=80,
            intent=intent,
            strategy_type="short volatility",
            data_is_weak=True,
        )
        intended = [score for score in scores if score.is_intended_term][0]
        self.assertEqual(intended.label, "no clear edge")


if __name__ == "__main__":
    unittest.main()
