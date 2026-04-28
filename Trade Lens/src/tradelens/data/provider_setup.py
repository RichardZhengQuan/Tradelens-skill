"""Provider setup registry and safe setup guidance."""

from __future__ import annotations

import importlib.util
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from tradelens.data.providers.opend_base_provider import is_opend_reachable


PROVIDER_TYPE_BROKER_GATEWAY = "broker_gateway"
PROVIDER_TYPE_API_PROVIDER = "api_provider"
PROVIDER_TYPE_PUBLIC_FALLBACK = "public_fallback"
PROVIDER_TYPE_MANUAL = "manual"


@dataclass(frozen=True)
class ProviderSetupInfo:
    provider_id: str
    display_name: str
    provider_type: str
    required_components: list[str] = field(default_factory=list)
    optional_components: list[str] = field(default_factory=list)
    official_setup_url: str = ""
    official_docs_url: str = ""
    sdk_package_name: str = ""
    sdk_install_command: str = ""
    env_vars_required: list[str] = field(default_factory=list)
    account_required: bool = False
    brokerage_account_required: bool = False
    password_required_by_tradelens: bool = False
    stores_secret_in_markdown: bool = False
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ProviderSetupStatus:
    provider_id: str
    installed: bool
    configured: bool
    reachable: bool
    missing_components: list[str] = field(default_factory=list)
    setup_url: str = ""
    docs_url: str = ""
    next_steps: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


