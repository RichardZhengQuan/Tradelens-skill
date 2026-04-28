"""Optional Polygon/Massive market data provider."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from tradelens.data.market_snapshot import ProviderStatus
from tradelens.data.provider_base import (
    CAP_NEWS,
    CAP_OPTION_CHAIN,
    CAP_OPTION_GREEKS,
    CAP_OPTION_IV,
    CAP_OPTION_OPEN_INTEREST,
    CAP_OPTION_VOLUME,
    CAP_QUOTE,
    MarketDataProvider,
)


@dataclass
class PolygonProvider(MarketDataProvider):
    enabled: bool = False
    api_key_env: str = "POLYGON_API_KEY"
    name: str = "PolygonProvider"

    def capabilities(self) -> set[str]:
        return {
            CAP_QUOTE,
            CAP_OPTION_CHAIN,
            CAP_OPTION_GREEKS,
            CAP_OPTION_IV,
            CAP_OPTION_OPEN_INTEREST,
            CAP_OPTION_VOLUME,
            CAP_NEWS,
        }

    def get_quote(self, symbol: str):
        return None, self._status(CAP_QUOTE, ["underlying realtime/latest price"])

    def get_option_chain(self, symbol: str, expiry: Optional[str] = None):
        return None, self._status(CAP_OPTION_CHAIN, ["option chain", "open interest", "volume", "IV", "Greeks"])

    def get_news(self, symbol: str):
        return None, self._status(CAP_NEWS, ["newest company news"])

    def _status(self, capability: str, missing_fields: list[str]) -> ProviderStatus:
        if not self.enabled:
            return ProviderStatus(
                provider_name=self.name,
                capability=capability,
                available=False,
                status="disabled",
                error="PolygonProvider disabled",
            )
        if not os.environ.get(self.api_key_env):
            return ProviderStatus(
                provider_name=self.name,
                capability=capability,
                available=False,
                status="unavailable",
                error=f"Provider unavailable: missing environment variable {self.api_key_env}",
                missing_fields=missing_fields,
                notes=["Polygon/Massive requires an account/API key, but not a brokerage account"],
            )
        return ProviderStatus(
            provider_name=self.name,
            capability=capability,
            available=False,
            status="unavailable",
            error="Polygon request not completed by local safe adapter",
            missing_fields=missing_fields,
            notes=["Data availability depends on subscription plan"],
        )
