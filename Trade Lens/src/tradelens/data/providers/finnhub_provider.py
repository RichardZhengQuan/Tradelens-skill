"""Optional Finnhub market data provider."""

from __future__ import annotations

import os
from dataclasses import dataclass

from tradelens.data.market_snapshot import ProviderStatus
from tradelens.data.provider_base import CAP_NEWS, CAP_QUOTE, CAP_VIX, MarketDataProvider


@dataclass
class FinnhubProvider(MarketDataProvider):
    enabled: bool = False
    api_key_env: str = "FINNHUB_API_KEY"
    name: str = "FinnhubProvider"

    def capabilities(self) -> set[str]:
        return {CAP_QUOTE, CAP_NEWS, CAP_VIX}

    def get_quote(self, symbol: str):
        return None, self._status(CAP_QUOTE, ["underlying realtime/latest price"])

    def get_news(self, symbol: str):
        return None, self._status(CAP_NEWS, ["newest company news"])

    def get_volatility(self):
        return None, self._status(CAP_VIX, ["VIX"])

    def _status(self, capability: str, missing_fields: list[str]) -> ProviderStatus:
        if not self.enabled:
            return ProviderStatus(
                provider_name=self.name,
                capability=capability,
                available=False,
                status="disabled",
                error="FinnhubProvider disabled",
            )
        if not os.environ.get(self.api_key_env):
            return ProviderStatus(
                provider_name=self.name,
                capability=capability,
                available=False,
                status="unavailable",
                error=f"Provider unavailable: missing environment variable {self.api_key_env}",
                missing_fields=missing_fields,
                notes=["Finnhub is useful for quote/news fallback but requires an API key"],
            )
        return ProviderStatus(
            provider_name=self.name,
            capability=capability,
            available=False,
            status="unavailable",
            error="Finnhub request not completed by local safe adapter",
            missing_fields=missing_fields,
        )
