"""Per-run TTL cache for market-data lookups."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Generic, Optional, TypeVar

T = TypeVar("T")

DEFAULT_TTLS = {
    "quote": 15,
    "vix": 30,
    "uvix": 30,
    "index_context": 30,
    "news": 600,
    "fear_greed": 1800,
    "option_chain": 60,
    "opend_preflight": 60,
}


@dataclass
class CacheEntry(Generic[T]):
    value: T
    expires_at: float


@dataclass
class MarketDataCache:
    _entries: dict[str, CacheEntry] = field(default_factory=dict)

    def get(self, key: str):
        entry = self._entries.get(key)
        if entry is None:
            return None
        if entry.expires_at < time.monotonic():
            self._entries.pop(key, None)
            return None
        return entry.value

    def set(self, key: str, value, ttl_seconds: int | float) -> None:
        self._entries[key] = CacheEntry(value=value, expires_at=time.monotonic() + ttl_seconds)

    def get_or_set(self, key: str, ttl_seconds: int | float, fetch_fn: Callable[[], T]) -> T:
        cached = self.get(key)
        if cached is not None:
            return cached
        value = fetch_fn()
        self.set(key, value, ttl_seconds)
        return value
