"""Resolve optional market data providers by capability."""

from __future__ import annotations

import os
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from tradelens.data.cache import MarketDataCache
from tradelens.data.capability_planner import ALL_MARKET_CAPABILITIES, CapabilityPlan, build_capability_plan
from tradelens.data.market_snapshot import (
    IndexContextSnapshot,
    MarketDataBundle,
    NewsSnapshot,
    OptionChainSnapshot,
    OptionContractSnapshot,
    ProviderStatus,
    QuoteSnapshot,
    VolatilitySnapshot,
    datetime_to_text,
)
from tradelens.data.provider_base import (
    CAP_ACCOUNT_SUMMARY,
    CAP_FEAR_GREED,
    CAP_INDEX_CONTEXT,
    CAP_NEWS,
    CAP_OPTION_CHAIN,
    CAP_OPTION_GREEKS,
    CAP_OPTION_IV,
    CAP_OPTION_OPEN_INTEREST,
    CAP_OPTION_VOLUME,
    CAP_POSITIONS,
    CAP_QUOTE,
    CAP_UVIX,
    CAP_VIX,
    MarketDataProvider,
)
from tradelens.data.providers.cnn_fear_greed_provider import CNNFearGreedProvider
from tradelens.data.providers.finnhub_provider import FinnhubProvider
from tradelens.data.providers.futu_opend_provider import FutuOpenDProvider
from tradelens.data.providers.manual_provider import ManualMarketDataProvider
from tradelens.data.providers.moomoo_opend_provider import MoomooOpenDProvider
from tradelens.data.providers.optioncharts_provider import OptionChartsProvider
from tradelens.data.providers.opend_base_provider import OpenDProvider, detect_opend_provider
from tradelens.data.providers.polygon_provider import PolygonProvider
from tradelens.data.providers.tradier_provider import TradierProvider
from tradelens.data.providers.yahoo_provider import YahooProvider
from tradelens.models import MarketSnapshot, OptionChain, OptionQuote

DEFAULT_REQUIRED_CAPABILITIES = [
    CAP_QUOTE,
    CAP_OPTION_CHAIN,
    CAP_OPTION_OPEN_INTEREST,
    CAP_NEWS,
    CAP_VIX,
    CAP_UVIX,
    CAP_FEAR_GREED,
    CAP_INDEX_CONTEXT,
]

MARKET_DATA_SNAPSHOT_SECTION = "Provider Market Data Snapshots"
ASSET_PROVIDER_SNAPSHOT_SECTION = "Provider Asset Snapshots"


