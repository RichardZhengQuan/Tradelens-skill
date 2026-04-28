"""Shared local-first OpenD market data provider support."""

from __future__ import annotations

import importlib
import importlib.util
import socket
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from tradelens.data.market_snapshot import OpenDProviderSetupResult, ProviderStatus, QuoteSnapshot
from tradelens.data.provider_base import (
    CAP_ACCOUNT_SUMMARY,
    CAP_EXTENDED_HOURS_QUOTE,
    CAP_OPTION_CHAIN,
    CAP_OPTION_GREEKS,
    CAP_OPTION_IV,
    CAP_OPTION_OPEN_INTEREST,
    CAP_OPTION_VOLUME,
    CAP_POSITIONS,
    CAP_QUOTE,
    CAP_UVIX,
    MarketDataProvider,
)

LOCAL_OPEND_HOSTS = {"127.0.0.1", "localhost", "::1"}

OPEND_DEFAULT_CONFIG = {
    "default_provider": "auto",
    "host": "127.0.0.1",
    "port": 11111,
    "require_local_opend": True,
    "read_only": True,
    "allow_trading": False,
    "store_password": False,
    "allow_remote_host": False,
}


@dataclass(frozen=True)
class OpenDDetectionResult:
    selected_provider: Optional[str]
    ambiguous: bool
    futu_sdk_installed: bool
    moomoo_sdk_installed: bool
    local_opend_reachable: bool
    reasons: tuple[str, ...] = ()


