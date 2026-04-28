import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime
from io import StringIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tradelens.cli import main as cli_main
from tradelens.analysis.report_writer import STANDARD_DISCLAIMER
from tradelens.parsers.text_parser import extract_bundle, parse_order_lines
from tradelens.storage.history_store import HistoryStore


class StorageParserTest(unittest.TestCase):
    def test_history_save_does_not_overwrite_same_second_same_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = HistoryStore(Path(tmp))
            created_at = datetime(2026, 4, 27, 12, 0, 0)

            first = store.save("NVDA covered call", "first", created_at)
            second = store.save("NVDA covered call", "second", created_at)

            self.assertNotEqual(first, second)
            self.assertEqual(first.read_text(encoding="utf-8"), "first\n")
            self.assertEqual(second.read_text(encoding="utf-8"), "second\n")

    def test_history_detail_view_includes_standard_disclaimer_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = HistoryStore(Path(tmp))
            created_at = datetime(2026, 4, 27, 12, 0, 0)
            store.save("NVDA covered call", "# **GOOD — Test**\n\nbody", created_at)

            detail = store.detail("covered call")

        self.assertIn(STANDARD_DISCLAIMER, detail)
        self.assertLess(detail.index(STANDARD_DISCLAIMER), detail.index("body"))
        self.assertEqual(detail.count(STANDARD_DISCLAIMER), 1)

    def test_history_cli_detail_view_includes_standard_disclaimer(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = HistoryStore(root / "analysis_history")
            store.save("NVDA covered call", "# **GOOD — Test**\n\nbody", datetime(2026, 4, 27, 12, 0, 0))
            stdout = StringIO()

            with redirect_stdout(stdout):
                exit_code = cli_main(["--root", tmp, "history", "--name", "covered call"])

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn(STANDARD_DISCLAIMER, output)
        self.assertEqual(output.count(STANDARD_DISCLAIMER), 1)

    def test_text_parser_does_not_treat_action_code_as_symbol(self):
        orders = parse_order_lines("BTO 1 NVDA 200C 2026-05-15 @ 4.20")

        self.assertEqual(orders[0].action, "bto")
        self.assertEqual(orders[0].symbol, "NVDA")
        self.assertEqual(orders[0].quantity, 1)

    def test_broker_style_order_patterns_parse_correctly(self):
        cases = [
            (
                "SELL TO OPEN 1 NVDA 20260501 200 PUT @ 3.50",
                "sell to open",
                1,
                "NVDA",
                "20260501",
                200,
                "put",
                3.50,
            ),
            (
                "BUY TO CLOSE 1 NVDA 20260501 200 PUT @ 1.20",
                "buy to close",
                1,
                "NVDA",
                "20260501",
                200,
                "put",
                1.20,
            ),
            (
                "STO 1 NVDA 200P 2026-05-01 @ 3.50",
                "sto",
                1,
                "NVDA",
                "2026-05-01",
                200,
                "put",
                3.50,
            ),
            (
                "BTO 2 NVDA 210C 2026-05-01 @ 4.20",
                "bto",
                2,
                "NVDA",
                "2026-05-01",
                210,
                "call",
                4.20,
            ),
            (
                "Sell 1 NVDA 05/01/2026 200 Put at 3.50",
                "sell",
                1,
                "NVDA",
                "05/01/2026",
                200,
                "put",
                3.50,
            ),
        ]

        for text, action, quantity, symbol, expiry, strike, option_type, price in cases:
            with self.subTest(text=text):
                order = parse_order_lines(text)[0]
                self.assertEqual(order.action, action)
                self.assertEqual(order.quantity, quantity)
                self.assertEqual(order.symbol, symbol)
                self.assertEqual(order.expiry, expiry)
                self.assertEqual(order.strike, strike)
                self.assertEqual(order.option_type, option_type)
                self.assertEqual(order.order_price, price)

    def test_extract_bundle_detects_missing_symbol_after_ignoring_action(self):
        bundle = extract_bundle("SELL 1 CALL")

        self.assertIn("symbol", bundle.missing_data)


if __name__ == "__main__":
    unittest.main()