@dataclass
class ProviderResolver:
    config: dict = field(default_factory=dict)
    market_data_path: Optional[Path] = None
    assets_path: Optional[Path] = None
    configured_providers: list[MarketDataProvider] = field(default_factory=list)
    public_fallback_providers: list[MarketDataProvider] = field(default_factory=list)
    host_providers: list[MarketDataProvider] = field(default_factory=list)
    manual_provider: ManualMarketDataProvider = field(default_factory=ManualMarketDataProvider)
    allow_public_fetch: bool = False

    def __post_init__(self) -> None:
        if self.market_data_path is not None:
            self.market_data_path = Path(self.market_data_path)
        if self.assets_path is not None:
            self.assets_path = Path(self.assets_path)
        market_data_text = self._read_market_data_text(self.market_data_path)
        file_config = _parse_markdown_provider_settings(market_data_text)
        self.config = _deep_merge(file_config, self.config)
        for symbol, snapshot in _parse_local_market_data_snapshots(market_data_text).items():
            self.manual_provider.snapshots.setdefault(symbol, snapshot)
        self.allow_public_fetch = self.allow_public_fetch or _env_flag("TRADELENS_ENABLE_PUBLIC_MARKET_DATA")
        if not self.configured_providers:
            self.configured_providers = self._build_configured_providers()
        if not self.public_fallback_providers:
            self.public_fallback_providers = self._build_public_fallback_providers()

    def resolve_market_data(
        self,
        symbol: str,
        expiry: str | None = None,
        required_capabilities: list[str] | None = None,
        manual_data: dict | None = None,
        strike: Optional[float] = None,
        option_type: Optional[str] = None,
        command: str = "trade",
        instrument_type: str | None = None,
        strategy_type: str | None = None,
        has_option_legs: bool = False,
        user_explicitly_requested: set[str] | None = None,
        capability_plan: CapabilityPlan | None = None,
    ) -> MarketDataBundle:
        plan = capability_plan or _plan_from_required_capabilities(
            required_capabilities,
            command=command,
            instrument_type=instrument_type,
            strategy_type=strategy_type,
            has_option_legs=has_option_legs,
            user_explicitly_requested=user_explicitly_requested,
        )
        required = [capability for capability in plan.required if capability in ALL_MARKET_CAPABILITIES]
        manual_provider = ManualMarketDataProvider(manual_data=manual_data or {})
        providers = self._provider_sequence(manual_provider if manual_data else None)
        self._attach_run_cache(providers)
        bundle = MarketDataBundle(symbol=symbol.upper())
        bundle.capability_plan = plan
        bundle.skipped_capabilities = {
            capability: plan.reason_by_capability.get(capability, "not requested")
            for capability in plan.skipped
        }

        for capability in required:
            if capability == CAP_QUOTE:
                self._resolve_quote(bundle, symbol, providers)
            elif capability in {CAP_OPTION_CHAIN, CAP_OPTION_OPEN_INTEREST, CAP_OPTION_VOLUME, CAP_OPTION_IV, CAP_OPTION_GREEKS}:
                self._resolve_option_chain(bundle, symbol, expiry, strike, option_type, providers, capability)
            elif capability == CAP_NEWS:
                self._resolve_news(bundle, symbol, providers)
            elif capability in {CAP_VIX, CAP_UVIX, CAP_FEAR_GREED}:
                self._resolve_volatility(bundle, providers, capability)
            elif capability == CAP_INDEX_CONTEXT:
                self._resolve_index_context(bundle, providers)
            elif capability == CAP_ACCOUNT_SUMMARY:
                self._resolve_account_summary(bundle, providers)
            elif capability == CAP_POSITIONS:
                self._resolve_positions(bundle, providers)

        self._finalize_bundle(bundle, expiry=expiry, strike=strike, option_type=option_type)
        self._enforce_asset_source_consistency(bundle, command)
        self._persist_market_data_snapshot(bundle)
        self._persist_asset_snapshot(bundle)
        return bundle

    def _attach_run_cache(self, providers: list[MarketDataProvider]) -> None:
        cache = MarketDataCache()
        for provider in providers:
            try:
                setattr(provider, "cache", cache)
            except Exception:
                continue

    def _provider_sequence(self, manual_data_provider: Optional[MarketDataProvider]) -> list[MarketDataProvider]:
        providers: list[MarketDataProvider] = []
        if manual_data_provider is not None:
            providers.append(manual_data_provider)
        providers.extend(self.configured_providers)
        providers.extend(self.public_fallback_providers)
        providers.extend(self.host_providers)
        providers.append(self.manual_provider)
        deduped = []
        seen = set()
        for provider in providers:
            if provider.name in seen:
                continue
            seen.add(provider.name)
            deduped.append(provider)
        return deduped

    def to_market_snapshot(self, bundle: MarketDataBundle) -> MarketSnapshot:
        quote = bundle.quote
        volatility = bundle.volatility
        context = bundle.index_context
        option_contract = _selected_option_contract(bundle.option_chain)
        legacy_option_quote = _legacy_option_quote(option_contract)
        legacy_option_chain = _legacy_option_chain(bundle.option_chain)
        source = quote.provider_name if quote else "provider-resolver"
        snapshot = MarketSnapshot(
            symbol=bundle.symbol.upper(),
            source=source,
            last_updated=datetime_to_text(quote.data_time if quote else None),
            session=quote.session if quote else "unknown",
            quote_timestamp=datetime_to_text(quote.data_time if quote else None),
            regular_hours_price=quote.price if quote else None,
            data_quality=bundle.raw_data_quality,
            missing_data=list(bundle.missing_data),
            stock_price_provider=quote.provider_name if quote else "missing",
            options_provider=(bundle.option_chain.provider_name if bundle.option_chain else "missing"),
            news_provider=(bundle.news.provider_name if bundle.news else "missing"),
            volatility_provider=(volatility.provider_name if volatility else "missing"),
            data_fetched_successfully=quote is not None,
            fallback_used=" > ".join(bundle.fallback_path_used) if bundle.fallback_path_used else "none",
            option_chain=legacy_option_chain,
            option_quote=legacy_option_quote,
            volatility_symbol=_volatility_symbol(volatility),
            volatility_price=_volatility_price(volatility),
            volatility_timestamp=datetime_to_text(volatility.data_time if volatility else None),
            news_headlines=list(bundle.news.headlines if bundle.news else []),
            context_prices=_context_prices(context),
            context_timestamps=_context_timestamps(context),
        )
        return snapshot

    def _resolve_quote(self, bundle: MarketDataBundle, symbol: str, providers: list[MarketDataProvider]) -> None:
        if bundle.quote is not None:
            return
        for provider in providers:
            if not provider.supports(CAP_QUOTE):
                continue
            quote, status = provider.get_quote(symbol)
            bundle.provider_statuses.append(status)
            bundle.fallback_path_used.append(provider.name)
            if quote and quote.price is not None:
                bundle.quote = quote
                return

    def _resolve_option_chain(
        self,
        bundle: MarketDataBundle,
        symbol: str,
        expiry: Optional[str],
        strike: Optional[float],
        option_type: Optional[str],
        providers: list[MarketDataProvider],
        capability: str,
    ) -> None:
        if capability != CAP_OPTION_CHAIN and bundle.option_chain is not None:
            self._record_derived_option_status(bundle, capability)
            return
        if bundle.option_chain is not None:
            return
        for provider in providers:
            if not provider.supports(CAP_OPTION_CHAIN) and not provider.supports(capability):
                continue
            chain, status = provider.get_option_chain(symbol, expiry)
            status.capability = capability if capability != CAP_OPTION_CHAIN else status.capability
            bundle.provider_statuses.append(status)
            bundle.fallback_path_used.append(provider.name)
            if chain and chain.contracts:
                if strike is not None and option_type:
                    _mark_selected_contract(chain, strike, option_type)
                bundle.option_chain = chain
                if capability != CAP_OPTION_CHAIN:
                    self._record_derived_option_status(bundle, capability)
                return

    def _resolve_news(self, bundle: MarketDataBundle, symbol: str, providers: list[MarketDataProvider]) -> None:
        if bundle.news is not None:
            return
        for provider in providers:
            if not provider.supports(CAP_NEWS):
                continue
            news, status = provider.get_news(symbol)
            bundle.provider_statuses.append(status)
            bundle.fallback_path_used.append(provider.name)
            if news and news.headlines:
                bundle.news = news
                return

    def _resolve_volatility(self, bundle: MarketDataBundle, providers: list[MarketDataProvider], capability: str) -> None:
        if _volatility_has_capability(bundle.volatility, capability):
            return
        for provider in providers:
            if not provider.supports(capability):
                continue
            volatility, status = provider.get_volatility()
            status.capability = capability
            bundle.provider_statuses.append(status)
            bundle.fallback_path_used.append(provider.name)
            if volatility:
                bundle.volatility = _merge_volatility(bundle.volatility, volatility)
                if _volatility_has_capability(bundle.volatility, capability):
                    return

    def _resolve_index_context(self, bundle: MarketDataBundle, providers: list[MarketDataProvider]) -> None:
        if bundle.index_context is not None:
            return
        for provider in providers:
            if not provider.supports(CAP_INDEX_CONTEXT):
                continue
            context, status = provider.get_index_context()
            bundle.provider_statuses.append(status)
            bundle.fallback_path_used.append(provider.name)
            if context and any((context.spy, context.qqq, context.soxx)):
                bundle.index_context = context
                return

    def _resolve_account_summary(self, bundle: MarketDataBundle, providers: list[MarketDataProvider]) -> None:
        if bundle.account_summary is not None:
            return
        for provider in providers:
            if not provider.supports(CAP_ACCOUNT_SUMMARY):
                continue
            account_summary, status = provider.get_account_summary()
            bundle.provider_statuses.append(status)
            bundle.fallback_path_used.append(provider.name)
            if account_summary:
                bundle.account_summary = account_summary
                return

    def _resolve_positions(self, bundle: MarketDataBundle, providers: list[MarketDataProvider]) -> None:
        if bundle.positions is not None:
            return
        for provider in providers:
            if not provider.supports(CAP_POSITIONS):
                continue
            positions, status = provider.get_positions()
            bundle.provider_statuses.append(status)
            bundle.fallback_path_used.append(provider.name)
            if positions:
                bundle.positions = positions
                return

    def _record_derived_option_status(self, bundle: MarketDataBundle, capability: str) -> None:
        missing = _option_capability_missing(bundle.option_chain, capability)
        bundle.provider_statuses.append(
            ProviderStatus(
                provider_name=bundle.option_chain.provider_name if bundle.option_chain else "missing",
                capability=capability,
                available=not missing,
                status="found" if not missing else "missing",
                error=None if not missing else f"{capability} missing from option chain",
                missing_fields=missing,
                data_quality=bundle.option_chain.data_quality if bundle.option_chain else "low",
            )
        )

    def _finalize_bundle(
        self,
        bundle: MarketDataBundle,
        expiry: Optional[str],
        strike: Optional[float],
        option_type: Optional[str],
    ) -> None:
        self._record_opend_setup_result(bundle)
        missing = []
        skipped = bundle.skipped_capabilities
        if CAP_QUOTE not in skipped and bundle.quote is None:
            missing.extend(["realtime data unavailable", "underlying realtime/latest price", "quote timestamp"])
        elif CAP_QUOTE not in skipped and bundle.quote.data_time is None:
            missing.append("quote timestamp")

        if CAP_OPTION_CHAIN not in skipped and expiry and bundle.option_chain is None:
            missing.append("option chain for relevant expiry")
        if (
            CAP_OPTION_CHAIN not in skipped
            and expiry
            and strike is not None
            and option_type
            and _selected_option_contract(bundle.option_chain) is None
        ):
            missing.append("option mark/bid/ask/open interest/volume/IV/delta")
        if CAP_NEWS not in skipped and bundle.news is None:
            missing.append("newest company news")
        if (
            (CAP_VIX not in skipped or CAP_UVIX not in skipped)
            and (bundle.volatility is None or (bundle.volatility.vix is None and bundle.volatility.uvix is None))
        ):
            missing.append("VIX or UVIX volatility context")
        if CAP_FEAR_GREED not in skipped and (bundle.volatility is None or bundle.volatility.fear_greed is None):
            missing.append("Fear & Greed")
        if CAP_INDEX_CONTEXT not in skipped and (bundle.index_context is None or not bundle.index_context.spy):
            missing.append("SPY latest context")
        if CAP_INDEX_CONTEXT not in skipped and (bundle.index_context is None or not bundle.index_context.qqq):
            missing.append("QQQ latest context")
        if CAP_INDEX_CONTEXT not in skipped and (bundle.index_context is None or not bundle.index_context.soxx):
            missing.append("SOXX latest context")
        if CAP_ACCOUNT_SUMMARY not in skipped and bundle.account_summary is None:
            missing.append("provider account summary")
        if CAP_POSITIONS not in skipped and bundle.positions is None:
            missing.append("provider positions")

        errors = [status.error for status in bundle.provider_statuses if status.error]
        status_missing = []
        for status in bundle.provider_statuses:
            status_missing.extend(status.missing_fields)

        bundle.missing_data = _ordered_unique(missing + status_missing)
        bundle.errors = _ordered_unique(errors)
        bundle.fallback_path_used = _ordered_unique(bundle.fallback_path_used)
        bundle.raw_data_quality = _raw_quality(bundle)
        bundle.classified_data_quality, bundle.data_quality_reason = _classify_bundle_quality(bundle)

    def _build_configured_providers(self) -> list[MarketDataProvider]:
        provider_config = self.config.get("providers", {})
        providers: list[MarketDataProvider] = []
        opend_config = _combined_provider_config(self.config, provider_config, "opend")
        concrete_opend_base = {key: value for key, value in opend_config.items() if key != "default_provider"}
        futu_config = _deep_merge(
            concrete_opend_base,
            _combined_provider_config(self.config, provider_config, "futu_opend", "futu"),
        )
        if futu_config.get("enabled"):
            providers.append(FutuOpenDProvider(**_allowed_kwargs(FutuOpenDProvider, futu_config)))
        moomoo_config = _deep_merge(
            concrete_opend_base,
            _combined_provider_config(self.config, provider_config, "moomoo_opend"),
        )
        if moomoo_config.get("enabled"):
            providers.append(MoomooOpenDProvider(**_allowed_kwargs(MoomooOpenDProvider, moomoo_config)))
        if opend_config.get("enabled"):
            detected_provider = _detect_enabled_opend_provider(opend_config)
            if detected_provider == "futu-opend" and not futu_config.get("enabled"):
                auto_config = _deep_merge(concrete_opend_base, {"enabled": True})
                providers.append(FutuOpenDProvider(**_allowed_kwargs(FutuOpenDProvider, auto_config)))
            elif detected_provider == "moomoo-opend" and not moomoo_config.get("enabled"):
                auto_config = _deep_merge(concrete_opend_base, {"enabled": True})
                providers.append(MoomooOpenDProvider(**_allowed_kwargs(MoomooOpenDProvider, auto_config)))
        tradier_config = provider_config.get("tradier", {})
        if tradier_config.get("enabled"):
            providers.append(TradierProvider(**_allowed_kwargs(TradierProvider, tradier_config)))
        polygon_config = provider_config.get("polygon", {})
        if polygon_config.get("enabled"):
            providers.append(PolygonProvider(**_allowed_kwargs(PolygonProvider, polygon_config)))
        finnhub_config = provider_config.get("finnhub", {})
        if finnhub_config.get("enabled"):
            providers.append(FinnhubProvider(**_allowed_kwargs(FinnhubProvider, finnhub_config)))
        yahoo_config = provider_config.get("yahoo", {})
        if yahoo_config.get("enabled"):
            yahoo_kwargs = _allowed_kwargs(YahooProvider, yahoo_config)
            yahoo_kwargs.setdefault("allow_fetch", self.allow_public_fetch)
            providers.append(YahooProvider(**yahoo_kwargs))
        return providers

    def _record_opend_setup_result(self, bundle: MarketDataBundle) -> None:
        provider = next((provider for provider in self.configured_providers if isinstance(provider, OpenDProvider)), None)
        if provider is None:
            return
        setup_result = provider.setup_result_from_statuses(bundle.provider_statuses)
        bundle.opend_provider_setup_result = setup_result
        if isinstance(provider, FutuOpenDProvider):
            bundle.futu_provider_setup_result = setup_result

    def _build_public_fallback_providers(self) -> list[MarketDataProvider]:
        public_config = self.config.get("public_fallbacks", {})
        yahoo_config = _public_fallback_config(public_config, "yahoo")
        cnn_config = _public_fallback_config(public_config, "cnn-fear-greed", "cnn_fear_greed", "cnn")
        optioncharts_config = _public_fallback_config(public_config, "optioncharts", "option_charts")
        return [
            YahooProvider(
                enabled=yahoo_config.get("enabled", True),
                allow_fetch=self.allow_public_fetch,
            ),
            CNNFearGreedProvider(
                enabled=cnn_config.get("enabled", True),
                allow_fetch=self.allow_public_fetch,
            ),
            OptionChartsProvider(
                enabled=optioncharts_config.get("enabled", True),
                allow_fetch=self.allow_public_fetch,
            ),
        ]

    def _persist_market_data_snapshot(self, bundle: MarketDataBundle) -> None:
        if self.market_data_path is None:
            return
        entry = _render_provider_snapshot_entry(bundle)
        if not entry:
            return
        _append_market_data_snapshot_entry(self.market_data_path, entry)

    def _persist_asset_snapshot(self, bundle: MarketDataBundle) -> None:
        if self.assets_path is None:
            return
        entry = _render_provider_asset_snapshot_entry(bundle)
        if not entry:
            return
        _append_asset_snapshot_entry(self.assets_path, entry)

    def _enforce_asset_source_consistency(self, bundle: MarketDataBundle, command: str) -> None:
        if not _is_assets_command(command):
            return
        if bundle.account_summary is not None and bundle.positions is not None:
            bundle.asset_data_source_mode = "provider"
            bundle.asset_data_source_reason = (
                "provider account summary and positions are complete; do not mix in local assets.md values"
            )
            return

        bundle.asset_data_source_mode = "local_fallback"
        bundle.asset_data_source_reason = (
            "provider account summary or positions are missing; use local assets.md only and do not mix quote refreshes"
        )
        bundle.account_summary = None
        bundle.positions = None
        bundle.quote = None
        bundle.option_chain = None
        bundle.news = None
        bundle.volatility = None
        bundle.index_context = None
        bundle.raw_data_quality = _raw_quality(bundle)
        bundle.classified_data_quality, bundle.data_quality_reason = _classify_bundle_quality(bundle)

    def _read_market_data_text(self, path: Optional[Path]) -> str:
        if path is None or not path.exists():
            return ""
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return ""

    def _read_market_data_settings(self, path: Optional[Path]) -> dict:
        return _parse_markdown_provider_settings(self._read_market_data_text(path))


