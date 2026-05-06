import sys
import tempfile
import time
import unittest
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tradelens.analysis.engine import AnalysisEngine
from tradelens.analysis.report_writer import write_analysis_report
from tradelens.data.capability_planner import build_capability_plan
from tradelens.data.market_snapshot import (
    IndexContextSnapshot,
    OptionChainSnapshot,
    OptionContractSnapshot,
    ProviderStatus,
    QuoteSnapshot,
    VolatilitySnapshot,
)
from tradelens.data.provider_base import (
    CAP_ACCOUNT_SUMMARY,
    CAP_FEAR_GREED,
    CAP_INDEX_CONTEXT,
    CAP_NEWS,
    CAP_OPTION_CHAIN,
    CAP_OPTION_OPEN_INTEREST,
    CAP_POSITIONS,
    CAP_QUOTE,
    CAP_UVIX,
)
from tradelens.data.provider_resolver import ProviderResolver
from tradelens.data.providers.futu_opend_provider import FutuOpenDProvider
from tradelens.data.providers.yahoo_provider import YahooProvider
from tradelens.models import Scenario


SCENARIOS = [
    Scenario("base", 0.77, 800),
    Scenario("downside", 0.13, -200),
    Scenario("worst", 0.10, -300),
]


class CountingProvider:
    name = "CountingProvider"

    def __init__(self):
        self.calls = Counter()

    def capabilities(self):
        return {CAP_QUOTE, CAP_OPTION_CHAIN, CAP_NEWS, CAP_FEAR_GREED, CAP_INDEX_CONTEXT, CAP_UVIX}

    def supports(self, capability):
        return capability in self.capabilities()

    def get_quote(self, symbol):
        self.calls[CAP_QUOTE] += 1
        quote = QuoteSnapshot(
            symbol=symbol.upper(),
            price=100,
            provider_name=self.name,
            fetched_at=datetime.now(timezone.utc),
            data_time=datetime.now(timezone.utc),
            data_quality="high",
        )
        return quote, ProviderStatus(self.name, CAP_QUOTE, True, "found", data_quality="high")

    def get_option_chain(self, symbol, expiry=None):
        self.calls[CAP_OPTION_CHAIN] += 1
        chain = OptionChainSnapshot(
            underlying_symbol=symbol.upper(),
            expiry=expiry,
            contracts=[
                OptionContractSnapshot(
                    symbol=f"{symbol.upper()}-TEST",
                    underlying_symbol=symbol.upper(),
                    option_type="put",
                    strike=200,
                    expiry=expiry or "2026-05-01",
                    mark=1.0,
                    provider_name=self.name,
                    data_quality="medium",
                )
            ],
            provider_name=self.name,
            data_quality="medium",
        )
        return chain, ProviderStatus(self.name, CAP_OPTION_CHAIN, True, "found", data_quality="medium")

    def get_news(self, symbol):
        self.calls[CAP_NEWS] += 1
        return None, ProviderStatus(self.name, CAP_NEWS, False, "missing", missing_fields=["newest company news"])

    def get_volatility(self):
        self.calls[CAP_FEAR_GREED] += 1
        snapshot = VolatilitySnapshot(fear_greed=50, provider_name=self.name, data_quality="medium")
        return snapshot, ProviderStatus(self.name, CAP_FEAR_GREED, True, "found", data_quality="medium")

    def get_index_context(self):
        self.calls[CAP_INDEX_CONTEXT] += 1
        return None, ProviderStatus(self.name, CAP_INDEX_CONTEXT, False, "missing")


class FakeYahooProvider(YahooProvider):
    def __init__(self, sleep_seconds=0.0):
        super().__init__(enabled=True, allow_fetch=True, timeout_seconds=0.01)
        self.calls = Counter()
        self.sleep_seconds = sleep_seconds

    def _fetch_quote(self, symbol):
        self.calls[symbol.upper()] += 1
        if self.sleep_seconds:
            time.sleep(self.sleep_seconds)
        return QuoteSnapshot(
            symbol=symbol.upper(),
            price=100,
            provider_name=self.name,
            fetched_at=datetime.now(timezone.utc),
            data_time=datetime.now(timezone.utc),
            data_quality="medium",
        )


