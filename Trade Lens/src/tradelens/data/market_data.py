"""Market data freshness helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from tradelens.models import MarketSnapshot


def _snapshot_timestamp(snapshot: MarketSnapshot) -> str:
    if snapshot.quote_timestamp not in ("unknown", "", None):
        return snapshot.quote_timestamp
    return snapshot.last_updated


def classify_data_quality(snapshot: MarketSnapshot, max_age_minutes: Optional[int] = None) -> str:
    if (
        snapshot.regular_hours_price is None
        and snapshot.premarket_price is None
        and snapshot.after_hours_price is None
        and snapshot.twenty_four_hour_price is None
    ):
        return "low"
    timestamp = _snapshot_timestamp(snapshot)
    if timestamp in ("unknown", "", None):
        return "medium" if max_age_minutes is None else "low"
    if max_age_minutes is None:
        return snapshot.data_quality if snapshot.data_quality in {"high", "medium", "low"} else "medium"
    try:
        updated = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=timezone.utc)
        age_minutes = (datetime.now(timezone.utc) - updated).total_seconds() / 60
    except ValueError:
        return "low"
    return "high" if age_minutes <= max_age_minutes else "low"


def available_underlying_price(snapshot: MarketSnapshot) -> Optional[float]:
    for value in (
        snapshot.regular_hours_price,
        snapshot.after_hours_price,
        snapshot.premarket_price,
        snapshot.twenty_four_hour_price,
    ):
        if value is not None:
            return value
    return None