PROVIDER_SETUP_REGISTRY: dict[str, ProviderSetupInfo] = {
    "futu-opend": ProviderSetupInfo(
        provider_id="futu-opend",
        display_name="Futu OpenD",
        provider_type=PROVIDER_TYPE_BROKER_GATEWAY,
        required_components=[
            "Futu OpenD app/gateway",
            "Futu or Futubull account",
            "local OpenD running",
            "quote/data permission if needed",
        ],
        optional_components=["Python futu-api SDK"],
        official_setup_url="https://www.futunn.com/en/download/OpenAPI",
        official_docs_url="https://openapi.futunn.com/futu-api-doc/en/quick/opend-base.html",
        sdk_package_name="futu-api",
        sdk_install_command="pip install futu-api",
        account_required=True,
        brokerage_account_required=False,
        password_required_by_tradelens=False,
        stores_secret_in_markdown=False,
        notes=[
            "Futu OpenD is a gateway app.",
            "User logs in through official Futu/OpenD flow.",
            "TradeLens connects only to local OpenD.",
            "TradeLens never asks for or stores Futu password.",
            "Default host should be 127.0.0.1.",
            "Trading must remain disabled by default.",
            "Brokerage account or paid data permission may be required for some market data.",
        ],
    ),
    "moomoo-opend": ProviderSetupInfo(
        provider_id="moomoo-opend",
        display_name="Moomoo OpenD",
        provider_type=PROVIDER_TYPE_BROKER_GATEWAY,
        required_components=[
            "Moomoo OpenD app/gateway",
            "Moomoo account",
            "local OpenD running",
            "quote/data permission if needed",
        ],
        optional_components=["Python moomoo-api SDK"],
        official_setup_url="https://www.moomoo.com/download/OpenAPI",
        official_docs_url="https://openapi.moomoo.com/moomoo-api-doc/en/quick/opend-base.html",
        sdk_package_name="moomoo-api",
        sdk_install_command="pip install moomoo-api",
        account_required=True,
        brokerage_account_required=False,
        password_required_by_tradelens=False,
        stores_secret_in_markdown=False,
        notes=[
            "Moomoo OpenD is separate from Futu OpenD.",
            "User logs in through official moomoo/OpenD flow.",
            "TradeLens connects only to local OpenD.",
            "TradeLens never asks for or stores moomoo password.",
            "Default host should be 127.0.0.1.",
            "Trading must remain disabled by default.",
            "Brokerage account or paid data permission may be required for some market data.",
        ],
    ),
    "tradier": ProviderSetupInfo(
        provider_id="tradier",
        display_name="Tradier",
        provider_type=PROVIDER_TYPE_API_PROVIDER,
        required_components=["Tradier API token", "TRADIER_API_KEY environment variable"],
        official_setup_url="https://docs.tradier.com/",
        official_docs_url="https://docs.tradier.com/",
        env_vars_required=["TRADIER_API_KEY"],
        account_required=True,
        brokerage_account_required=True,
        password_required_by_tradelens=False,
        stores_secret_in_markdown=False,
        notes=[
            "Use environment variable only.",
            "Do not store API key in market_data.md.",
            "If missing, provider is unavailable but analysis can continue.",
            "Brokerage account is required for real-time U.S. stocks/options data.",
        ],
    ),
    "polygon": ProviderSetupInfo(
        provider_id="polygon",
        display_name="Polygon / Massive",
        provider_type=PROVIDER_TYPE_API_PROVIDER,
        required_components=["Polygon API key", "POLYGON_API_KEY environment variable"],
        official_setup_url="https://polygon.io/",
        official_docs_url="https://polygon.io/docs",
        env_vars_required=["POLYGON_API_KEY"],
        account_required=True,
        brokerage_account_required=False,
        password_required_by_tradelens=False,
        stores_secret_in_markdown=False,
        notes=[
            "Requires account/API key.",
            "Does not require brokerage account.",
            "Data availability depends on plan.",
            "Do not store API key in markdown.",
        ],
    ),
    "finnhub": ProviderSetupInfo(
        provider_id="finnhub",
        display_name="Finnhub",
        provider_type=PROVIDER_TYPE_API_PROVIDER,
        required_components=["Finnhub API key", "FINNHUB_API_KEY environment variable"],
        official_setup_url="https://finnhub.io/",
        official_docs_url="https://finnhub.io/docs/api",
        env_vars_required=["FINNHUB_API_KEY"],
        account_required=True,
        brokerage_account_required=False,
        password_required_by_tradelens=False,
        stores_secret_in_markdown=False,
        notes=[
            "Good quote/news fallback.",
            "Do not assume full options support.",
        ],
    ),
    "yahoo": ProviderSetupInfo(
        provider_id="yahoo",
        display_name="Yahoo public quote fallback",
        provider_type=PROVIDER_TYPE_PUBLIC_FALLBACK,
        official_setup_url="https://finance.yahoo.com/",
        official_docs_url="https://finance.yahoo.com/",
        account_required=False,
        brokerage_account_required=False,
        password_required_by_tradelens=False,
        stores_secret_in_markdown=False,
        notes=[
            "Best-effort public fallback only.",
            "Do not rely on it for broker-grade options analysis.",
        ],
    ),
    "cnn-fear-greed": ProviderSetupInfo(
        provider_id="cnn-fear-greed",
        display_name="CNN Fear & Greed",
        provider_type=PROVIDER_TYPE_PUBLIC_FALLBACK,
        official_setup_url="https://www.cnn.com/markets/fear-and-greed",
        official_docs_url="https://www.cnn.com/markets/fear-and-greed",
        account_required=False,
        brokerage_account_required=False,
        password_required_by_tradelens=False,
        stores_secret_in_markdown=False,
        notes=[
            "Best-effort public sentiment fallback.",
            "May block automated fetching.",
            "Never fake value.",
        ],
    ),
    "optioncharts": ProviderSetupInfo(
        provider_id="optioncharts",
        display_name="OptionCharts",
        provider_type=PROVIDER_TYPE_PUBLIC_FALLBACK,
        official_setup_url="https://optioncharts.io/options/",
        official_docs_url="https://optioncharts.io/options/",
        account_required=False,
        brokerage_account_required=False,
        password_required_by_tradelens=False,
        stores_secret_in_markdown=False,
        notes=[
            "Best-effort public options/OI fallback.",
            "May require symbol-specific path.",
            "Never fake option-chain/OI/IV/Greeks.",
        ],
    ),
}


_PROVIDER_ALIASES = {
    "futu": "futu-opend",
    "futu-opend": "futu-opend",
    "futud": "futu-opend",
    "moomoo": "moomoo-opend",
    "moomoo-opend": "moomoo-opend",
    "moomoo openapi": "moomoo-opend",
    "polygon": "polygon",
    "massive": "polygon",
    "tradier": "tradier",
    "finnhub": "finnhub",
    "yahoo": "yahoo",
    "feargreed": "cnn-fear-greed",
    "fear greed": "cnn-fear-greed",
    "cnn": "cnn-fear-greed",
    "cnn-fear-greed": "cnn-fear-greed",
    "cnn fear greed": "cnn-fear-greed",
    "optioncharts": "optioncharts",
    "option charts": "optioncharts",
}

_SDK_IMPORT_MODULES = {
    "futu-api": "futu",
    "moomoo-api": "moomoo",
}

_OPEND_APP_NAMES = {
    "futu-opend": (
        "Futu OpenD.app",
        "FutuOpenD.app",
        "Futubull OpenD.app",
    ),
    "moomoo-opend": (
        "Moomoo OpenD.app",
        "moomoo OpenD.app",
        "MoomooOpenD.app",
    ),
}