def resolve_market_data_provider(
    configured_provider: Optional[MarketDataProvider] = None,
    manual_provider: Optional[ManualMarketDataProvider] = None,
    allow_web: Optional[bool] = None,
) -> ProviderResolver | MarketDataProvider:
    if configured_provider is not None:
        return ProviderResolver(configured_providers=[configured_provider])
    if allow_web is None:
        allow_web = _env_flag("TRADELENS_ENABLE_PUBLIC_MARKET_DATA")
    return ProviderResolver(
        manual_provider=manual_provider or ManualMarketDataProvider(),
        allow_public_fetch=allow_web,
    )


def _plan_from_required_capabilities(
    required_capabilities: list[str] | None,
    command: str,
    instrument_type: str | None,
    strategy_type: str | None,
    has_option_legs: bool,
    user_explicitly_requested: set[str] | None,
) -> CapabilityPlan:
    if required_capabilities is None:
        return build_capability_plan(
            command=command,
            instrument_type=instrument_type,
            strategy_type=strategy_type,
            has_option_legs=has_option_legs,
            user_explicitly_requested=user_explicitly_requested,
        )
    required = {capability for capability in required_capabilities if capability in ALL_MARKET_CAPABILITIES}
    skipped = ALL_MARKET_CAPABILITIES - required
    reasons = {capability: "required by caller" for capability in required}
    reasons.update({capability: "not requested" for capability in skipped})
    return CapabilityPlan(required=required, optional=set(), skipped=skipped, reason_by_capability=reasons)