@dataclass
class OpenDProvider(MarketDataProvider):
    enabled: bool = False
    host: str = "127.0.0.1"
    port: int = 11111
    market: str = "US"
    account_type: str = "opend"
    require_local_opend: bool = True
    read_only: bool = True
    allow_trading: bool = False
    store_password: bool = False
    allow_remote_host: bool = False
    sdk_package: str = ""
    sdk_display_name: str = "OpenD SDK"
    provider_type: str = "unknown"
    login_name: str = "broker"
    server_name: str = "OpenD"
    last_test_status: str = "unknown"
    last_test_time: Optional[str] = None
    timeout_seconds: float = 1.0
    name: str = "OpenDProvider"

    @classmethod
    def default_config(cls) -> dict:
        if cls is OpenDProvider:
            return dict(OPEND_DEFAULT_CONFIG)
        return cls.provider_default_config()

    @classmethod
    def provider_default_config(cls) -> dict:
        return {
            "enabled": False,
            "host": "127.0.0.1",
            "port": 11111,
            "market": "US",
            "account_type": getattr(cls, "account_type", "opend"),
            "require_local_opend": True,
            "read_only": True,
            "allow_trading": False,
            "store_password": False,
            "allow_remote_host": False,
            "sdk_package": getattr(cls, "sdk_package", ""),
            "last_test_status": "unknown",
            "last_test_time": "",
        }

    def capabilities(self) -> set[str]:
        return {
            CAP_QUOTE,
            CAP_EXTENDED_HOURS_QUOTE,
            CAP_OPTION_CHAIN,
            CAP_POSITIONS,
            CAP_ACCOUNT_SUMMARY,
            CAP_UVIX,
            CAP_OPTION_OPEN_INTEREST,
            CAP_OPTION_VOLUME,
            CAP_OPTION_IV,
            CAP_OPTION_GREEKS,
        }

    def setup_result_from_statuses(
        self,
        statuses: list[ProviderStatus],
        test_quote_symbol: str = "SPY",
    ) -> OpenDProviderSetupResult:
        provider_statuses = [status for status in statuses if status.provider_name == self.name]
        quote_status = next((status for status in provider_statuses if status.capability == CAP_QUOTE), None)
        first_error = next((status.error for status in provider_statuses if status.error), None)
        integration_installed = self._sdk_installed()
        opend_reachable = integration_installed and bool(provider_statuses) and not any(
            _is_opend_reachability_error(status.error) for status in provider_statuses
        )
        return OpenDProviderSetupResult(
            provider_type=self.provider_type,
            integration_available=integration_installed,
            integration_installed=integration_installed,
            opend_reachable=opend_reachable,
            host=self.host,
            port=self.port,
            read_only=self.read_only,
            trading_enabled=self.allow_trading,
            password_stored=self.store_password,
            test_quote_symbol=test_quote_symbol,
            test_quote_success=bool(quote_status and quote_status.available),
            error=first_error,
            warnings=_ordered_unique([note for status in provider_statuses for note in status.notes]),
        )

    def get_quote(self, symbol: str) -> tuple[Optional[QuoteSnapshot], ProviderStatus]:
        unavailable = self._unavailable_status(CAP_QUOTE)
        if unavailable:
            return None, unavailable
        return self._read_only_quote_request(symbol)

    def get_option_chain(self, symbol: str, expiry: Optional[str] = None):
        unavailable = self._unavailable_status(CAP_OPTION_CHAIN)
        if unavailable:
            return None, unavailable
        return None, ProviderStatus(
            provider_name=self.name,
            capability=CAP_OPTION_CHAIN,
            available=False,
            status="unavailable",
            error="Permission missing or market data unavailable",
            missing_fields=["option chain", "open interest", "volume", "IV", "Greeks"],
            notes=[f"Do not assume U.S. options Greeks/OI are available from {self.provider_type}"],
        )

    def get_volatility(self):
        unavailable = self._unavailable_status(CAP_UVIX)
        if unavailable:
            return None, unavailable
        return None, ProviderStatus(
            provider_name=self.name,
            capability=CAP_UVIX,
            available=False,
            status="unavailable",
            error="Permission missing or market data unavailable",
            missing_fields=["UVIX"],
        )

    def _unavailable_status(self, capability: str) -> Optional[ProviderStatus]:
        if not self.enabled:
            return ProviderStatus(
                provider_name=self.name,
                capability=capability,
                available=False,
                status="disabled",
                error=f"{self.name} disabled",
            )
        if self.store_password:
            return ProviderStatus(
                provider_name=self.name,
                capability=capability,
                available=False,
                status="invalid_config",
                error=f"{self.name} must not store broker password",
            )
        if not self.read_only:
            return ProviderStatus(
                provider_name=self.name,
                capability=capability,
                available=False,
                status="invalid_config",
                error=f"{self.name} must remain read-only",
            )
        if self.allow_trading:
            return ProviderStatus(
                provider_name=self.name,
                capability=capability,
                available=False,
                status="invalid_config",
                error=f"{self.name} must not enable trading",
            )
        if not is_local_opend_host(self.host) and not self.allow_remote_host:
            return ProviderStatus(
                provider_name=self.name,
                capability=capability,
                available=False,
                status="invalid_config",
                error="Remote OpenD host is disabled by default for account safety.",
            )
        if self.require_local_opend and not is_local_opend_host(self.host):
            return ProviderStatus(
                provider_name=self.name,
                capability=capability,
                available=False,
                status="invalid_config",
                error=f"{self.name} requires local OpenD when require_local_opend is true",
            )
        if not self._sdk_installed():
            return ProviderStatus(
                provider_name=self.name,
                capability=capability,
                available=False,
                status="unavailable",
                error=f"{self.sdk_display_name} package not installed",
                notes=[f"Do not silently install {self.sdk_display_name}; ask the user first."],
            )
        if not is_opend_reachable(self.host, self.port, self.timeout_seconds):
            return ProviderStatus(
                provider_name=self.name,
                capability=capability,
                available=False,
                status="unavailable",
                error=f"{self.provider_type} not reachable",
            )
        return None

    def _read_only_quote_request(self, symbol: str) -> tuple[Optional[QuoteSnapshot], ProviderStatus]:
        fetched_at = datetime.now(timezone.utc)
        try:
            sdk = importlib.import_module(self.sdk_package)
        except Exception as exc:
            return None, ProviderStatus(
                provider_name=self.name,
                capability=CAP_QUOTE,
                available=False,
                status="unavailable",
                error=f"{self.sdk_display_name} package import failed",
                fetched_at=fetched_at,
                notes=[str(exc)],
            )

        quote_context_class = getattr(sdk, "OpenQuoteContext", None)
        if quote_context_class is None:
            return None, ProviderStatus(
                provider_name=self.name,
                capability=CAP_QUOTE,
                available=False,
                status="unavailable",
                error=f"{self.sdk_display_name} OpenQuoteContext unavailable",
            )

        quote_context = None
        try:
            quote_context = quote_context_class(host=self.host, port=self.port)
            ret, data = quote_context.get_market_snapshot([self._format_symbol(symbol)])
            ret_ok = getattr(sdk, "RET_OK", 0)
            if ret != ret_ok:
                return None, ProviderStatus(
                    provider_name=self.name,
                    capability=CAP_QUOTE,
                    available=False,
                    status="unavailable",
                    error=f"{self.provider_type} quote request failed",
                    fetched_at=fetched_at,
                    notes=[_table_or_text(data)],
                )
            price = _extract_price(data)
            if price is None:
                return None, ProviderStatus(
                    provider_name=self.name,
                    capability=CAP_QUOTE,
                    available=False,
                    status="unavailable",
                    error="Permission missing or market data unavailable",
                    fetched_at=fetched_at,
                    missing_fields=["underlying realtime/latest price"],
                    notes=[f"{self.provider_type} access depends on OpenD permissions and market subscriptions"],
                )
            quote = QuoteSnapshot(
                symbol=symbol.upper(),
                price=price,
                provider_name=self.name,
                source_type="opend",
                fetched_at=fetched_at,
                data_time=fetched_at,
                data_quality="medium",
            )
            return quote, ProviderStatus(
                provider_name=self.name,
                capability=CAP_QUOTE,
                available=True,
                status="found",
                fetched_at=fetched_at,
                data_time=fetched_at,
                data_quality="medium",
                notes=[f"Read-only quote request through {self.provider_type}"],
            )
        except Exception as exc:
            return None, ProviderStatus(
                provider_name=self.name,
                capability=CAP_QUOTE,
                available=False,
                status="unavailable",
                error=f"{self.provider_type} quote request failed",
                fetched_at=fetched_at,
                notes=[str(exc)],
            )
        finally:
            close = getattr(quote_context, "close", None)
            if callable(close):
                close()

    def _format_symbol(self, symbol: str) -> str:
        cleaned = symbol.strip().upper()
        if "." in cleaned:
            return cleaned
        return f"{self.market.upper()}.{cleaned}"

    def _sdk_installed(self) -> bool:
        return bool(self.sdk_package) and importlib.util.find_spec(self.sdk_package) is not None