_PROVIDER_MARKET_DATA_KEYS = {
    "futu-opend": ("futu_opend", "futu"),
    "moomoo-opend": ("moomoo_opend",),
    "tradier": ("tradier",),
    "polygon": ("polygon",),
    "finnhub": ("finnhub",),
    "yahoo": ("yahoo",),
}


def normalize_provider_id(provider_name: str) -> str | None:
    normalized = _normalize_provider_name(provider_name)
    return _PROVIDER_ALIASES.get(normalized)


def get_provider_setup_info(provider_name: str) -> ProviderSetupInfo | None:
    provider_id = normalize_provider_id(provider_name)
    if provider_id is None:
        return None
    return PROVIDER_SETUP_REGISTRY.get(provider_id)


def check_provider_setup_status(
    provider_name: str,
    root: Path | str | None = None,
    host: str = "127.0.0.1",
    port: int = 11111,
    timeout_seconds: float = 1.0,
) -> ProviderSetupStatus:
    provider_id = normalize_provider_id(provider_name)
    if provider_id is None or provider_id not in PROVIDER_SETUP_REGISTRY:
        raise ValueError(f"Unknown provider setup target: {provider_name}")
    info = PROVIDER_SETUP_REGISTRY[provider_id]
    root_path = Path(root) if root is not None else None

    if info.provider_type == PROVIDER_TYPE_BROKER_GATEWAY:
        return _check_broker_gateway_setup(info, root_path, host, port, timeout_seconds)
    if info.provider_type == PROVIDER_TYPE_API_PROVIDER:
        return _check_api_provider_setup(info)
    return _check_public_fallback_setup(info)


def render_provider_setup(
    provider_name: str,
    root: Path | str | None = None,
    host: str = "127.0.0.1",
    port: int = 11111,
) -> str:
    provider_id = normalize_provider_id(provider_name)
    if provider_id is None:
        return _render_unknown_provider(provider_name)
    info = PROVIDER_SETUP_REGISTRY[provider_id]
    status = check_provider_setup_status(provider_id, root=root, host=host, port=port)
    if info.provider_type == PROVIDER_TYPE_BROKER_GATEWAY:
        return _render_broker_gateway_setup(info, status, host, port)
    if info.provider_type == PROVIDER_TYPE_API_PROVIDER:
        return _render_api_provider_setup(info, status)
    return _render_public_fallback_setup(info, status)


def _check_broker_gateway_setup(
    info: ProviderSetupInfo,
    root: Path | None,
    host: str,
    port: int,
    timeout_seconds: float,
) -> ProviderSetupStatus:
    app_installed = _detect_provider_app(info.provider_id)
    sdk_installed = _sdk_installed(info)
    reachable = is_opend_reachable(host, port, timeout_seconds)
    provider_enabled = _provider_enabled_in_market_data(root, info.provider_id)
    missing = []
    if not app_installed:
        missing.append(f"{info.display_name} app/gateway is not detected.")
    if not reachable:
        missing.append(f"Local OpenD is not reachable at {host}:{port}.")

    warnings = _base_security_warnings(info)
    if info.sdk_package_name and not sdk_installed:
        warnings.append(
            f"{info.sdk_package_name} SDK is not installed; install SDKs only after explicit user approval."
        )
    if root is not None and not provider_enabled:
        warnings.append(f"{info.display_name} is not enabled in market_data.md; zero-config/manual mode remains available.")

    return ProviderSetupStatus(
        provider_id=info.provider_id,
        installed=app_installed,
        configured=app_installed and provider_enabled and not info.password_required_by_tradelens,
        reachable=reachable,
        missing_components=missing,
        setup_url=info.official_setup_url,
        docs_url=info.official_docs_url,
        next_steps=_broker_gateway_next_steps(info),
        warnings=warnings,
    )


def _check_api_provider_setup(info: ProviderSetupInfo) -> ProviderSetupStatus:
    missing = [f"{env_var} environment variable." for env_var in info.env_vars_required if not os.environ.get(env_var)]
    configured = not missing
    warnings = _base_security_warnings(info)
    return ProviderSetupStatus(
        provider_id=info.provider_id,
        installed=True,
        configured=configured,
        reachable=configured,
        missing_components=missing,
        setup_url=info.official_setup_url,
        docs_url=info.official_docs_url,
        next_steps=_api_provider_next_steps(info),
        warnings=_ordered_unique(warnings),
    )