class CountingAssetProvider:
    name = "CountingAssetProvider"

    def __init__(self):
        self.calls = Counter()

    def capabilities(self):
        return {CAP_ACCOUNT_SUMMARY, CAP_POSITIONS}

    def supports(self, capability):
        return capability in self.capabilities()

    def get_account_summary(self):
        self.calls[CAP_ACCOUNT_SUMMARY] += 1
        return (
            {"total_assets": 75098.01, "cash": 26127.43, "buying_power": 26127.43},
            ProviderStatus(self.name, CAP_ACCOUNT_SUMMARY, True, "found", data_quality="high"),
        )

    def get_positions(self):
        self.calls[CAP_POSITIONS] += 1
        return (
            [{"symbol": "SGOV", "quantity": 488, "market_value": 49122.08}],
            ProviderStatus(self.name, CAP_POSITIONS, True, "found", data_quality="high"),
        )


class AccountOnlyAssetProvider:
    name = "AccountOnlyAssetProvider"

    def __init__(self):
        self.calls = Counter()

    def capabilities(self):
        return {CAP_ACCOUNT_SUMMARY}

    def supports(self, capability):
        return capability in self.capabilities()

    def get_account_summary(self):
        self.calls[CAP_ACCOUNT_SUMMARY] += 1
        return (
            {"total_assets": 75098.01, "cash": 26127.43},
            ProviderStatus(self.name, CAP_ACCOUNT_SUMMARY, True, "found", data_quality="high"),
        )


class SmartFetchPlanTest(unittest.TestCase):
    def test_history_commands_fetch_no_market_data(self):
        plan = build_capability_plan("history")

        self.assertEqual(plan.required, set())
        self.assertIn(CAP_QUOTE, plan.skipped)
        self.assertEqual(plan.reason_by_capability[CAP_QUOTE], "not required for history command")

    def test_provider_setup_fetches_no_market_data(self):
        plan = build_capability_plan("provider setup")

        self.assertEqual(plan.required, set())
        self.assertIn(CAP_QUOTE, plan.skipped)

    def test_provider_test_uses_only_quote(self):
        plan = build_capability_plan("provider test")

        self.assertEqual(plan.required, {CAP_QUOTE})
        self.assertIn(CAP_NEWS, plan.skipped)

    def test_stock_only_trade_requires_quote_and_skips_options_news_fear_by_default(self):
        plan = build_capability_plan("trade", instrument_type="stock")

        self.assertEqual(plan.required, {CAP_QUOTE})
        self.assertIn(CAP_OPTION_CHAIN, plan.skipped)
        self.assertIn(CAP_NEWS, plan.skipped)
        self.assertIn(CAP_FEAR_GREED, plan.skipped)

    def test_option_trade_requires_quote_and_relevant_option_data(self):
        plan = build_capability_plan("trade", instrument_type="option", has_option_legs=True)

        self.assertIn(CAP_QUOTE, plan.required)
        self.assertIn(CAP_OPTION_CHAIN, plan.required)
        self.assertIn(CAP_OPTION_OPEN_INTEREST, plan.optional)

    def test_explicit_context_requests_are_included(self):
        plan = build_capability_plan(
            "trade",
            instrument_type="stock",
            user_explicitly_requested={CAP_NEWS, CAP_FEAR_GREED},
        )

        self.assertIn(CAP_NEWS, plan.required)
        self.assertIn(CAP_FEAR_GREED, plan.required)

    def test_assets_check_requires_account_and_position_provider_refresh(self):
        plan = build_capability_plan("assets")

        self.assertIn(CAP_ACCOUNT_SUMMARY, plan.required)
        self.assertIn(CAP_POSITIONS, plan.required)
        self.assertNotIn(CAP_QUOTE, plan.required)

    def test_assets_check_does_not_add_quote_refresh_even_when_requested(self):
        plan = build_capability_plan("assets", user_explicitly_requested={CAP_QUOTE})

        self.assertIn(CAP_ACCOUNT_SUMMARY, plan.required)
        self.assertIn(CAP_POSITIONS, plan.required)
        self.assertNotIn(CAP_QUOTE, plan.required)
        self.assertIn(CAP_QUOTE, plan.skipped)


