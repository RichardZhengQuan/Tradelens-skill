"""Best-effort public Yahoo Finance fallback provider."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone

from tradelens.data.market_snapshot import IndexContextSnapshot, ProviderStatus, QuoteSnapshot, VolatilitySnapshot
from tradelens.data.provider_base import CAP_INDEX_CONTEXT, CAP_QUOTE, CAP_UVIX, CAP_VIX, MarketDataProvider


@dataclass
class YahooProvider(MarketDataProvider):
    enabled: bool = True
    allow_fetch: bool = False
    timeout_seconds: float = 5.0
    name: str = "YahooProvider"

    def capabilities(self) -> set[str]:
        return {CAP_QUOTE, CAP_VIX, CAP_UVIX, CAP_INDEX_CONTEXT}

    def get_quote(self, symbol: str):
        if not self.enabled:
            return None, self._disabled(CAP_QUOTE)
        if not self.allow_fetch:
            return None, self._public_disabled(CAP_QUOTE, ["underlying realtime/latest price"])
        try:
            quote = self._fetch_quote(symbol)
        except Exception as exc:  # pragma: no cover - network behavior is host-dependent
            return None, ProviderStatus(
                provider_name=self.name,
                capability=CAP_QUOTE,
                available=False,
                status="unavailable",
                error=f"Yahoo quote unavailable: {exc}",
                missing_fields=["underlying realtime/latest price"],
                data_quality="low",
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
            notes=["best-effort public quote fallback"],
        )

    def get_volatility(self):
        if not self.enabled:
            return None, self._disabled(CAP_VIX)
        if not self.allow_fetch:
            return None, self._public_disabled("volatility", ["VIX", "UVIX"])
        vix = uvix = None
        errors = []
        for target in ("^VIX", "UVIX"):
            try:
                quote = self._fetch_quote(target)
            except Exception as exc:  # pragma: no cover - network behavior is host-dependent
                errors.append(f"{target}: {exc}")
                continue
            if target == "^VIX":
                vix = quote.price
            else:
                uvix = quote.price
        if vix is None and uvix is None:
            return None, ProviderStatus(
                provider_name=self.name,
                capability="volatility",
                available=False,
                status="unavailable",
                error="Yahoo VIX/UVIX unavailable",
                missing_fields=["VIX", "UVIX"],
                notes=errors,
            )
        snapshot = VolatilitySnapshot(
            vix=vix,
            uvix=uvix,
            provider_name=self.name,
            source_type="public",
            fetched_at=datetime.utcnow(),
            data_quality="medium",
            missing_fields=[] if vix is not None or uvix is not None else ["VIX", "UVIX"],
        )
        return snapshot, ProviderStatus(
            provider_name=self.name,
            capability="volatility",
            available=True,
            status="found",
            data_quality="medium",
            missing_fields=list(snapshot.missing_fields),
        )

    def get_index_context(self):
        if not self.enabled:
            return None, self._disabled(CAP_INDEX_CONTEXT)
        if not self.allow_fetch:
            return None, self._public_disabled(CAP_INDEX_CONTEXT, ["SPY latest context", "QQQ latest context", "SOXX latest context"])
        context = IndexContextSnapshot(provider_name=self.name, source_type="public", fetched_at=datetime.utcnow())
        errors = []
        for attr, symbol in (("spy", "SPY"), ("qqq", "QQQ"), ("soxx", "SOXX")):
            try:
                setattr(context, attr, self._fetch_quote(symbol))
            except Exception as exc:  # pragma: no cover - network behavior is host-dependent
                errors.append(f"{symbol}: {exc}")
                context.missing_fields.append(f"{symbol} latest context")
        context.errors = errors
        context.data_quality = "medium" if any((context.spy, context.qqq, context.soxx)) else "low"
        return (context if context.data_quality != "low" else None), ProviderStatus(
            provider_name=self.name,
            capability=CAP_INDEX_CONTEXT,
            available=context.data_quality != "low",
            status="found" if context.data_quality != "low" else "unavailable",
            error=None if context.data_quality != "low" else "Yahoo index context unavailable",
            missing_fields=list(context.missing_fields),
            notes=errors,
            data_quality=context.data_quality,
        )

    def _fetch_quote(self, symbol: str) -> QuoteSnapshot:
        encoded = urllib.parse.quote(symbol, safe="")
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}?range=1d&interval=1m&includePrePost=true"
        request = urllib.request.Request(url, headers={"User-Agent": "TradeLensSkill/1.0"})
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            data = json.loads(response.read().decode("utf-8"))
        result = data.get("chart", {}).get("result") or []
        if not result:
            raise ValueError("chart response contained no result")
        chart = result[0]
        meta = chart.get("meta", {})
        timestamps = chart.get("timestamp") or []
        close_values = (((chart.get("indicators") or {}).get("quote") or [{}])[0].get("close") or [])
        price = None
        data_time = None
        for index in range(len(close_values) - 1, -1, -1):
            if close_values[index] is not None:
                price = float(close_values[index])
                if index < len(timestamps):
                    data_time = datetime.fromtimestamp(timestamps[index], timezone.utc)
                break
        if price is None and meta.get("regularMarketPrice") is not None:
            price = float(meta["regularMarketPrice"])
            timestamp = meta.get("regularMarketTime")
            if timestamp:
                data_time = datetime.fromtimestamp(timestamp, timezone.utc)
        if price is None:
            raise ValueError("chart response contained no price")
        return QuoteSnapshot(
            symbol=symbol.upper(),
            price=price,
            session=_normalize_market_state(meta.get("marketState")),
            provider_name=self.name,
            source_type="public",
            fetched_at=datetime.utcnow(),
            data_time=data_time,
            is_realtime=None,
            is_delayed=None,
            data_quality="medium",
            missing_fields=[] if data_time else ["quote timestamp"],
        )

    def _disabled(self, capability: str) -> ProviderStatus:
        return ProviderStatus(
            provider_name=self.name,
            capability=capability,
            available=False,
            status="disabled",
            error="YahooProvider disabled",
        )

    def _public_disabled(self, capability: str, missing_fields: list[str]) -> ProviderStatus:
        return ProviderStatus(
            provider_name=self.name,
            capability=capability,
            available=False,
            status="unavailable",
            error="Yahoo public fetch disabled or unavailable in host",
            missing_fields=missing_fields,
            notes=["best-effort public fallback; enable only when host/network policy allows it"],
        )


def _normalize_market_state(value: object) -> str:
    state = str(value or "").lower()
    if "pre" in state:
        return "premarket"
    if "post" in state or "after" in state:
        return "after-hours"
    if "regular" in state or state == "open":
        return "regular"
    if "overnight" in state:
        return "overnight"
    return "unknown"
