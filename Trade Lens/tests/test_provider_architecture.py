import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tradelens.cli import main as cli_main
from tradelens.analysis.engine import AnalysisEngine
from tradelens.analysis.report_writer import write_analysis_report
from tradelens.data.provider_setup import (
    PROVIDER_SETUP_REGISTRY,
    check_provider_setup_status,
    normalize_provider_id,
    render_provider_setup,
)
from tradelens.data.provider_resolver import ProviderResolver
from tradelens.data.providers.cnn_fear_greed_provider import CNNFearGreedProvider
from tradelens.data.providers.finnhub_provider import FinnhubProvider
from tradelens.data.providers.futu_provider import FutuProvider
from tradelens.data.providers.futu_opend_provider import FutuOpenDProvider
from tradelens.data.providers.manual_provider import ManualMarketDataProvider
from tradelens.data.providers.moomoo_opend_provider import MoomooOpenDProvider
from tradelens.data.providers.optioncharts_provider import OptionChartsProvider
from tradelens.data.providers.opend_base_provider import OpenDDetectionResult, OpenDProvider
from tradelens.data.providers.polygon_provider import PolygonProvider
from tradelens.data.providers.tradier_provider import TradierProvider
from tradelens.models import Scenario


SCENARIOS = [
    Scenario("base", 0.77, 800),
    Scenario("downside", 0.13, -200),
    Scenario("worst", 0.10, -300),
]


