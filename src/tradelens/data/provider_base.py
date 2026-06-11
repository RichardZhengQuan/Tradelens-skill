"""Base interface for optional market data providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
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

CAP_QUOTE = "quote"
CAP_EXTENDED_HOURS_QUOTE = "extended_hours_quote"
CAP_OVERNIGHT_QUOTE = "overnight_quote"
CAP_OPTION_CHAIN = "option_chain"
CAP_OPTION_CONTRACT = "option_contract"
CAP_OPTION_GREEKS = "option_greeks"
CAP_OPTION_IV = "option_iv"
CAP_OPTION_OPEN_INTEREST = "option_open_interest"
CAP_OPTION_VOLUME = "option_volume"
CAP_NEWS = "news"
CAP_VIX = "vix"
CAP_UVIX = "uvix"
CAP_FEAR_GREED = "fear_greed"
CAP_INDEX_CONTEXT = "index_context"
CAP_POSITIONS = "positions"
CAP_ACCOUNT_SUMMARY = "account_summary"


class MarketDataProvider(ABC):
    name: str = "base"

    def supports(self, capability: str) -> bool:
        return capability in self.capabilities()

    @abstractmethod
    def capabilities(self) -> set[str]:
        raise NotImplementedError

    def unavailable(
        self,
        capability: str,
        status: str = "unsupported",
        error: Optional[str] = None,
        missing_fields: Optional[list[str]] = None,
        notes: Optional[list[str]] = None,
    ) -> ProviderStatus:
        return ProviderStatus(
            provider_name=self.name,
            capability=capability,
            available=False,
            status=status,
            error=error or f"{capability} unsupported",
            missing_fields=missing_fields or [],
            notes=notes or [],
        )

    def get_quote(self, symbol: str) -> tuple[Optional[QuoteSnapshot], ProviderStatus]:
        return None, self.unavailable(CAP_QUOTE)

    def get_option_chain(
        self,
        symbol: str,
        expiry: Optional[str] = None,
    ) -> tuple[Optional[OptionChainSnapshot], ProviderStatus]:
        return None, self.unavailable(CAP_OPTION_CHAIN)

    def get_option_contract(
        self,
        symbol: str,
        expiry: Optional[str],
        strike: Optional[float],
        option_type: Optional[str],
    ) -> tuple[Optional[OptionContractSnapshot], ProviderStatus]:
        return None, self.unavailable(CAP_OPTION_CONTRACT)

    def get_news(self, symbol: str) -> tuple[Optional[NewsSnapshot], ProviderStatus]:
        return None, self.unavailable(CAP_NEWS)

    def get_volatility(self) -> tuple[Optional[VolatilitySnapshot], ProviderStatus]:
        return None, self.unavailable("volatility")

    def get_index_context(self) -> tuple[Optional[IndexContextSnapshot], ProviderStatus]:
        return None, self.unavailable(CAP_INDEX_CONTEXT)

    def get_positions(self) -> tuple[Optional[Any], ProviderStatus]:
        return None, self.unavailable(CAP_POSITIONS)

    def get_account_summary(self) -> tuple[Optional[Any], ProviderStatus]:
        return None, self.unavailable(CAP_ACCOUNT_SUMMARY)
