"""Best-effort CNN Fear & Greed public fallback provider."""

from __future__ import annotations

from dataclasses import dataclass

from tradelens.data.market_snapshot import ProviderStatus
from tradelens.data.provider_base import CAP_FEAR_GREED, MarketDataProvider


@dataclass
class CNNFearGreedProvider(MarketDataProvider):
    enabled: bool = True
    allow_fetch: bool = False
    name: str = "CNNFearGreedProvider"
    url: str = "https://www.cnn.com/markets/fear-and-greed"

    def capabilities(self) -> set[str]:
        return {CAP_FEAR_GREED}

    def get_volatility(self):
        if not self.enabled:
            return None, ProviderStatus(
                provider_name=self.name,
                capability=CAP_FEAR_GREED,
                available=False,
                status="disabled",
                error="CNN Fear & Greed disabled",
            )
        return None, ProviderStatus(
            provider_name=self.name,
            capability=CAP_FEAR_GREED,
            available=False,
            status="unavailable",
            error="CNN Fear & Greed unavailable or blocked",
            missing_fields=["Fear & Greed"],
            notes=[
                self.url,
                "optional public fallback source; may block automated fetching or require browser access",
            ],
        )