def _check_public_fallback_setup(info: ProviderSetupInfo) -> ProviderSetupStatus:
    warnings = _base_security_warnings(info)
    return ProviderSetupStatus(
        provider_id=info.provider_id,
        installed=True,
        configured=True,
        reachable=False,
        missing_components=[],
        setup_url=info.official_setup_url,
        docs_url=info.official_docs_url,
        next_steps=[
            f"Use {info.display_name} only as a best-effort public fallback.",
            "If automated fetching is blocked or incomplete, paste visible data manually.",
            f"Run: /tradelens provider test {info.provider_id}",
        ],
        warnings=warnings,
    )


def _render_broker_gateway_setup(
    info: ProviderSetupInfo,
    status: ProviderSetupStatus,
    host: str,
    port: int,
) -> str:
    lines = [
        f"## {info.display_name} Setup",
        "",
        f"Status: {_broker_gateway_status_text(status)}",
        "",
        "Missing:",
        *_bullet_lines(status.missing_components or ["No required setup components are missing."]),
        "",
        "Install:",
        f"- Official download: {status.setup_url}",
        f"- Official guide: {status.docs_url}",
        "",
        "Safe setup:",
        *_numbered_lines(status.next_steps),
        "",
        "Security:",
        *_security_bullets(info),
        "- No broker password is needed by TradeLens.",
        "- No app, SDK, or package was installed.",
        "",
        "Zero-config:",
        "- Provider setup is optional; TradeLens can continue in zero-config/manual mode.",
    ]
    if info.sdk_package_name:
        lines.extend(
            [
                "",
                "Optional SDK:",
                f"- {info.sdk_package_name} is optional for setup guidance.",
                "- Ask explicitly before installing any SDK package.",
            ]
        )
    if status.warnings:
        lines.extend(["", "Warnings:", *_bullet_lines(status.warnings)])
    return "\n".join(lines).replace(f"{host}:{port}", f"{host}:{port}")


def _render_api_provider_setup(info: ProviderSetupInfo, status: ProviderSetupStatus) -> str:
    title = _api_setup_title(info)
    lines = [
        f"## {title} Setup",
        "",
        f"Status: {_api_provider_status_text(status)}",
        "",
        "Missing:",
        *_bullet_lines(status.missing_components or ["No required setup components are missing."]),
        "",
        "Setup:",
        *_numbered_lines(status.next_steps),
        "",
        "Links:",
        f"- Official setup: {status.setup_url}",
        f"- Official docs: {status.docs_url}",
        "",
        "Security:",
        "- Do not paste API keys into chat.",
        "- Do not store API keys in market_data.md.",
        "- TradeLens reads API keys only from environment variables or OS keychain.",
        "- No app, SDK, or package was installed.",
        "",
        "Zero-config:",
        "- Provider setup is optional; TradeLens can continue in zero-config/manual mode.",
    ]
    if status.warnings:
        lines.extend(["", "Warnings:", *_bullet_lines(status.warnings)])
    return "\n".join(lines)


def _render_public_fallback_setup(info: ProviderSetupInfo, status: ProviderSetupStatus) -> str:
    lines = [
        f"## {info.display_name} Setup",
        "",
        "Status: no account or API key required.",
        "",
        "Missing:",
        "- No required setup components are missing.",
        "",
        "Setup:",
        *_numbered_lines(status.next_steps),
        "",
        "Links:",
        f"- Official site: {status.setup_url}",
        f"- Official docs: {status.docs_url}",
        "",
        "Security:",
        "- Do not paste broker credentials or API keys into chat.",
        "- Do not store secrets in market_data.md.",
        "- No app, SDK, or package was installed.",
        "",
        "Zero-config:",
        "- This provider is a best-effort fallback; manual data remains available.",
    ]
    if status.warnings:
        lines.extend(["", "Warnings:", *_bullet_lines(status.warnings)])
    return "\n".join(lines)


def _render_unknown_provider(provider_name: str) -> str:
    provider = provider_name.strip() or "unknown"
    supported = ", ".join(sorted(PROVIDER_SETUP_REGISTRY))
    return (
        f"Unknown provider setup target: {provider}\n"
        f"Supported providers: {supported}\n"
        "No app, SDK, package, API key, or provider config was installed."
    )


def _broker_gateway_status_text(status: ProviderSetupStatus) -> str:
    if status.installed and status.reachable:
        return "installed and reachable."
    return "not installed or not reachable."


def _api_provider_status_text(status: ProviderSetupStatus) -> str:
    if status.configured:
        return "API key environment variable is configured."
    return "API key not configured."


def _api_setup_title(info: ProviderSetupInfo) -> str:
    if info.provider_id == "polygon":
        return "Polygon"
    return info.display_name


