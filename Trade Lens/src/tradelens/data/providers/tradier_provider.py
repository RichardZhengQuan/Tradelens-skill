"""Optional Tradier market data provider."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from tradelens.data.market_snapshot import ProviderStatus
from tradelens.data.provider_base import (
    CAP_OPTION_CHAIN,
    CAP_OPTION_GREEKS,
    CAP_OPTION_IV,
    CAP_OPTION_OPEN_INTEREST,
    CAP_OPTION_VOLUME,
    CAP_QUOTE,
    MarketDataProvider,
)


@dataclass
class TradierProvider(MarketDataProvider):
    enabled: bool = False
    environment: str = "production"
    api_key_env: str = "TRADIER_API_KEY"
    name: str = "TradierProvider"

    def capabilities(self) -> set[str]:
        return {
            CAP_QUOTE,
            CAP_OPTION_CHAIN,
            CAP_OPTION_GREEKS,
            CAP_OPTION_IV,
            CAP_OPTION_OPEN_INTEREST,
            CAP_OPTION_VOLUME,
        }

    def get_quote(self, symbol: str):
        return None, self._status(CAP_QUOTE, ["underlying realtime/latest price"])

    def get_option_chain(self, symbol: str, expiry: Optional[str] = None):
        return None, self._status(
            CAP_OPTION_CHAIN,
            ["option chain", "open interest", "volume", "IV", "Greeks"],
        )

    def _status(self, capability: str, missing_fields: list[str]) -> ProviderStatus:
        if not self.enabled:
            return ProviderStatus(
                provider_name=self.name,
                capability=capability,
                available=False,
                status="disabled",
                error="TradierProvider disabled",
            )
        if not os.environ.get(self.api_key_env):
            return ProviderStatus(
                provider_name=self.name,
                capability=capability,
                available=False,
                status="unavailable",
                error=f"Provider unavailable: missing environment variable {self.api_key_env}",
                missing_fields=missing_fields,
                notes=["Tradier real-time U.S. stocks/options data generally requires a Tradier Brokerage account"],
            )
        return ProviderStatus(
            provider_name=self.name,
            capability=capability,
            available=False,
            status="unavailable",
            error="Tradier request not completed by local safe adapter",
            missing_fields=missing_fields,
            notes=["API key was read from environment only; no key was stored in markdown"],
        )