class SmartFetchResolverTest(unittest.TestCase):
    def test_stock_only_trade_fetches_quote_not_options_news_or_fear_by_default(self):
        provider = CountingProvider()
        resolver = ProviderResolver(configured_providers=[provider])

        AnalysisEngine(resolver).analyze_trade(
            symbol="NVDA",
            question="@buy nvda now, 100 stocks",
            scenarios=SCENARIOS,
            max_data_age_minutes=15,
        )

        self.assertEqual(provider.calls[CAP_QUOTE], 1)
        self.assertEqual(provider.calls[CAP_OPTION_CHAIN], 0)
        self.assertEqual(provider.calls[CAP_NEWS], 0)
        self.assertEqual(provider.calls[CAP_FEAR_GREED], 0)

    def test_option_trade_fetches_quote_and_relevant_option_data(self):
        provider = CountingProvider()
        resolver = ProviderResolver(configured_providers=[provider])

        AnalysisEngine(resolver).analyze_trade(
            symbol="NVDA",
            question="Evaluate NVDA put",
            scenarios=SCENARIOS,
            option_expiry="2026-05-01",
            option_strike=200,
            option_type="put",
            max_data_age_minutes=15,
        )

        self.assertEqual(provider.calls[CAP_QUOTE], 1)
        self.assertEqual(provider.calls[CAP_OPTION_CHAIN], 1)
        self.assertEqual(provider.calls[CAP_NEWS], 0)

    def test_user_request_check_news_includes_news(self):
        provider = CountingProvider()
        resolver = ProviderResolver(configured_providers=[provider])

        AnalysisEngine(resolver).analyze_trade(
            symbol="NVDA",
            question="Evaluate NVDA stock and check news",
            scenarios=SCENARIOS,
            max_data_age_minutes=15,
        )

        self.assertEqual(provider.calls[CAP_NEWS], 1)

    def test_user_request_check_fear_greed_includes_fear_greed(self):
        provider = CountingProvider()
        resolver = ProviderResolver(configured_providers=[provider])

        AnalysisEngine(resolver).analyze_trade(
            symbol="NVDA",
            question="Evaluate NVDA stock and check Fear & Greed",
            scenarios=SCENARIOS,
            max_data_age_minutes=15,
        )

        self.assertEqual(provider.calls[CAP_FEAR_GREED], 1)

    def test_report_explains_skipped_data_without_modes(self):
        provider = CountingProvider()
        result = AnalysisEngine(ProviderResolver(configured_providers=[provider])).analyze_trade(
            symbol="NVDA",
            question="@buy nvda now, 100 stocks",
            scenarios=SCENARIOS,
            max_data_age_minutes=15,
        )
        report = write_analysis_report(result).lower()

        self.assertIn("smart fetch", report)
        self.assertIn("not required", report)
        self.assertNotIn("quick mode", report)
        self.assertNotIn("balanced mode", report)
        self.assertNotIn("deep mode", report)

    def test_assets_check_attempts_account_and_position_provider_before_local_fallback(self):
        provider = CountingAssetProvider()
        resolver = ProviderResolver(configured_providers=[provider])

        bundle = resolver.resolve_market_data("ACCOUNT", command="assets")

        self.assertEqual(provider.calls[CAP_ACCOUNT_SUMMARY], 1)
        self.assertEqual(provider.calls[CAP_POSITIONS], 1)
        self.assertEqual(bundle.account_summary["total_assets"], 75098.01)
        self.assertEqual(bundle.positions[0]["symbol"], "SGOV")
        self.assertEqual(bundle.asset_data_source_mode, "provider")

    def test_asset_provider_snapshot_is_persisted_to_assets_md(self):
        provider = CountingAssetProvider()
        with tempfile.TemporaryDirectory() as tmp:
            assets_path = Path(tmp) / "assets.md"
            resolver = ProviderResolver(configured_providers=[provider], assets_path=assets_path)

            resolver.resolve_market_data("ACCOUNT", command="assets")

            text = assets_path.read_text(encoding="utf-8")

        self.assertIn("## Provider Asset Snapshots", text)
        self.assertIn("- account_summary_source: CountingAssetProvider", text)
        self.assertIn('"total_assets": 75098.01', text)
        self.assertIn('"symbol": "SGOV"', text)

    def test_partial_asset_provider_data_is_not_used_or_persisted(self):
        provider = AccountOnlyAssetProvider()
        with tempfile.TemporaryDirectory() as tmp:
            assets_path = Path(tmp) / "assets.md"
            resolver = ProviderResolver(configured_providers=[provider], assets_path=assets_path)

            bundle = resolver.resolve_market_data("ACCOUNT", command="assets")

        self.assertEqual(provider.calls[CAP_ACCOUNT_SUMMARY], 1)
        self.assertIsNone(bundle.account_summary)
        self.assertIsNone(bundle.positions)
        self.assertEqual(bundle.asset_data_source_mode, "local_fallback")
        self.assertFalse(assets_path.exists())

    def test_assets_command_discards_quote_only_refresh_to_avoid_mixing_with_local_assets(self):
        provider = CountingProvider()
        with tempfile.TemporaryDirectory() as tmp:
            market_data_path = Path(tmp) / "market_data.md"
            resolver = ProviderResolver(configured_providers=[provider], market_data_path=market_data_path)

            bundle = resolver.resolve_market_data(
                "SGOV",
                command="assets",
                required_capabilities=[CAP_QUOTE],
            )

        self.assertEqual(provider.calls[CAP_QUOTE], 1)
        self.assertIsNone(bundle.quote)
        self.assertEqual(bundle.asset_data_source_mode, "local_fallback")
        self.assertFalse(market_data_path.exists())

    def test_provider_quote_is_persisted_to_market_data_md(self):
        provider = CountingProvider()
        with tempfile.TemporaryDirectory() as tmp:
            market_data_path = Path(tmp) / "market_data.md"
            resolver = ProviderResolver(configured_providers=[provider], market_data_path=market_data_path)

            resolver.resolve_market_data("NVDA", required_capabilities=[CAP_QUOTE])

            text = market_data_path.read_text(encoding="utf-8")

        self.assertIn("## Provider Market Data Snapshots", text)
        self.assertIn("- symbol: NVDA", text)
        self.assertIn("- source: CountingProvider", text)
        self.assertIn("- price: 100", text)

    def test_local_market_data_snapshot_is_used_when_realtime_is_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp:
            market_data_path = Path(tmp) / "market_data.md"
            market_data_path.write_text(
                """# Market Data Settings

## Provider Market Data Snapshots

### Snapshot 2026-04-29T00:00:00+00:00 - NVDA

- symbol: NVDA
- fetched_at: 2026-04-29T00:00:00+00:00
- classified_data_quality: medium
- missing_data: none

#### Quote
- source: FutuOpenDProvider
- price: 123.45
- session: regular
- quote_timestamp: 2026-04-29T00:00:00+00:00
- data_quality: medium
""",
                encoding="utf-8",
            )
            resolver = ProviderResolver(market_data_path=market_data_path)

            bundle = resolver.resolve_market_data("NVDA", required_capabilities=[CAP_QUOTE])

        self.assertIsNotNone(bundle.quote)
        self.assertEqual(bundle.quote.price, 123.45)
        self.assertEqual(bundle.quote.provider_name, "manual")


