"""Manual/user-confirmed market data provider."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from tradelens.data.market_snapshot import (
    IndexContextSnapshot,
    NewsSnapshot,
    OptionChainSnapshot,
    OptionContractSnapshot,
    ProviderStatus,
    QuoteSnapshot,
    VolatilitySnapshot,
)
from tradelens.data.provider_base import (
    CAP_ACCOUNT_SUMMARY,
    CAP_EXTENDED_HOURS_QUOTE,
    CAP_FEAR_GREED,
    CAP_INDEX_CONTEXT,
    CAP_NEWS,
    CAP_OPTION_CHAIN,
    CAP_OPTION_CONTRACT,
    CAP_OPTION_GREEKS,
    CAP_OPTION_IV,
    CAP_OPTION_OPEN_INTEREST,
    CAP_OPTION_VOLUME,
    CAP_OVERNIGHT_QUOTE,
    CAP_POSITIONS,
    CAP_QUOTE,
    CAP_UVIX,
    CAP_VIX,
    MarketDataProvider,
)
from tradelens.models import MarketSnapshot


@dataclass
class ManualMarketDataProvider(MarketDataProvider):
    name: str = "manual"
    manual_data: dict[str, Any] = field(default_factory=dict)
    snapshots: dict[str, MarketSnapshot] = field(default_factory=dict)
    snapshot: Optional[MarketSnapshot] = None

    def __post_init__(self) -> None:
        if self.snapshot:
            self.set_snapshot(self.snapshot)

    def capabilities(self) -> set[str]:
        return {
            CAP_QUOTE,
            CAP_EXTENDED_HOURS_QUOTE,
            CAP_OVERNIGHT_QUOTE,
            CAP_OPTION_CHAIN,
            CAP_OPTION_CONTRACT,
            CAP_OPTION_GREEKS,
            CAP_OPTION_IV,
            CAP_OPTION_OPEN_INTEREST,
            CAP_OPTION_VOLUME,
            CAP_NEWS,
            CAP_VIX,
            CAP_UVIX,
            CAP_FEAR_GREED,
            CAP_INDEX_CONTEXT,
            CAP_POSITIONS,
            CAP_ACCOUNT_SUMMARY,
        }

    def set_snapshot(self, snapshot: MarketSnapshot) -> None:
        self.snapshots[snapshot.symbol.upper()] = snapshot

    def get_quote(self, symbol: str) -> tuple[Optional[QuoteSnapshot], ProviderStatus]:
        key = symbol.upper()
        snapshot = self.snapshots.get(key)
        quote_data = self.manual_data.get("quote", {})
        price = _first_present(
            quote_data.get("price"),
            getattr(snapshot, "regular_hours_price", None),
            getattr(snapshot, "after_hours_price", None),
            getattr(snapshot, "premarket_price", None),
            getattr(snapshot, "twenty_four_hour_price", None),
        )
        data_time = _datetime_or_none(
            _first_known(
                quote_data.get("data_time"),
                quote_data.get("quote_timestamp"),
                getattr(snapshot, "quote_timestamp", None),
                getattr(snapshot, "last_updated", None),
            )
        )
        if price is None:
            return None, self._missing_status(
                CAP_QUOTE,
                "manual quote not provided",
                ["underlying realtime/latest price", "quote timestamp"],
            )

        quote = QuoteSnapshot(
            symbol=key,
            price=float(price),
            bid=_float_or_none(quote_data.get("bid")),
            ask=_float_or_none(quote_data.get("ask")),
            session=quote_data.get("session") or getattr(snapshot, "session", "unknown"),
            provider_name=self.name,
            source_type=quote_data.get("source_type", "manual"),
            fetched_at=datetime.utcnow(),
            data_time=data_time,
            is_realtime=quote_data.get("is_realtime"),
            is_delayed=quote_data.get("is_delayed"),
            data_quality=quote_data.get("data_quality") or getattr(snapshot, "data_quality", "low"),
            missing_fields=[] if data_time else ["quote timestamp"],
        )
        return quote, ProviderStatus(
            provider_name=self.name,
            capability=CAP_QUOTE,
            available=True,
            status="found",
            fetched_at=quote.fetched_at,
            data_time=quote.data_time,
            is_realtime=quote.is_realtime,
            is_delayed=quote.is_delayed,
            data_quality=quote.data_quality,
            missing_fields=list(quote.missing_fields),
            notes=["manual or user-confirmed quote"],
        )

    def get_option_chain(
        self,
        symbol: str,
        expiry: Optional[str] = None,
    ) -> tuple[Optional[OptionChainSnapshot], ProviderStatus]:
        chain = self.manual_data.get("option_chain")
        if isinstance(chain, OptionChainSnapshot):
            return chain, ProviderStatus(
                provider_name=self.name,
                capability=CAP_OPTION_CHAIN,
                available=True,
                status="found",
                data_quality=chain.data_quality,
                missing_fields=list(chain.missing_fields),
                notes=["manual or user-confirmed option chain"],
            )
        return None, self._missing_status(
            CAP_OPTION_CHAIN,
            "manual option chain not provided",
            ["option chain for relevant expiry"],
        )

    def get_option_contract(
        self,
        symbol: str,
        expiry: Optional[str],
        strike: Optional[float],
        option_type: Optional[str],
    ) -> tuple[Optional[OptionContractSnapshot], ProviderStatus]:
        contract = self.manual_data.get("option_contract")
        if isinstance(contract, OptionContractSnapshot):
            return contract, ProviderStatus(
                provider_name=self.name,
                capability=CAP_OPTION_CONTRACT,
                available=True,
                status="found",
                data_quality=contract.data_quality,
                missing_fields=list(contract.missing_fields),
                notes=["manual or user-confirmed option contract"],
            )
        return None, self._missing_status(
            CAP_OPTION_CONTRACT,
            "manual option contract not provided",
            ["option mark", "option bid", "option ask", "open interest", "volume", "IV", "delta"],
        )

    def get_news(self, symbol: str) -> tuple[Optional[NewsSnapshot], ProviderStatus]:
        headlines = list(self.manual_data.get("news_headlines", []))
        if not headlines:
            return None, self._missing_status(CAP_NEWS, "manual news not provided", ["newest company news"])
        news = NewsSnapshot(
            symbol=symbol.upper(),
            headlines=headlines,
            provider_name=self.name,
            source_type="manual",
            fetched_at=datetime.utcnow(),
            data_quality=self.manual_data.get("news_data_quality", "medium"),
        )
        return news, ProviderStatus(
            provider_name=self.name,
            capability=CAP_NEWS,
            available=True,
            status="found",
            data_quality=news.data_quality,
        )

    def get_volatility(self) -> tuple[Optional[VolatilitySnapshot], ProviderStatus]:
        volatility = self.manual_data.get("volatility")
        if isinstance(volatility, VolatilitySnapshot):
            return volatility, ProviderStatus(
                provider_name=self.name,
                capability="volatility",
                available=True,
                status="found",
                data_quality=volatility.data_quality,
                missing_fields=list(volatility.missing_fields),
            )
        return None, self._missing_status(
            "volatility",
            "manual volatility data not provided",
            ["VIX", "UVIX", "Fear & Greed"],
        )

    def get_index_context(self) -> tuple[Optional[IndexContextSnapshot], ProviderStatus]:
        index_context = self.manual_data.get("index_context")
        if isinstance(index_context, IndexContextSnapshot):
            return index_context, ProviderStatus(
                provider_name=self.name,
                capability=CAP_INDEX_CONTEXT,
                available=True,
                status="found",
                data_quality=index_context.data_quality,
                missing_fields=list(index_context.missing_fields),
            )
        return None, self._missing_status(
            CAP_INDEX_CONTEXT,
            "manual index context not provided",
            ["SPY latest context", "QQQ latest context", "SOXX latest context"],
        )

    # Compatibility for older callers.
    def get_snapshot(
        self,
        symbol: str,
        option_expiry: Optional[str] = None,
        option_strike: Optional[float] = None,
        option_type: Optional[str] = None,
    ) -> MarketSnapshot:
        key = symbol.upper()
        if key in self.snapshots:
            return self.snapshots[key]
        return MarketSnapshot(
            symbol=key,
            source=self.name,
            data_quality="low",
            missing_data=[
                "realtime data unavailable",
                "underlying realtime/latest price",
                "quote timestamp",
                "option chain for relevant expiry",
                "option mark/bid/ask/open interest/volume/IV/delta",
            ],
            stock_price_provider=self.name,
            options_provider=self.name,
            news_provider=self.name,
            volatility_provider=self.name,
            data_fetched_successfully=False,
            fallback_used=self.name,
        )

    def _missing_status(self, capability: str, error: str, missing_fields: list[str]) -> ProviderStatus:
        return ProviderStatus(
            provider_name=self.name,
            capability=capability,
            available=False,
            status="missing",
            error=error,
            missing_fields=missing_fields,
            data_quality="low",
            notes=["manual provider remains available for pasted or screenshot-derived data"],
        )


def _first_present(*values):
    for value in values:
        if value is not None:
            return value
    return None


def _first_known(*values):
    for value in values:
        if value not in (None, "", "unknown"):
            return value
    return None


def _float_or_none(value) -> Optional[float]:
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


def _datetime_or_none(value) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value
    if value in (None, "", "unknown"):
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
