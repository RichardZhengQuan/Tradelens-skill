"""Shared local-first OpenD market data provider support."""

from __future__ import annotations

import importlib
import importlib.util
import socket
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from tradelens.data.cache import DEFAULT_TTLS, MarketDataCache
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
from tradelens.data.providers.opend_direct_client import OpenDDirectError, fetch_quote_direct_opend

LOCAL_OPEND_HOSTS = {"127.0.0.1", "localhost", "::1"}

OPEND_PROCESS_PATTERNS = {
    "Futu OpenD": ("Futu OpenD", "FutuOpenD", "Futubull OpenD"),
    "Moomoo OpenD": ("Moomoo OpenD", "moomoo OpenD", "MoomooOpenD"),
}

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
    security_firm: str = ""
    trading_env: str = "REAL"
    currency: str = "USD"
    account_id: int = 0
    account_index: int = 0
    provider_type: str = "unknown"
    login_name: str = "broker"
    server_name: str = "OpenD"
    last_test_status: str = "unknown"
    last_test_time: Optional[str] = None
    timeout_seconds: float = 1.0
    name: str = "OpenDProvider"
    cache: Optional[MarketDataCache] = None

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
            "security_firm": "",
            "trading_env": "REAL",
            "currency": "USD",
            "account_id": 0,
            "account_index": 0,
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
        port_reachable = self._opend_reachable()
        quote_success = bool(quote_status and quote_status.available)
        direct_quote_success = bool(
            quote_status
            and quote_status.available
            and any("direct OpenD" in note for note in quote_status.notes)
        )
        integration_installed = self._sdk_installed()
        sdk_connection_success, sdk_connection_error = self._sdk_connection_test()
        opend_reachable = port_reachable and (quote_success or sdk_connection_success)
        return OpenDProviderSetupResult(
            provider_type=self.provider_type,
            integration_available=integration_installed or direct_quote_success,
            integration_installed=integration_installed,
            opend_reachable=opend_reachable,
            host=self.host,
            port=self.port,
            read_only=self.read_only,
            trading_enabled=self.allow_trading,
            password_stored=self.store_password,
            test_quote_symbol=test_quote_symbol,
            test_quote_success=bool(quote_status and quote_status.available),
            opend_process_detected=detect_opend_process(self.provider_type),
            opend_port_reachable=port_reachable,
            direct_opend_quote_success=direct_quote_success,
            direct_opend_quote_error="" if direct_quote_success else (quote_status.error if quote_status else ""),
            python_executable=sys.executable,
            sdk_installed=integration_installed,
            sdk_connection_success=sdk_connection_success,
            sdk_connection_error=sdk_connection_error,
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

    def get_account_summary(self):
        unavailable = self._unavailable_status(CAP_ACCOUNT_SUMMARY)
        if unavailable:
            return None, unavailable
        return self._read_only_account_summary_request()

    def get_positions(self):
        unavailable = self._unavailable_status(CAP_POSITIONS)
        if unavailable:
            return None, unavailable
        return self._read_only_positions_request()

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
        if not self._opend_reachable():
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
            quote = fetch_quote_direct_opend(
                symbol,
                host=self.host,
                port=self.port,
                timeout=self.timeout_seconds,
                market=self.market,
                provider_name=self.name,
            )
            return quote, ProviderStatus(
                provider_name=self.name,
                capability=CAP_QUOTE,
                available=True,
                status="found",
                fetched_at=quote.fetched_at,
                data_time=quote.data_time,
                data_quality=quote.data_quality,
                notes=[f"Read-only direct OpenD quote request through {self.provider_type}"],
            )
        except OpenDDirectError as direct_exc:
            direct_error = str(direct_exc)

        if not self._sdk_installed():
            return None, ProviderStatus(
                provider_name=self.name,
                capability=CAP_QUOTE,
                available=False,
                status="unavailable",
                error=f"Direct OpenD quote failed and {self.sdk_display_name} package is not installed",
                fetched_at=fetched_at,
                missing_fields=["underlying realtime/latest price"],
                notes=[
                    direct_error,
                    f"Optional SDK fallback: install {self.sdk_display_name} only after explicit user approval.",
                ],
            )
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

    def _read_only_account_summary_request(self):
        fetched_at = datetime.now(timezone.utc)
        sdk, status = self._import_trade_sdk(CAP_ACCOUNT_SUMMARY, fetched_at)
        if status is not None:
            return None, status
        trade_context, status = self._open_trade_context(sdk, CAP_ACCOUNT_SUMMARY, fetched_at)
        if status is not None:
            return None, status
        try:
            query = getattr(trade_context, "accinfo_query", None)
            if not callable(query):
                return None, ProviderStatus(
                    provider_name=self.name,
                    capability=CAP_ACCOUNT_SUMMARY,
                    available=False,
                    status="unavailable",
                    error=f"{self.sdk_display_name} accinfo_query unavailable",
                    fetched_at=fetched_at,
                    missing_fields=["account summary"],
                )
            ret, data = _call_sdk_query(query, self._account_summary_query_variants(sdk))
            ret_ok = getattr(sdk, "RET_OK", 0)
            if ret != ret_ok:
                return None, ProviderStatus(
                    provider_name=self.name,
                    capability=CAP_ACCOUNT_SUMMARY,
                    available=False,
                    status="unavailable",
                    error=f"{self.provider_type} account summary query failed",
                    fetched_at=fetched_at,
                    missing_fields=["account summary"],
                    notes=[_table_or_text(data)],
                )
            rows = _records_from_table(data)
            if not rows:
                return None, ProviderStatus(
                    provider_name=self.name,
                    capability=CAP_ACCOUNT_SUMMARY,
                    available=False,
                    status="missing",
                    error=f"{self.provider_type} account summary query returned no rows",
                    fetched_at=fetched_at,
                    missing_fields=["account summary"],
                )
            account_summary = {
                "provider": self.name,
                "provider_type": self.provider_type,
                "source_type": "opend_sdk",
                "fetched_at": fetched_at.isoformat(),
                "market": self.market,
                "currency": self.currency,
                "trading_env": self.trading_env,
                "account": rows[0],
                "rows": rows,
            }
            return account_summary, ProviderStatus(
                provider_name=self.name,
                capability=CAP_ACCOUNT_SUMMARY,
                available=True,
                status="found",
                fetched_at=fetched_at,
                data_time=fetched_at,
                data_quality="high",
                notes=[f"Read-only OpenD SDK accinfo_query through {self.provider_type}"],
            )
        except Exception as exc:
            return None, ProviderStatus(
                provider_name=self.name,
                capability=CAP_ACCOUNT_SUMMARY,
                available=False,
                status="unavailable",
                error=f"{self.provider_type} account summary query failed",
                fetched_at=fetched_at,
                missing_fields=["account summary"],
                notes=[str(exc)],
            )
        finally:
            close = getattr(trade_context, "close", None)
            if callable(close):
                close()

    def _read_only_positions_request(self):
        fetched_at = datetime.now(timezone.utc)
        sdk, status = self._import_trade_sdk(CAP_POSITIONS, fetched_at)
        if status is not None:
            return None, status
        trade_context, status = self._open_trade_context(sdk, CAP_POSITIONS, fetched_at)
        if status is not None:
            return None, status
        try:
            query = getattr(trade_context, "position_list_query", None)
            if not callable(query):
                return None, ProviderStatus(
                    provider_name=self.name,
                    capability=CAP_POSITIONS,
                    available=False,
                    status="unavailable",
                    error=f"{self.sdk_display_name} position_list_query unavailable",
                    fetched_at=fetched_at,
                    missing_fields=["positions"],
                )
            ret, data = _call_sdk_query(query, self._positions_query_variants(sdk))
            ret_ok = getattr(sdk, "RET_OK", 0)
            if ret != ret_ok:
                return None, ProviderStatus(
                    provider_name=self.name,
                    capability=CAP_POSITIONS,
                    available=False,
                    status="unavailable",
                    error=f"{self.provider_type} positions query failed",
                    fetched_at=fetched_at,
                    missing_fields=["positions"],
                    notes=[_table_or_text(data)],
                )
            rows = _records_from_table(data)
            return rows, ProviderStatus(
                provider_name=self.name,
                capability=CAP_POSITIONS,
                available=True,
                status="found",
                fetched_at=fetched_at,
                data_time=fetched_at,
                data_quality="high",
                notes=[f"Read-only OpenD SDK position_list_query through {self.provider_type}"],
            )
        except Exception as exc:
            return None, ProviderStatus(
                provider_name=self.name,
                capability=CAP_POSITIONS,
                available=False,
                status="unavailable",
                error=f"{self.provider_type} positions query failed",
                fetched_at=fetched_at,
                missing_fields=["positions"],
                notes=[str(exc)],
            )
        finally:
            close = getattr(trade_context, "close", None)
            if callable(close):
                close()

    def _import_trade_sdk(self, capability: str, fetched_at: datetime):
        if not self._sdk_installed():
            return None, ProviderStatus(
                provider_name=self.name,
                capability=capability,
                available=False,
                status="unavailable",
                error=f"{self.sdk_display_name} package is required for {capability}",
                fetched_at=fetched_at,
                missing_fields=[capability],
                notes=["Direct OpenD quote path does not expose account or position APIs."],
            )
        try:
            return importlib.import_module(self.sdk_package), None
        except Exception as exc:
            return None, ProviderStatus(
                provider_name=self.name,
                capability=capability,
                available=False,
                status="unavailable",
                error=f"{self.sdk_display_name} package import failed",
                fetched_at=fetched_at,
                missing_fields=[capability],
                notes=[str(exc)],
            )

    def _open_trade_context(self, sdk, capability: str, fetched_at: datetime):
        context_class = getattr(sdk, "OpenSecTradeContext", None)
        if context_class is None:
            return None, ProviderStatus(
                provider_name=self.name,
                capability=capability,
                available=False,
                status="unavailable",
                error=f"{self.sdk_display_name} OpenSecTradeContext unavailable",
                fetched_at=fetched_at,
                missing_fields=[capability],
            )
        market = _sdk_enum_value(sdk, "TrdMarket", self.market) or _sdk_enum_value(sdk, "TrdMarket", "NONE")
        firm = _sdk_enum_value(sdk, "SecurityFirm", self._security_firm_name())
        attempts = []
        base_kwargs = {"host": self.host, "port": self.port}
        if market is not None:
            base_kwargs["filter_trdmarket"] = market
        if firm is not None:
            attempts.append({**base_kwargs, "security_firm": firm})
        attempts.append(base_kwargs)
        errors = []
        for kwargs in attempts:
            try:
                return context_class(**kwargs), None
            except TypeError as exc:
                errors.append(str(exc))
                continue
            except Exception as exc:
                return None, ProviderStatus(
                    provider_name=self.name,
                    capability=capability,
                    available=False,
                    status="unavailable",
                    error=f"{self.provider_type} trade context failed",
                    fetched_at=fetched_at,
                    missing_fields=[capability],
                    notes=[str(exc)],
                )
        return None, ProviderStatus(
            provider_name=self.name,
            capability=capability,
            available=False,
            status="unavailable",
            error=f"{self.provider_type} trade context failed",
            fetched_at=fetched_at,
            missing_fields=[capability],
            notes=errors,
        )

    def _account_summary_query_variants(self, sdk) -> list[dict[str, Any]]:
        base = self._trade_query_base_kwargs(sdk)
        currency = _sdk_enum_value(sdk, "Currency", self.currency)
        asset_category = _sdk_enum_value(sdk, "AssetCategory", "NONE")
        variants = []
        with_currency = dict(base)
        if currency is not None:
            with_currency["currency"] = currency
        if asset_category is not None:
            with_currency["asset_category"] = asset_category
        variants.append(with_currency)
        if "asset_category" in with_currency:
            without_asset_category = dict(with_currency)
            without_asset_category.pop("asset_category", None)
            variants.append(without_asset_category)
        without_currency = dict(base)
        if asset_category is not None:
            without_currency["asset_category"] = asset_category
            variants.append(without_currency)
            without_currency = dict(base)
        variants.append(without_currency)
        variants.append({})
        return _dedupe_kwargs(variants)

    def _positions_query_variants(self, sdk) -> list[dict[str, Any]]:
        base = self._trade_query_base_kwargs(sdk)
        position_market = _sdk_enum_value(sdk, "TrdMarket", "NONE")
        asset_category = _sdk_enum_value(sdk, "AssetCategory", "NONE")
        variants = []
        with_filters = dict(base)
        if position_market is not None:
            with_filters["position_market"] = position_market
        if asset_category is not None:
            with_filters["asset_category"] = asset_category
        variants.append(with_filters)
        if "asset_category" in with_filters:
            without_asset_category = dict(with_filters)
            without_asset_category.pop("asset_category", None)
            variants.append(without_asset_category)
        variants.append(base)
        variants.append({})
        return _dedupe_kwargs(variants)

    def _trade_query_base_kwargs(self, sdk) -> dict[str, Any]:
        kwargs: dict[str, Any] = {"refresh_cache": True}
        trd_env = _sdk_enum_value(sdk, "TrdEnv", self.trading_env)
        if trd_env is not None:
            kwargs["trd_env"] = trd_env
        if self.account_id:
            kwargs["acc_id"] = self.account_id
        elif self.account_index:
            kwargs["acc_index"] = self.account_index
        return kwargs

    def _security_firm_name(self) -> str:
        if self.security_firm:
            return self.security_firm
        if self.account_type == "moomoo":
            return "FUTUINC" if self.market.upper() == "US" else "FUTUSECURITIES"
        return "FUTUSECURITIES"

    def _format_symbol(self, symbol: str) -> str:
        cleaned = symbol.strip().upper()
        if "." in cleaned:
            return cleaned
        return f"{self.market.upper()}.{cleaned}"

    def _sdk_installed(self) -> bool:
        if not self.sdk_package:
            return False
        key = f"opend:sdk:{self.sdk_package}"
        if self.cache is None:
            return importlib.util.find_spec(self.sdk_package) is not None
        return bool(
            self.cache.get_or_set(
                key,
                DEFAULT_TTLS["opend_preflight"],
                lambda: importlib.util.find_spec(self.sdk_package) is not None,
            )
        )

    def _opend_reachable(self) -> bool:
        key = f"opend:reachable:{self.host}:{self.port}"
        if self.cache is None:
            return is_opend_reachable(self.host, self.port, self.timeout_seconds)
        return bool(
            self.cache.get_or_set(
                key,
                DEFAULT_TTLS["opend_preflight"],
                lambda: is_opend_reachable(self.host, self.port, self.timeout_seconds),
            )
        )

    def _sdk_connection_test(self) -> tuple[bool, str]:
        if not self._sdk_installed():
            return False, f"{self.sdk_display_name} package not installed"
        if not self._opend_reachable():
            return False, f"{self.provider_type} port is not reachable"
        try:
            sdk = importlib.import_module(self.sdk_package)
        except Exception as exc:
            return False, f"{self.sdk_display_name} package import failed: {exc}"
        quote_context_class = getattr(sdk, "OpenQuoteContext", None)
        if quote_context_class is None:
            return False, f"{self.sdk_display_name} OpenQuoteContext unavailable"
        quote_context = None
        try:
            quote_context = quote_context_class(host=self.host, port=self.port)
        except Exception as exc:
            return False, f"{self.provider_type} SDK connection failed: {exc}"
        finally:
            close = getattr(quote_context, "close", None)
            if callable(close):
                close()
        return True, ""


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


def detect_opend_process(provider_type: str) -> bool:
    patterns = OPEND_PROCESS_PATTERNS.get(provider_type, ())
    if not patterns:
        return False
    try:
        result = subprocess.run(
            ["pgrep", "-fl", "|".join(patterns)],
            check=False,
            capture_output=True,
            text=True,
            timeout=1,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    output = result.stdout or ""
    return result.returncode == 0 and any(pattern.lower() in output.lower() for pattern in patterns)


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


def _call_sdk_query(query, variants: list[dict[str, Any]]):
    last_type_error = None
    for kwargs in variants:
        try:
            return query(**kwargs)
        except TypeError as exc:
            last_type_error = exc
            continue
    if last_type_error is not None:
        raise last_type_error
    return query()


def _records_from_table(data: Any) -> list[dict[str, Any]]:
    if data is None:
        return []
    if hasattr(data, "to_dict"):
        try:
            records = data.to_dict(orient="records")
            if isinstance(records, list):
                return [_plain_record(record) for record in records]
        except Exception:
            pass
    if isinstance(data, list):
        return [_plain_record(item) for item in data]
    if isinstance(data, tuple):
        return [_plain_record(item) for item in data]
    if isinstance(data, dict):
        nested = data.get("data")
        if nested is not None and nested is not data:
            nested_records = _records_from_table(nested)
            if nested_records:
                return nested_records
        return [_plain_record(data)]
    row = _first_row(data)
    return [] if row is None else [_plain_record(row)]


def _plain_record(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return {str(key): _plain_value(item) for key, item in value.items()}
    if hasattr(value, "to_dict"):
        try:
            item = value.to_dict()
            if isinstance(item, dict):
                return {str(key): _plain_value(raw) for key, raw in item.items()}
        except Exception:
            pass
    return {"value": _plain_value(value)}


def _plain_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    try:
        if value != value:
            return None
    except Exception:
        pass
    item = getattr(value, "item", None)
    if callable(item):
        try:
            return item()
        except Exception:
            pass
    return str(value)


def _sdk_enum_value(sdk, enum_name: str, value_name: str):
    enum = getattr(sdk, enum_name, None)
    if enum is None:
        return None
    normalized = str(value_name or "").strip()
    if not normalized:
        return None
    candidates = [
        normalized,
        normalized.upper(),
        normalized.lower(),
        normalized.capitalize(),
    ]
    aliases = {
        "REAL": ["REAL", "Real"],
        "SIMULATE": ["SIMULATE", "Simulate"],
        "NONE": ["NONE", "None"],
        "USD": ["USD", "Usd"],
        "HKD": ["HKD", "Hkd"],
        "US": ["US", "Us"],
        "HK": ["HK", "Hk"],
        "FUTUINC": ["FUTUINC", "FutuInc"],
        "FUTUSECURITIES": ["FUTUSECURITIES", "FutuSecurities"],
        "FUTUSG": ["FUTUSG", "FutuSg"],
        "FUTUAU": ["FUTUAU", "FutuAu"],
    }
    candidates.extend(aliases.get(normalized.upper(), []))
    for candidate in candidates:
        if hasattr(enum, candidate):
            return getattr(enum, candidate)
    return None


def _dedupe_kwargs(variants: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped = []
    seen = set()
    for kwargs in variants:
        marker = tuple(sorted((key, repr(value)) for key, value in kwargs.items()))
        if marker in seen:
            continue
        seen.add(marker)
        deduped.append(kwargs)
    return deduped


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