def _is_assets_command(command: str) -> bool:
    normalized = command.strip().lower().replace("-", "_").replace("/", "").replace("_", " ")
    return normalized in {"assets", "asset", "tradelens assets"}


def _parse_markdown_provider_settings(text: str) -> dict:
    config: dict = {"providers": {}, "public_fallbacks": {}}
    current: tuple[str, str] | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        heading = re.match(r"^##\s+(.+)$", line)
        if heading:
            current = _provider_section_config_target(heading.group(1))
            continue
        if current and line.startswith("- ") and ":" in line:
            key, value = line[2:].split(":", 1)
            parsed = _parse_value(value.strip())
            config_group, provider_id = current
            config[config_group].setdefault(provider_id, {})[key.strip()] = parsed
    return config


def _provider_section_config_target(heading: str) -> tuple[str, str] | None:
    normalized = heading.strip().lower()
    normalized = re.sub(r"\bprovider\b", "", normalized)
    normalized = normalized.replace("&", " ")
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")
    normalized = normalized.replace("__", "_")
    providers = {
        "opend": "opend",
        "futu": "futu",
        "futu_opend": "futu_opend",
        "moomoo_opend": "moomoo_opend",
        "tradier": "tradier",
        "polygon": "polygon",
        "finnhub": "finnhub",
        "yahoo": "yahoo",
    }
    public_fallbacks = {
        "cnn": "cnn-fear-greed",
        "cnn_fear_greed": "cnn-fear-greed",
        "cnn_fear_and_greed": "cnn-fear-greed",
        "optioncharts": "optioncharts",
        "option_charts": "optioncharts",
    }
    if normalized in providers:
        return "providers", providers[normalized]
    if normalized in public_fallbacks:
        return "public_fallbacks", public_fallbacks[normalized]
    return None


