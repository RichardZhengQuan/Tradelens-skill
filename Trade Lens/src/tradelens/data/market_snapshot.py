"""Structured market-data snapshots for provider-backed analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class ProviderStatus:
    provider_name: str
    capability: str
    available: bool
    status: str
    error: Optional[str] = None
    fetched_at: Optional[datetime] = None
    data_time: Optional[datetime] = None
    is_realtime: Optional[bool] = None
    is_delayed: Optional[bool] = None
    data_quality: str = "low"
    missing_fields: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass
class QuoteSnapshot:
    symbol: str
    price: Optional[float]
    bid: Optional[float] = None
    ask: Optional[float] = None
    previous_close: Optional[float] = None
    change: Optional[float] = None
    change_pct: Optional[float] = None
    session: str = "unknown"
    provider_name: str = "unknown"
    source_type: str = "unknown"
    fetched_at: Optional[datetime] = None
    data_time: Optional[datetime] = None
    is_realtime: Optional[bool] = None
    is_delayed: Optional[bool] = None
    data_quality: str = "low"
    missing_fields: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class OptionContractSnapshot:
    symbol: str
    underlying_symbol: str
    option_type: str
    strike: float
    expiry: str
    bid: Optional[float] = None
    ask: Optional[float] = None
    mark: Optional[float] = None
    last: Optional[float] = None
    volume: Optional[int] = None
    open_interest: Optional[int] = None
    iv: Optional[float] = None
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    provider_name: str = "unknown"
    source_type: str = "unknown"
    fetched_at: Optional[datetime] = None
    data_time: Optional[datetime] = None
    is_realtime: Optional[bool] = None
    is_delayed: Optional[bool] = None
    data_quality: str = "low"
    missing_fields: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class OptionChainSnapshot:
    underlying_symbol: str
    expiry: Optional[str]
    contracts: list[OptionContractSnapshot] = field(default_factory=list)
    highest_oi_calls: list[dict[str, Any]] = field(default_factory=list)
    highest_oi_puts: list[dict[str, Any]] = field(default_factory=list)
    provider_name: str = "unknown"
    source_type: str = "unknown"
    fetched_at: Optional[datetime] = None
    data_time: Optional[datetime] = None
    is_realtime: Optional[bool] = None
    is_delayed: Optional[bool] = None
    data_quality: str = "low"
    missing_fields: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class NewsSnapshot:
    symbol: str
    headlines: list[str] = field(default_factory=list)
    provider_name: str = "unknown"
    source_type: str = "unknown"
    fetched_at: Optional[datetime] = None
    data_time: Optional[datetime] = None
    data_quality: str = "low"
    missing_fields: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class VolatilitySnapshot:
    vix: Optional[float] = None
    uvix: Optional[float] = None
    fear_greed: Optional[float] = None
    fear_greed_label: Optional[str] = None
    provider_name: str = "unknown"
    source_type: str = "unknown"
    fetched_at: Optional[datetime] = None
    data_time: Optional[datetime] = None
    data_quality: str = "low"
    missing_fields: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class IndexContextSnapshot:
    spy: Optional[QuoteSnapshot] = None
    qqq: Optional[QuoteSnapshot] = None
    soxx: Optional[QuoteSnapshot] = None
    provider_name: str = "unknown"
    source_type: str = "unknown"
    fetched_at: Optional[datetime] = None
    data_quality: str = "low"
    missing_fields: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class OpenDProviderSetupResult:
    provider_type: str
    integration_available: bool
    integration_installed: bool
    opend_reachable: bool
    host: str
    port: int
    read_only: bool
    trading_enabled: bool
    password_stored: bool
    test_quote_symbol: str
    test_quote_success: bool
    error: Optional[str] = None
    warnings: list[str] = field(default_factory=list)


FutuProviderSetupResult = OpenDProviderSetupResult


@dataclass
class MarketDataBundle:
    symbol: str
    quote: Optional[QuoteSnapshot] = None
    option_chain: Optional[OptionChainSnapshot] = None
    news: Optional[NewsSnapshot] = None
    volatility: Optional[VolatilitySnapshot] = None
    index_context: Optional[IndexContextSnapshot] = None
    provider_statuses: list[ProviderStatus] = field(default_factory=list)
    missing_data: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    raw_data_quality: str = "low"
    classified_data_quality: str = "low"
    data_quality_reason: Optional[str] = None
    fallback_path_used: list[str] = field(default_factory=list)
    opend_provider_setup_result: Optional[OpenDProviderSetupResult] = None
    futu_provider_setup_result: Optional[FutuProviderSetupResult] = None


def datetime_to_text(value: Optional[datetime]) -> str:
    return "unknown" if value is None else value.isoformat()