class ProviderArchitectureTest(unittest.TestCase):
    def test_empty_market_data_md_does_not_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "market_data.md"
            path.write_text("", encoding="utf-8")
            bundle = ProviderResolver(market_data_path=path).resolve_market_data("NVDA")

        self.assertEqual(bundle.symbol, "NVDA")
        self.assertIn("realtime data unavailable", bundle.missing_data)

    def test_no_provider_configured_still_returns_bundle(self):
        bundle = ProviderResolver(config={}).resolve_market_data("NVDA")

        self.assertEqual(bundle.symbol, "NVDA")
        self.assertEqual(bundle.classified_data_quality, "low")
        self.assertIsNone(bundle.quote)

    def test_manual_provider_fallback_always_works_without_fake_price(self):
        quote, status = ManualMarketDataProvider().get_quote("NVDA")

        self.assertIsNone(quote)
        self.assertFalse(status.available)
        self.assertIn("underlying realtime/latest price", status.missing_fields)

    def test_host_public_tool_unavailable_falls_back_cleanly(self):
        bundle = ProviderResolver(allow_public_fetch=False).resolve_market_data("NVDA")

        self.assertIn("YahooProvider", [status.provider_name for status in bundle.provider_statuses])
        self.assertIn("manual", bundle.fallback_path_used)
        self.assertIsNone(bundle.quote)

    def test_readme_says_providers_are_optional(self):
        readme = (Path(__file__).resolve().parents[1] / "README.md").read_text(encoding="utf-8").lower()

        self.assertIn("providers are optional", readme)
        self.assertIn("does not give action advice", readme)

    def test_analysis_runs_with_low_data_quality(self):
        result = AnalysisEngine(ManualMarketDataProvider()).analyze_trade(
            symbol="NVDA",
            question="Evaluate this trade",
            scenarios=SCENARIOS,
            max_data_age_minutes=15,
        )

        self.assertEqual(result.classified_data_quality, "low")
        self.assertEqual(result.trade_judgment, "no clear edge")

    def test_provider_resolver_attempts_futu_when_enabled(self):
        resolver = ProviderResolver(config={"providers": {"futu_opend": {"enabled": True}}})
        bundle = resolver.resolve_market_data("NVDA", required_capabilities=["quote"])

        self.assertIn("FutuOpenDProvider", [status.provider_name for status in bundle.provider_statuses])

    def test_provider_resolver_falls_back_when_futu_unavailable(self):
        resolver = ProviderResolver(config={"providers": {"futu_opend": {"enabled": True}}})
        bundle = resolver.resolve_market_data("NVDA", required_capabilities=["quote"])

        self.assertIn("manual", bundle.fallback_path_used)
        self.assertIsNone(bundle.quote)

    def test_missing_futu_api_package_does_not_crash(self):
        with patch("tradelens.data.providers.opend_base_provider.importlib.util.find_spec", return_value=None):
            quote, status = FutuOpenDProvider(enabled=True).get_quote("NVDA")

        self.assertIsNone(quote)
        self.assertFalse(status.available)
        self.assertEqual(status.error, "futu-api package not installed")

    def test_opend_unreachable_returns_unavailable(self):
        with patch("tradelens.data.providers.opend_base_provider.importlib.util.find_spec", return_value=object()):
            with patch("tradelens.data.providers.opend_base_provider.socket.create_connection", side_effect=OSError):
                quote, status = FutuOpenDProvider(enabled=True).get_quote("NVDA")

        self.assertIsNone(quote)
        self.assertFalse(status.available)
        self.assertEqual(status.error, "Futu OpenD not reachable")

    def test_futu_provider_never_has_password_config(self):
        config = FutuOpenDProvider.default_config()
        provider = FutuOpenDProvider()

        self.assertFalse(config["store_password"])
        self.assertFalse(provider.store_password)
        self.assertNotIn("password", [name for name in provider.__dataclass_fields__ if name != "store_password"])

    def test_futu_and_moomoo_opend_providers_are_separate_classes(self):
        self.assertIsNot(FutuOpenDProvider, MoomooOpenDProvider)
        self.assertIsInstance(FutuOpenDProvider(), OpenDProvider)
        self.assertIsInstance(MoomooOpenDProvider(), OpenDProvider)

    def test_futu_provider_alias_maps_to_futu_opend_provider(self):
        self.assertIs(FutuProvider, FutuOpenDProvider)

    def test_opend_defaults_are_local_read_only_and_no_trading_or_password_storage(self):
        opend_config = OpenDProvider.default_config()
        futu_config = FutuOpenDProvider.default_config()
        moomoo_config = MoomooOpenDProvider.default_config()

        self.assertEqual(opend_config["host"], "127.0.0.1")
        for config in (opend_config, futu_config, moomoo_config):
            self.assertTrue(config["read_only"])
            self.assertFalse(config["allow_trading"])
            self.assertFalse(config["store_password"])

    def test_non_local_opend_host_is_blocked_unless_remote_hosts_allowed(self):
        quote, status = FutuOpenDProvider(enabled=True, host="192.0.2.10").get_quote("NVDA")

        self.assertIsNone(quote)
        self.assertFalse(status.available)
        self.assertEqual(status.error, "Remote OpenD host is disabled by default for account safety.")

        with patch("tradelens.data.providers.opend_base_provider.importlib.util.find_spec", return_value=None):
            quote, status = FutuOpenDProvider(
                enabled=True,
                host="192.0.2.10",
                allow_remote_host=True,
                require_local_opend=False,
            ).get_quote("NVDA")

        self.assertIsNone(quote)
        self.assertNotEqual(status.error, "Remote OpenD host is disabled by default for account safety.")

    def test_provider_setup_never_asks_for_broker_password(self):
        with tempfile.TemporaryDirectory() as tmp:
            stdout = StringIO()
            with redirect_stdout(stdout):
                exit_code = cli_main(["--root", tmp, "provider", "add", "futu-opend"])

        output = stdout.getvalue().lower()
        self.assertEqual(exit_code, 0)
        self.assertIn("no broker password", output)
        self.assertIn("no package was installed", output)
        self.assertNotIn("enter", output)

    def test_ambiguous_opend_add_asks_user_to_choose_futu_or_moomoo(self):
        detection = OpenDDetectionResult(
            selected_provider=None,
            ambiguous=True,
            futu_sdk_installed=True,
            moomoo_sdk_installed=True,
            local_opend_reachable=True,
            reasons=("Both SDK packages are installed.",),
        )
        with tempfile.TemporaryDirectory() as tmp:
            stdout = StringIO()
            with patch("tradelens.cli.detect_opend_provider", return_value=detection):
                with redirect_stdout(stdout):
                    exit_code = cli_main(["--root", tmp, "provider", "add", "opend"])

        output = stdout.getvalue()
        self.assertEqual(exit_code, 2)
        self.assertIn("Choose `/tradelens provider add futu-opend`", output)
        self.assertIn("`/tradelens provider add moomoo-opend`", output)

    def test_report_shows_opend_provider_type(self):
        with patch("tradelens.data.providers.opend_base_provider.importlib.util.find_spec", return_value=None):
            result = AnalysisEngine(FutuOpenDProvider(enabled=True)).analyze_trade(
                symbol="NVDA",
                question="Evaluate this trade",
                scenarios=SCENARIOS,
                max_data_age_minutes=15,
            )
        report = write_analysis_report(result)

        self.assertIn("**OpenD provider status**", report)
        self.assertIn("| Provider type | Futu OpenD |", report)

    def test_api_providers_read_tokens_from_environment_only(self):
        providers = [
            (TradierProvider(enabled=True), "TRADIER_API_KEY"),
            (PolygonProvider(enabled=True), "POLYGON_API_KEY"),
            (FinnhubProvider(enabled=True), "FINNHUB_API_KEY"),
        ]
        for provider, env_name in providers:
            with self.subTest(provider=provider.name):
                with patch.dict(os.environ, {}, clear=True):
                    quote, status = provider.get_quote("NVDA")
                self.assertIsNone(quote)
                self.assertFalse(status.available)
                self.assertIn(env_name, status.error)

    def test_api_keys_are_not_stored_in_market_data_md(self):
        market_data = (Path(__file__).resolve().parents[1] / "market_data.md").read_text(encoding="utf-8")

        self.assertNotRegex(market_data, r"(?i)(api[_ -]?key|token)\s*[:=]\s*[A-Za-z0-9_\-]{12,}")

    def test_public_fallbacks_return_missing_without_exception(self):
        volatility, cnn_status = CNNFearGreedProvider().get_volatility()
        chain, optioncharts_status = OptionChartsProvider().get_option_chain("NVDA", "2026-05-01")

        self.assertIsNone(volatility)
        self.assertEqual(cnn_status.error, "CNN Fear & Greed unavailable or blocked")
        self.assertIsNone(chain)
        self.assertEqual(optioncharts_status.error, "OptionCharts unavailable or unsupported path")

    def test_report_includes_public_source_attempts_and_no_action_advice(self):
        result = AnalysisEngine(ManualMarketDataProvider()).analyze_trade(
            symbol="NVDA",
            question="Evaluate this trade",
            scenarios=SCENARIOS,
            max_data_age_minutes=15,
        )
        report = write_analysis_report(result)

        self.assertIn("**Provider attempts**", report)
        self.assertIn("CNN Fear & Greed unavailable or blocked", report)
        self.assertIn("OptionCharts unavailable or unsupported path", report)
        forbidden = [
            "you should buy",
            "you should sell",
            "you should roll",
            "you should close",
            "the best action is",
            "i recommend",
            "recommend",
        ]
        for phrase in forbidden:
            self.assertNotIn(phrase, report.lower())