def _broker_gateway_next_steps(info: ProviderSetupInfo) -> list[str]:
    login = "Futu/OpenD" if info.provider_id == "futu-opend" else "moomoo/OpenD"
    return [
        f"Download {info.display_name} from the official link.",
        "Install and start OpenD.",
        f"Log in through official {login}.",
        "Keep OpenD running locally.",
        f"Run: /tradelens provider test {info.provider_id}",
    ]


def _api_provider_next_steps(info: ProviderSetupInfo) -> list[str]:
    env_var = info.env_vars_required[0] if info.env_vars_required else "PROVIDER_API_KEY"
    return [
        f"Create/get API key from the official {info.display_name} site: {info.official_setup_url}",
        f'Set environment variable: export {env_var}="your_key_here"',
        "Restart the host if needed.",
        f"Run: /tradelens provider test {info.provider_id}",
    ]


def _security_bullets(info: ProviderSetupInfo) -> list[str]:
    if info.provider_id == "futu-opend":
        broker_name = "Futu"
    elif info.provider_id == "moomoo-opend":
        broker_name = "moomoo"
    else:
        broker_name = "broker"
    return [
        f"- TradeLens does not ask for your {broker_name} password.",
        "- TradeLens does not store broker credentials.",
        "- TradeLens connects only to local OpenD.",
        "- Trading is disabled by default.",
        "- Never paste broker passwords, 2FA codes, SMS codes, or recovery codes into chat.",
    ]


def _base_security_warnings(info: ProviderSetupInfo) -> list[str]:
    warnings = []
    if info.password_required_by_tradelens:
        warnings.append("Invalid setup metadata: TradeLens must not require a provider password.")
    if info.stores_secret_in_markdown:
        warnings.append("Invalid setup metadata: TradeLens must not store secrets in markdown.")
    warnings.append("Provider setup is optional and only improves data quality.")
    warnings.append("If setup is incomplete, continue in zero-config/manual mode.")
    return warnings


def _detect_provider_app(provider_id: str) -> bool:
    app_names = _OPEND_APP_NAMES.get(provider_id, ())
    app_dirs = [Path("/Applications"), Path.home() / "Applications"]
    return any((app_dir / app_name).exists() for app_dir in app_dirs for app_name in app_names)


def _sdk_installed(info: ProviderSetupInfo) -> bool:
    if not info.sdk_package_name:
        return False
    module_name = _SDK_IMPORT_MODULES.get(info.sdk_package_name, info.sdk_package_name.replace("-", "_"))
    return importlib.util.find_spec(module_name) is not None


def _provider_enabled_in_market_data(root: Path | None, provider_id: str) -> bool:
    if root is None:
        return False
    path = root / "market_data.md"
    if not path.exists():
        return False
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False
    keys = _PROVIDER_MARKET_DATA_KEYS.get(provider_id, ())
    if not keys:
        return False
    sections = _parse_provider_sections(text)
    return any(sections.get(key, {}).get("enabled") is True for key in keys)


def _parse_provider_sections(text: str) -> dict[str, dict[str, object]]:
    sections: dict[str, dict[str, object]] = {}
    current = ""
    for raw_line in text.splitlines():
        line = raw_line.strip()
        heading = re.match(r"^##\s+(.+)$", line)
        if heading:
            current = _normalize_market_data_heading(heading.group(1))
            sections.setdefault(current, {})
            continue
        if current and line.startswith("- ") and ":" in line:
            key, value = line[2:].split(":", 1)
            sections[current][key.strip()] = _parse_value(value.strip())
    return sections


def _normalize_market_data_heading(heading: str) -> str:
    normalized = heading.strip().lower().replace("provider", "").replace(" ", "_").replace("-", "_")
    return normalized.replace("__", "_").strip("_")


def _normalize_provider_name(provider_name: str) -> str:
    normalized = provider_name.strip().lower().replace("_", "-")
    normalized = re.sub(r"\s+", " ", normalized)
    if normalized == "option-charts":
        return "option charts"
    if normalized == "cnn-fear-and-greed":
        return "cnn-fear-greed"
    return normalized


def _parse_value(value: str) -> object:
    lowered = value.strip().lower()
    if lowered in {"true", "yes"}:
        return True
    if lowered in {"false", "no"}:
        return False
    return value


def _bullet_lines(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items]


def _numbered_lines(items: list[str]) -> list[str]:
    return [f"{index}. {item}" for index, item in enumerate(items, start=1)]


def _ordered_unique(items: list[str]) -> list[str]:
    seen = set()
    unique = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            unique.append(item)
    return unique