def detect_opend_provider(
    host: str = "127.0.0.1",
    port: int = 11111,
    timeout_seconds: float = 1.0,
) -> OpenDDetectionResult:
    futu_sdk_installed = importlib.util.find_spec("futu") is not None
    moomoo_sdk_installed = importlib.util.find_spec("moomoo") is not None
    local_reachable = is_local_opend_host(host) and is_opend_reachable(host, port, timeout_seconds)
    candidates = []
    if futu_sdk_installed:
        candidates.append("futu-opend")
    if moomoo_sdk_installed:
        candidates.append("moomoo-opend")

    if len(candidates) == 1:
        return OpenDDetectionResult(
            selected_provider=candidates[0],
            ambiguous=False,
            futu_sdk_installed=futu_sdk_installed,
            moomoo_sdk_installed=moomoo_sdk_installed,
            local_opend_reachable=local_reachable,
            reasons=(f"{candidates[0]} SDK package is installed",),
        )

    reasons = []
    if not candidates:
        reasons.append("No Futu or moomoo OpenD SDK package is installed.")
    else:
        reasons.append("Both Futu and moomoo OpenD SDK packages are installed.")
    if local_reachable:
        reasons.append("A local OpenD gateway is reachable, but the server family is still ambiguous.")
    else:
        reasons.append("Local OpenD is not reachable at the configured host and port.")
    reasons.append("Choose Futu OpenD or Moomoo OpenD explicitly.")
    return OpenDDetectionResult(
        selected_provider=None,
        ambiguous=True,
        futu_sdk_installed=futu_sdk_installed,
        moomoo_sdk_installed=moomoo_sdk_installed,
        local_opend_reachable=local_reachable,
        reasons=tuple(reasons),
    )


def is_local_opend_host(host: str) -> bool:
    return host.strip().lower() in LOCAL_OPEND_HOSTS


def is_opend_reachable(host: str, port: int, timeout_seconds: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout_seconds):
            return True
    except OSError:
        return False


def _extract_price(data: Any) -> Optional[float]:
    row = _first_row(data)
    if row is None:
        return None
    for key in ("last_price", "price", "cur_price", "latest_price"):
        price = _row_get(row, key)
        coerced = _coerce_float(price)
        if coerced is not None:
            return coerced
    return None


def _first_row(data: Any) -> Any:
    if data is None:
        return None
    if hasattr(data, "empty") and hasattr(data, "iloc"):
        if data.empty:
            return None
        return data.iloc[0]
    if isinstance(data, list):
        return data[0] if data else None
    if isinstance(data, tuple):
        return data[0] if data else None
    if isinstance(data, dict):
        if "data" in data:
            return _first_row(data["data"])
        return data
    return data


def _row_get(row: Any, key: str) -> Any:
    if isinstance(row, dict):
        return row.get(key)
    try:
        return row[key]
    except Exception:
        return getattr(row, key, None)


def _coerce_float(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _table_or_text(value: Any) -> str:
    text = str(value)
    return text.replace("\n", " ")[:300]


def _is_opend_reachability_error(error: Optional[str]) -> bool:
    if not error:
        return False
    lowered = error.lower()
    return "not reachable" in lowered or "remote opend host" in lowered or "requires local opend" in lowered


def _ordered_unique(items: list[str]) -> list[str]:
    seen = set()
    unique = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            unique.append(item)
    return unique