class ProviderSetupRegistryTest(unittest.TestCase):
    def test_provider_setup_registry_includes_futu_opend(self):
        self.assertIn("futu-opend", PROVIDER_SETUP_REGISTRY)

    def test_provider_setup_registry_includes_moomoo_opend(self):
        self.assertIn("moomoo-opend", PROVIDER_SETUP_REGISTRY)

    def test_provider_setup_registry_includes_tradier(self):
        self.assertIn("tradier", PROVIDER_SETUP_REGISTRY)

    def test_provider_setup_registry_includes_polygon(self):
        self.assertIn("polygon", PROVIDER_SETUP_REGISTRY)

    def test_provider_setup_registry_includes_finnhub(self):
        self.assertIn("finnhub", PROVIDER_SETUP_REGISTRY)

    def test_provider_setup_registry_includes_yahoo(self):
        self.assertIn("yahoo", PROVIDER_SETUP_REGISTRY)

    def test_provider_setup_registry_includes_cnn_fear_greed(self):
        self.assertIn("cnn-fear-greed", PROVIDER_SETUP_REGISTRY)

    def test_provider_setup_registry_includes_optioncharts(self):
        self.assertIn("optioncharts", PROVIDER_SETUP_REGISTRY)

    def test_futu_alias_normalizes_to_futu_opend(self):
        self.assertEqual(normalize_provider_id("futu"), "futu-opend")

    def test_moomoo_alias_normalizes_to_moomoo_opend(self):
        self.assertEqual(normalize_provider_id("moomoo"), "moomoo-opend")

    def test_massive_alias_normalizes_to_polygon(self):
        self.assertEqual(normalize_provider_id("massive"), "polygon")

    def test_setup_output_for_missing_futu_opend_includes_official_download_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("tradelens.data.provider_setup._detect_provider_app", return_value=False):
                with patch("tradelens.data.provider_setup.is_opend_reachable", return_value=False):
                    output = render_provider_setup("futu-opend", root=tmp)

        self.assertIn("https://www.futunn.com/en/download/OpenAPI", output)
        self.assertIn("Local OpenD is not reachable at 127.0.0.1:11111", output)

    def test_setup_output_for_missing_moomoo_opend_includes_official_download_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("tradelens.data.provider_setup._detect_provider_app", return_value=False):
                with patch("tradelens.data.provider_setup.is_opend_reachable", return_value=False):
                    output = render_provider_setup("moomoo-opend", root=tmp)

        self.assertIn("https://www.moomoo.com/download/OpenAPI", output)
        self.assertIn("Local OpenD is not reachable at 127.0.0.1:11111", output)

    def test_setup_output_for_api_provider_missing_key_says_to_use_env_variable(self):
        with patch.dict(os.environ, {}, clear=True):
            output = render_provider_setup("polygon")

        self.assertIn("POLYGON_API_KEY environment variable", output)
        self.assertIn('export POLYGON_API_KEY="your_key_here"', output)

    def test_setup_output_does_not_ask_for_broker_password(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = render_provider_setup("futu-opend", root=tmp).lower()

        self.assertIn("does not ask for your futu password", output)
        self.assertNotIn("enter your password", output)
        self.assertNotIn("paste your password", output)

    def test_setup_output_does_not_print_or_store_api_keys(self):
        with patch.dict(os.environ, {"POLYGON_API_KEY": "super-secret-polygon-key"}, clear=True):
            output = render_provider_setup("polygon")

        self.assertNotIn("super-secret-polygon-key", output)
        self.assertIn("Do not store API keys in market_data.md", output)

    def test_setup_command_does_not_silently_install_anything(self):
        with tempfile.TemporaryDirectory() as tmp:
            stdout = StringIO()
            with patch("tradelens.data.provider_setup._detect_provider_app", return_value=False):
                with patch("tradelens.data.provider_setup.is_opend_reachable", return_value=False):
                    with redirect_stdout(stdout):
                        exit_code = cli_main(["--root", tmp, "provider", "setup", "futu-opend"])

        self.assertEqual(exit_code, 0)
        self.assertIn("No app, SDK, or package was installed.", stdout.getvalue())

    def test_public_fallback_providers_do_not_require_account(self):
        for provider_id in ("yahoo", "cnn-fear-greed", "optioncharts"):
            with self.subTest(provider_id=provider_id):
                info = PROVIDER_SETUP_REGISTRY[provider_id]
                self.assertFalse(info.account_required)
                self.assertFalse(info.brokerage_account_required)

    def test_manual_provider_remains_always_available(self):
        provider = ManualMarketDataProvider()

        self.assertIn("quote", provider.capabilities())
        self.assertIn("option_chain", provider.capabilities())

    def test_incomplete_provider_setup_keeps_zero_config_manual_mode_available(self):
        with patch("tradelens.data.provider_setup._detect_provider_app", return_value=False):
            status = check_provider_setup_status("futu-opend")
        bundle = ProviderResolver(config={"providers": {"futu_opend": {"enabled": True}}}).resolve_market_data(
            "NVDA",
            required_capabilities=["quote"],
        )

        self.assertFalse(status.installed)
        self.assertIn("manual", bundle.fallback_path_used)
        self.assertIsNone(bundle.quote)


if __name__ == "__main__":
    unittest.main()