class SpeedBehaviorTest(unittest.TestCase):
    def test_yahoo_shared_symbols_are_cached_per_run(self):
        provider = FakeYahooProvider()
        resolver = ProviderResolver(configured_providers=[provider])

        resolver.resolve_market_data("SPY", required_capabilities=[CAP_QUOTE, CAP_INDEX_CONTEXT])

        self.assertEqual(provider.calls["SPY"], 1)
        self.assertEqual(provider.calls["QQQ"], 1)
        self.assertEqual(provider.calls["SOXX"], 1)

    def test_public_index_fetches_are_parallelized_where_safe(self):
        provider = FakeYahooProvider(sleep_seconds=0.1)
        start = time.monotonic()

        context, status = provider.get_index_context()

        elapsed = time.monotonic() - start
        self.assertTrue(status.available)
        self.assertIsNotNone(context)
        self.assertLess(elapsed, 0.25)

    def test_opend_unreachable_preflight_is_checked_once_per_run(self):
        provider = FutuOpenDProvider(enabled=True)
        resolver = ProviderResolver(configured_providers=[provider])

        with patch("tradelens.data.providers.opend_base_provider.importlib.util.find_spec", return_value=object()) as find_spec:
            with patch("tradelens.data.providers.opend_base_provider.socket.create_connection", side_effect=OSError) as create_connection:
                resolver.resolve_market_data(
                    "NVDA",
                    required_capabilities=[CAP_QUOTE, CAP_OPTION_CHAIN, CAP_UVIX],
                    expiry="2026-05-01",
                )

        self.assertEqual(find_spec.call_count, 1)
        self.assertEqual(create_connection.call_count, 1)


if __name__ == "__main__":
    unittest.main()
