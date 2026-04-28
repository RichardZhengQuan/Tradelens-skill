"""Best-effort OptionCharts public options fallback provider."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from tradelens.data.market_snapshot import ProviderStatus
from tradelens.data.provider_base import (
    CAP_OPTION_CHAIN,
    CAP_OPTION_GREEKS,
    CAP_OPTION_IV,
    CAP_OPTION_OPEN_INTEREST,
    CAP_OPTION_VOLUME,
    MarketDataProvider,
)


@dataclass
class OptionChartsProvider(MarketDataProvider):
    enabled: bool = True
    allow_fetch: bool = False
    name: str = "OptionChartsProvider"
    url: str = "https://optioncharts.io/options/"

    def capabilities(self) -> set[str]:
        return {
            CAP_OPTION_CHAIN,
            CAP_OPTION_OPEN_INTEREST,
            CAP_OPTION_VOLUME,
            CAP_OPTION_IV,
            CAP_OPTION_GREEKS,
        }

    def get_option_chain(self, symbol: str, expiry: Optional[str] = None):
        if not self.enabled:
            return None, ProviderStatus(
                provider_name=self.name,
                capability=CAP_OPTION_CHAIN,
                available=False,
                status="disabled",
                error="OptionCharts disabled",
            )
        return None, ProviderStatus(
            provider_name=self.name,
            capability=CAP_OPTION_CHAIN,
            available=False,
            status="unavailable",
            error="OptionCharts unavailable or unsupported path",
            missing_fields=["option chain", "open interest", "volume"],
            notes=[
                self.url,
                "optional public fallback source; may require symbol-specific paths or browser access",
            ],
        )