def _parse_value(value: str):
    lowered = value.strip().lower()
    if lowered in {"true", "yes"}:
        return True
    if lowered in {"false", "no"}:
        return False
    try:
        return int(value)
    except ValueError:
        return value


def _deep_merge(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _public_fallback_config(public_config: dict, *keys: str) -> dict:
    merged: dict = {}
    for key in keys:
        value = public_config.get(key, {})
        if isinstance(value, dict):
            merged = _deep_merge(merged, value)
    return merged


def _combined_provider_config(config: dict, provider_config: dict, *names: str) -> dict:
    merged = {}
    for name in names:
        top_level = config.get(name, {})
        nested = provider_config.get(name, {})
        if isinstance(top_level, dict):
            merged = _deep_merge(merged, top_level)
        if isinstance(nested, dict):
            merged = _deep_merge(merged, nested)
    return merged


def _detect_enabled_opend_provider(opend_config: dict) -> Optional[str]:
    default_provider = str(opend_config.get("default_provider", "auto")).strip().lower().replace("_", "-")
    if default_provider in {"futu", "futu-opend"}:
        return "futu-opend"
    if default_provider in {"moomoo", "moomoo-opend"}:
        return "moomoo-opend"
    detection = detect_opend_provider(
        host=str(opend_config.get("host", "127.0.0.1")),
        port=int(opend_config.get("port", 11111)),
    )
    return detection.selected_provider


def _allowed_kwargs(cls, config: dict) -> dict:
    field_names = getattr(cls, "__dataclass_fields__", {}).keys()
    return {key: value for key, value in config.items() if key in field_names}


def _raw_quality(bundle: MarketDataBundle) -> str:
    qualities = []
    for item in (bundle.quote, bundle.option_chain, bundle.news, bundle.volatility, bundle.index_context):
        if item is not None:
            qualities.append(getattr(item, "data_quality", "low"))
    if not qualities:
        return "low"
    if "low" in qualities:
        return "low"
    if "medium" in qualities:
        return "medium"
    return "high"


def _classify_bundle_quality(bundle: MarketDataBundle) -> tuple[str, str]:
    if bundle.quote is None or bundle.quote.price is None:
        return "low", "no fresh quote available"
    has_options = bundle.option_chain is not None and bool(bundle.option_chain.contracts)
    has_context = bool(bundle.news) or bool(bundle.volatility) or bool(bundle.index_context)
    if has_options and has_context:
        return "high", "fresh quote plus relevant market context available"
    return "medium", "quote available but options, sentiment, volatility, news, or index context is incomplete"


def _selected_option_contract(chain: Optional[OptionChainSnapshot]) -> Optional[OptionContractSnapshot]:
    if chain is None:
        return None
    for contract in chain.contracts:
        if "selected contract" in contract.missing_fields:
            continue
        if getattr(contract, "selected", False):
            return contract
    return chain.contracts[0] if chain.contracts else None


def _mark_selected_contract(chain: OptionChainSnapshot, strike: float, option_type: str) -> None:
    normalized_type = {"c": "call", "p": "put"}.get(option_type.lower(), option_type.lower())
    for contract in chain.contracts:
        if contract.option_type == normalized_type and abs(contract.strike - strike) < 0.0001:
            setattr(contract, "selected", True)
            return


def _legacy_option_quote(contract: Optional[OptionContractSnapshot]) -> Optional[OptionQuote]:
    if contract is None:
        return None
    return OptionQuote(
        symbol=contract.symbol,
        expiry=contract.expiry,
        strike=contract.strike,
        option_type=contract.option_type,
        mark=contract.mark,
        bid=contract.bid,
        ask=contract.ask,
        open_interest=contract.open_interest,
        volume=contract.volume,
        iv=contract.iv,
        delta=contract.delta,
        source=contract.provider_name,
        last_updated=datetime_to_text(contract.data_time),
    )


def _legacy_option_chain(chain: Optional[OptionChainSnapshot]) -> Optional[OptionChain]:
    if chain is None:
        return None
    return OptionChain(
        symbol=chain.underlying_symbol,
        expiry=chain.expiry or "unknown",
        source=chain.provider_name,
        last_updated=datetime_to_text(chain.data_time),
        options=[_legacy_option_quote(contract) for contract in chain.contracts if _legacy_option_quote(contract)],
        missing_data=list(chain.missing_fields),
    )


def _option_capability_missing(chain: Optional[OptionChainSnapshot], capability: str) -> list[str]:
    contract = _selected_option_contract(chain)
    if contract is None:
        return [capability]
    if capability == CAP_OPTION_OPEN_INTEREST and contract.open_interest is None:
        return ["open interest"]
    if capability == CAP_OPTION_VOLUME and contract.volume is None:
        return ["volume"]
    if capability == CAP_OPTION_IV and contract.iv is None:
        return ["IV"]
    if capability == CAP_OPTION_GREEKS and all(
        value is None for value in (contract.delta, contract.gamma, contract.theta, contract.vega)
    ):
        return ["Greeks"]
    return []


def _merge_volatility(existing: Optional[VolatilitySnapshot], new: VolatilitySnapshot) -> VolatilitySnapshot:
    if existing is None:
        return new
    existing.vix = existing.vix if existing.vix is not None else new.vix
    existing.uvix = existing.uvix if existing.uvix is not None else new.uvix
    existing.fear_greed = existing.fear_greed if existing.fear_greed is not None else new.fear_greed
    existing.fear_greed_label = existing.fear_greed_label or new.fear_greed_label
    existing.missing_fields = _ordered_unique(existing.missing_fields + new.missing_fields)
    existing.errors = _ordered_unique(existing.errors + new.errors)
    existing.data_quality = "medium" if existing.data_quality != "high" or new.data_quality != "high" else "high"
    return existing


def _volatility_has_capability(volatility: Optional[VolatilitySnapshot], capability: str) -> bool:
    if volatility is None:
        return False
    if capability == CAP_VIX:
        return volatility.vix is not None
    if capability == CAP_UVIX:
        return volatility.uvix is not None
    if capability == CAP_FEAR_GREED:
        return volatility.fear_greed is not None
    return False


def _volatility_symbol(volatility: Optional[VolatilitySnapshot]) -> str:
    if volatility is None:
        return "unknown"
    if volatility.vix is not None:
        return "VIX"
    if volatility.uvix is not None:
        return "UVIX"
    if volatility.fear_greed is not None:
        return "Fear & Greed"
    return "unknown"


def _volatility_price(volatility: Optional[VolatilitySnapshot]) -> Optional[float]:
    if volatility is None:
        return None
    return volatility.vix if volatility.vix is not None else volatility.uvix


def _context_prices(context: Optional[IndexContextSnapshot]) -> dict[str, Optional[float]]:
    return {
        "SPY": context.spy.price if context and context.spy else None,
        "QQQ": context.qqq.price if context and context.qqq else None,
        "SOXX": context.soxx.price if context and context.soxx else None,
    }


def _context_timestamps(context: Optional[IndexContextSnapshot]) -> dict[str, str]:
    return {
        "SPY": datetime_to_text(context.spy.data_time if context and context.spy else None),
        "QQQ": datetime_to_text(context.qqq.data_time if context and context.qqq else None),
        "SOXX": datetime_to_text(context.soxx.data_time if context and context.soxx else None),
    }


def _render_provider_snapshot_entry(bundle: MarketDataBundle) -> str:
    if not _has_persistable_provider_data(bundle):
        return ""
    fetched_at = datetime.now(timezone.utc).isoformat()
    lines = [
        f"### Snapshot {fetched_at} - {bundle.symbol.upper()}",
        "",
        f"- symbol: {bundle.symbol.upper()}",
        f"- fetched_at: {fetched_at}",
        f"- raw_data_quality: {_text_value(bundle.raw_data_quality)}",
        f"- classified_data_quality: {_text_value(bundle.classified_data_quality)}",
        f"- data_quality_reason: {_text_value(bundle.data_quality_reason)}",
        f"- fallback_path_used: {_list_value(bundle.fallback_path_used)}",
        f"- missing_data: {_list_value(bundle.missing_data)}",
    ]
    if _is_persistable_provider(bundle.quote):
        quote = bundle.quote
        lines.extend(
            [
                "",
                "#### Quote",
                f"- source: {_text_value(quote.provider_name)}",
                f"- source_type: {_text_value(quote.source_type)}",
                f"- price: {_text_value(quote.price)}",
                f"- bid: {_text_value(quote.bid)}",
                f"- ask: {_text_value(quote.ask)}",
                f"- previous_close: {_text_value(quote.previous_close)}",
                f"- change: {_text_value(quote.change)}",
                f"- change_pct: {_text_value(quote.change_pct)}",
                f"- session: {_text_value(quote.session)}",
                f"- quote_timestamp: {_text_value(datetime_to_text(quote.data_time))}",
                f"- is_realtime: {_text_value(quote.is_realtime)}",
                f"- is_delayed: {_text_value(quote.is_delayed)}",
                f"- data_quality: {_text_value(quote.data_quality)}",
            ]
        )
    if _is_persistable_provider(bundle.option_chain):
        chain = bundle.option_chain
        selected = _selected_option_contract(chain)
        lines.extend(
            [
                "",
                "#### Option Chain",
                f"- source: {_text_value(chain.provider_name)}",
                f"- expiry: {_text_value(chain.expiry)}",
                f"- contracts_returned: {len(chain.contracts)}",
                f"- selected_contract: {_text_value(selected.symbol if selected else None)}",
                f"- selected_mark: {_text_value(selected.mark if selected else None)}",
                f"- selected_bid: {_text_value(selected.bid if selected else None)}",
                f"- selected_ask: {_text_value(selected.ask if selected else None)}",
                f"- selected_open_interest: {_text_value(selected.open_interest if selected else None)}",
                f"- selected_volume: {_text_value(selected.volume if selected else None)}",
                f"- selected_iv: {_text_value(selected.iv if selected else None)}",
                f"- selected_delta: {_text_value(selected.delta if selected else None)}",
                f"- data_time: {_text_value(datetime_to_text(chain.data_time))}",
                f"- data_quality: {_text_value(chain.data_quality)}",
            ]
        )
    if _is_persistable_provider(bundle.volatility):
        volatility = bundle.volatility
        lines.extend(
            [
                "",
                "#### Volatility",
                f"- source: {_text_value(volatility.provider_name)}",
                f"- vix: {_text_value(volatility.vix)}",
                f"- uvix: {_text_value(volatility.uvix)}",
                f"- fear_greed: {_text_value(volatility.fear_greed)}",
                f"- fear_greed_label: {_text_value(volatility.fear_greed_label)}",
                f"- data_time: {_text_value(datetime_to_text(volatility.data_time))}",
                f"- data_quality: {_text_value(volatility.data_quality)}",
            ]
        )
    if _is_persistable_provider(bundle.index_context):
        context = bundle.index_context
        lines.extend(
            [
                "",
                "#### Index Context",
                f"- source: {_text_value(context.provider_name)}",
                f"- spy: {_text_value(context.spy.price if context.spy else None)}",
                f"- qqq: {_text_value(context.qqq.price if context.qqq else None)}",
                f"- soxx: {_text_value(context.soxx.price if context.soxx else None)}",
                f"- data_quality: {_text_value(context.data_quality)}",
            ]
        )
    if _is_persistable_provider(bundle.news):
        news = bundle.news
        lines.extend(
            [
                "",
                "#### News",
                f"- source: {_text_value(news.provider_name)}",
                f"- data_time: {_text_value(datetime_to_text(news.data_time))}",
                f"- data_quality: {_text_value(news.data_quality)}",
                f"- headlines: {_list_value(news.headlines)}",
            ]
        )
    return "\n".join(lines)


def _render_provider_asset_snapshot_entry(bundle: MarketDataBundle) -> str:
    if bundle.account_summary is None or bundle.positions is None:
        return ""
    fetched_at = datetime.now(timezone.utc).isoformat()
    account_status = _first_status(bundle, CAP_ACCOUNT_SUMMARY)
    positions_status = _first_status(bundle, CAP_POSITIONS)
    lines = [
        f"### Asset Snapshot {fetched_at}",
        "",
        f"- fetched_at: {fetched_at}",
        f"- account_summary_source: {_text_value(account_status.provider_name if account_status else None)}",
        f"- positions_source: {_text_value(positions_status.provider_name if positions_status else None)}",
        f"- account_summary_status: {_text_value(account_status.status if account_status else None)}",
        f"- positions_status: {_text_value(positions_status.status if positions_status else None)}",
    ]
    if bundle.account_summary is not None:
        lines.extend(
            [
                "",
                "#### Account Summary",
                "```json",
                _safe_json(bundle.account_summary),
                "```",
            ]
        )
    if bundle.positions is not None:
        lines.extend(
            [
                "",
                "#### Positions",
                "```json",
                _safe_json(bundle.positions),
                "```",
            ]
        )
    return "\n".join(lines)


def _append_asset_snapshot_entry(path: Path, entry: str) -> None:
    text = path.read_text(encoding="utf-8") if path.exists() else "# Assets\n\n"
    heading = f"## {ASSET_PROVIDER_SNAPSHOT_SECTION}"
    section_pattern = re.compile(rf"^{re.escape(heading)}\n.*?(?=^## |\Z)", re.MULTILINE | re.DOTALL)
    match = section_pattern.search(text)
    if match:
        section = match.group(0).rstrip() + "\n\n" + entry.rstrip() + "\n"
        text = text[: match.start()] + section + text[match.end() :]
    else:
        section = f"{heading}\n\n{entry.rstrip()}\n"
        marker = "\n## Corrections"
        if marker in text:
            text = text.replace(marker, "\n" + section + marker, 1)
        else:
            text = text.rstrip() + "\n\n" + section
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _first_status(bundle: MarketDataBundle, capability: str) -> Optional[ProviderStatus]:
    return next(
        (
            status
            for status in bundle.provider_statuses
            if status.capability == capability and status.available
        ),
        None,
    )


def _safe_json(value) -> str:
    redacted = _redact_secret_values(value)
    return json.dumps(redacted, indent=2, sort_keys=True, default=str)


def _redact_secret_values(value):
    if isinstance(value, dict):
        redacted = {}
        for key, item in value.items():
            key_text = str(key)
            if _looks_secret_key(key_text):
                redacted[key_text] = "[secret redacted]"
            else:
                redacted[key_text] = _redact_secret_values(item)
        return redacted
    if isinstance(value, list):
        return [_redact_secret_values(item) for item in value]
    return value


def _looks_secret_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_").replace(" ", "_")
    secret_terms = (
        "api_key",
        "apikey",
        "token",
        "secret",
        "password",
        "2fa",
        "sms",
        "recovery_code",
    )
    return any(term in normalized for term in secret_terms)


def _has_persistable_provider_data(bundle: MarketDataBundle) -> bool:
    return any(
        _is_persistable_provider(item)
        for item in (bundle.quote, bundle.option_chain, bundle.volatility, bundle.index_context, bundle.news)
    )


def _is_persistable_provider(item) -> bool:
    if item is None:
        return False
    provider_name = str(getattr(item, "provider_name", "") or "").lower()
    source_type = str(getattr(item, "source_type", "") or "").lower()
    return provider_name not in {"", "unknown", "manual"} and source_type != "manual"


def _append_market_data_snapshot_entry(path: Path, entry: str) -> None:
    text = path.read_text(encoding="utf-8") if path.exists() else "# Market Data Settings\n\n"
    heading = f"## {MARKET_DATA_SNAPSHOT_SECTION}"
    section_pattern = re.compile(rf"^{re.escape(heading)}\n.*?(?=^## |\Z)", re.MULTILINE | re.DOTALL)
    match = section_pattern.search(text)
    if match:
        section = match.group(0).rstrip() + "\n\n" + entry.rstrip() + "\n"
        text = text[: match.start()] + section + text[match.end() :]
    else:
        section = f"{heading}\n\n{entry.rstrip()}\n"
        marker = "\n## Corrections"
        if marker in text:
            text = text.replace(marker, "\n" + section + marker, 1)
        else:
            text = text.rstrip() + "\n\n" + section
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _parse_local_market_data_snapshots(text: str) -> dict[str, MarketSnapshot]:
    snapshots: dict[str, MarketSnapshot] = {}
    if not text:
        return snapshots
    block_pattern = re.compile(r"^### Snapshot .*\n.*?(?=^### Snapshot |^## |\Z)", re.MULTILINE | re.DOTALL)
    for match in block_pattern.finditer(text):
        snapshot = _parse_local_quote_snapshot(match.group(0))
        if snapshot is not None:
            snapshots[snapshot.symbol.upper()] = snapshot
    return snapshots


def _parse_local_quote_snapshot(block: str) -> Optional[MarketSnapshot]:
    fields = _parse_bullet_fields(block)
    quote_fields = _parse_bullet_fields(_subsection_body(block, "Quote"))
    symbol = str(fields.get("symbol") or "").upper()
    price = _float_or_none(quote_fields.get("price"))
    if not symbol or price is None:
        return None
    quote_timestamp = _known_text(quote_fields.get("quote_timestamp"))
    source = _known_text(quote_fields.get("source")) or "market_data.md"
    data_quality = _known_text(quote_fields.get("data_quality")) or _known_text(fields.get("classified_data_quality")) or "low"
    return MarketSnapshot(
        symbol=symbol,
        source=source,
        last_updated=quote_timestamp or (_known_text(fields.get("fetched_at")) or "unknown"),
        session=_known_text(quote_fields.get("session")) or "unknown",
        quote_timestamp=quote_timestamp or "unknown",
        regular_hours_price=price,
        data_quality=data_quality,
        missing_data=_list_from_text(fields.get("missing_data")),
        stock_price_provider="market_data.md",
        options_provider="market_data.md",
        news_provider="market_data.md",
        volatility_provider="market_data.md",
        data_fetched_successfully=True,
        fallback_used="market_data.md",
    )


def _subsection_body(block: str, heading: str) -> str:
    pattern = re.compile(rf"^#### {re.escape(heading)}\n(.*?)(?=^#### |^### |^## |\Z)", re.MULTILINE | re.DOTALL)
    match = pattern.search(block)
    return match.group(1) if match else ""


def _parse_bullet_fields(text: str) -> dict[str, str]:
    fields = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line.startswith("- ") or ":" not in line:
            continue
        key, value = line[2:].split(":", 1)
        fields[key.strip()] = value.strip()
    return fields


def _known_text(value) -> Optional[str]:
    if value in (None, "", "unknown", "none"):
        return None
    return str(value)


def _text_value(value) -> str:
    if value is None or value == "":
        return "unknown"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value).replace("\n", " ").strip() or "unknown"


def _list_value(values) -> str:
    if not values:
        return "none"
    if isinstance(values, str):
        return values
    return "; ".join(_text_value(value) for value in values if _text_value(value) != "unknown") or "none"


def _list_from_text(value) -> list[str]:
    if value in (None, "", "none", "unknown"):
        return []
    return [item.strip() for item in str(value).split(";") if item.strip()]


def _float_or_none(value) -> Optional[float]:
    try:
        return None if value in (None, "", "unknown") else float(value)
    except (TypeError, ValueError):
        return None


def _ordered_unique(items: list[str]) -> list[str]:
    seen = set()
    unique = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}
