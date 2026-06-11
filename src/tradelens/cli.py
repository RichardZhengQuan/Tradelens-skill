"""Small local CLI helpers for Trade Lens markdown files."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from tradelens.data.provider_setup import normalize_provider_id, render_provider_setup
from tradelens.data.providers.futu_opend_provider import FutuOpenDProvider
from tradelens.data.providers.moomoo_opend_provider import MoomooOpenDProvider
from tradelens.data.providers.opend_base_provider import OpenDProvider, detect_opend_provider
from tradelens.storage.history_store import HistoryStore

PROVIDER_TARGETS = {
    "cnn",
    "cnn-fear-greed",
    "feargreed",
    "finnhub",
    "futu",
    "futu-opend",
    "futud",
    "massive",
    "moomoo",
    "moomoo-opend",
    "opend",
    "optioncharts",
    "polygon",
    "tradier",
    "yahoo",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tradelens")
    parser.add_argument("--root", default=".", help="TradeLensSkill root directory")
    sub = parser.add_subparsers(dest="command")
    history = sub.add_parser("history", help="List saved analysis records")
    history.add_argument("--name", help="Show one saved analysis detail by exact or fuzzy name")
    provider = sub.add_parser("provider", help="Manage optional market data providers")
    provider_sub = provider.add_subparsers(dest="provider_command")
    provider_setup = provider_sub.add_parser("setup", help="Show safe provider setup guidance")
    provider_setup.add_argument("target", nargs="+")
    provider_add = provider_sub.add_parser("add", help="Add a read-only provider config")
    provider_add.add_argument("target", nargs="+")
    provider_test = provider_sub.add_parser("test", help="Test a read-only provider connection")
    provider_test.add_argument("target", nargs="+")
    for alias in ("futu", "moomoo", "opend"):
        alias_parser = sub.add_parser(alias, help=f"{alias} provider helpers")
        alias_sub = alias_parser.add_subparsers(dest="alias_command")
        alias_sub.add_parser("setup", help=f"Show {alias} setup guidance")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root)
    if args.command == "history":
        history = HistoryStore(root / "analysis_history")
        if args.name:
            print(history.detail(args.name), end="")
            return 0
        for path in history.list_all():
            print(path.name)
        return 0
    if args.command == "provider":
        target = _target_text(getattr(args, "target", ""))
        if args.provider_command == "setup":
            return _provider_setup(root, target)
        if args.provider_command == "add":
            return _provider_add(root, target)
        if args.provider_command == "test":
            return _provider_test(root, target)
    if args.command in {"futu", "moomoo", "opend"} and getattr(args, "alias_command", None) == "setup":
        return _provider_setup(root, args.command)
    return 0


def _provider_setup(root: Path, target: str) -> int:
    provider_target = _resolve_provider_target(target)
    if provider_target is None:
        print("OpenD can mean Futu OpenD or Moomoo OpenD.")
        print("Choose `/tradelens provider setup futu-opend` or `/tradelens provider setup moomoo-opend`.")
        print("No app, SDK, package, API key, or provider config was installed.")
        return 2
    print(render_provider_setup(provider_target, root=root))
    return 0


def _provider_add(root: Path, target: str) -> int:
    provider_target = _resolve_provider_target(target)
    if provider_target is None:
        print("OpenD can mean Futu OpenD or Moomoo OpenD.")
        print("Choose `/tradelens provider add futu-opend` or `/tradelens provider add moomoo-opend`.")
        print("No package was installed and no provider was enabled.")
        return 2
    heading, config = _provider_config_for_target(provider_target)
    config = dict(config)
    config["enabled"] = True
    config["read_only"] = True
    config["allow_trading"] = False
    config["store_password"] = False
    _upsert_provider_config(root / "market_data.md", heading, config)
    print(f"Added {heading} config in read-only mode.")
    print("No broker password, trading password, 2FA code, SMS code, or recovery code is needed.")
    print("No package was installed.")
    print("")
    print(render_provider_setup(provider_target, root=root))
    return 0


def _provider_test(root: Path, target: str) -> int:
    provider_target = _resolve_provider_target(target)
    if provider_target is None:
        print("OpenD provider is ambiguous. Choose Futu OpenD or Moomoo OpenD before testing.")
        return 2
    if provider_target not in {"futu-opend", "moomoo-opend"}:
        print(render_provider_setup(provider_target, root=root))
        return 0
    provider = _provider_for_target(provider_target)
    quote, status = provider.get_quote("SPY")
    setup_result = provider.setup_result_from_statuses([status])
    _upsert_opend_provider_status(root / "market_data.md", setup_result)
    print(f"Provider type: {setup_result.provider_type}")
    print(f"OpenD process detected: {'yes' if setup_result.opend_process_detected else 'no'}")
    print(f"OpenD port reachable: {'yes' if setup_result.opend_port_reachable else 'no'}")
    print(f"Direct OpenD quote test: {'success' if setup_result.direct_opend_quote_success else 'fail'}")
    print(f"Python executable used: {setup_result.python_executable}")
    print(f"{provider.sdk_display_name} installed: {'yes' if setup_result.sdk_installed else 'no'}")
    print(f"SDK connection test: {'success' if setup_result.sdk_connection_success else 'fail'}")
    print(f"Test quote: {'success' if quote and status.available else 'failed'}")
    if not setup_result.sdk_installed:
        print(f"Optional SDK install command: python3 -m pip install {_sdk_install_package(provider)}")
    if setup_result.direct_opend_quote_error:
        print(f"Direct OpenD quote error: {setup_result.direct_opend_quote_error}")
    if setup_result.sdk_connection_error:
        print(f"SDK connection error: {setup_result.sdk_connection_error}")
    if status.error:
        print(f"Error: {status.error}")
    return 0 if quote and status.available else 1


def _resolve_provider_target(target: str) -> str | None:
    normalized = target.strip().lower()
    if normalized != "opend":
        return normalize_provider_id(normalized)
    detection = detect_opend_provider()
    return detection.selected_provider


def _provider_for_target(target: str) -> OpenDProvider:
    if target == "futu-opend":
        return FutuOpenDProvider(enabled=True)
    if target == "moomoo-opend":
        return MoomooOpenDProvider(enabled=True)
    raise ValueError(f"Unknown OpenD provider target: {target}")


def _sdk_install_package(provider: OpenDProvider) -> str:
    return {"futu": "futu-api", "moomoo": "moomoo-api"}.get(provider.sdk_package, provider.sdk_display_name)


def _provider_config_for_target(target: str) -> tuple[str, dict]:
    if target == "futu-opend":
        return "Futu OpenD Provider", FutuOpenDProvider.default_config()
    if target == "moomoo-opend":
        return "Moomoo OpenD Provider", MoomooOpenDProvider.default_config()
    if target == "tradier":
        return "TradierProvider", {"enabled": True, "environment": "production", "api_key_env": "TRADIER_API_KEY"}
    if target == "polygon":
        return "PolygonProvider", {"enabled": True, "api_key_env": "POLYGON_API_KEY"}
    if target == "finnhub":
        return "FinnhubProvider", {"enabled": True, "api_key_env": "FINNHUB_API_KEY"}
    if target == "yahoo":
        return "YahooProvider", {"enabled": True, "quality": "best_effort"}
    if target == "cnn-fear-greed":
        return "CNN Fear & Greed Provider", {"enabled": True, "quality": "best_effort"}
    if target == "optioncharts":
        return "OptionCharts Provider", {"enabled": True, "quality": "best_effort"}
    raise ValueError(f"Unknown provider target: {target}")


def _upsert_provider_config(path: Path, heading: str, config: dict) -> None:
    updates = {
        key: config[key]
        for key in (
            "enabled",
            "host",
            "port",
            "market",
            "account_type",
            "require_local_opend",
            "read_only",
            "allow_trading",
            "store_password",
            "allow_remote_host",
            "sdk_package",
            "security_firm",
            "trading_env",
            "currency",
            "account_id",
            "account_index",
            "environment",
            "api_key_env",
            "quality",
        )
        if key in config
    }
    _upsert_bullet_section(path, heading, updates)


def _upsert_opend_provider_status(path: Path, setup_result) -> None:
    rows = [
        ("Provider type", setup_result.provider_type),
        ("OpenD process detected", "yes" if setup_result.opend_process_detected else "no"),
        ("OpenD port reachable", "yes" if setup_result.opend_port_reachable else "no"),
        ("Direct OpenD quote test", "success" if setup_result.direct_opend_quote_success else "fail"),
        ("Python executable used", setup_result.python_executable),
        ("futu-api installed" if setup_result.provider_type == "Futu OpenD" else "SDK installed", "yes" if setup_result.sdk_installed else "no"),
        ("SDK connection test", "success" if setup_result.sdk_connection_success else "fail"),
        ("Host", setup_result.host),
        ("Port", setup_result.port),
        ("Read-only mode", "yes" if setup_result.read_only else "no"),
        ("Trading enabled", "yes" if setup_result.trading_enabled else "no"),
        ("Password stored", "yes" if setup_result.password_stored else "no"),
        ("Test quote", "success" if setup_result.test_quote_success else "failed"),
    ]
    table = "\n".join(f"| {item} | {status} |" for item, status in rows)
    section = f"""## OpenD Provider Status

| Item | Status |
|---|---|
{table}
"""
    text = _read_text_or_default(path)
    pattern = re.compile(r"^## OpenD Provider Status\n.*?(?=^## |\Z)", re.MULTILINE | re.DOTALL)
    if pattern.search(text):
        text = pattern.sub(section.strip() + "\n\n", text)
    else:
        marker = "\n## Corrections"
        if marker in text:
            text = text.replace(marker, "\n" + section + marker, 1)
        else:
            text = text.rstrip() + "\n\n" + section
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _upsert_bullet_section(path: Path, heading: str, updates: dict) -> None:
    text = _read_text_or_default(path)
    heading_line = f"## {heading}"
    pattern = re.compile(rf"^{re.escape(heading_line)}\n.*?(?=^## |\Z)", re.MULTILINE | re.DOTALL)
    match = pattern.search(text)
    if match:
        section = match.group(0)
        for key, value in updates.items():
            line_pattern = re.compile(rf"^- {re.escape(key)}: .*$", re.MULTILINE)
            line = f"- {key}: {_config_value(value)}"
            if line_pattern.search(section):
                section = line_pattern.sub(line, section)
            else:
                section = section.rstrip() + "\n" + line + "\n"
        text = text[: match.start()] + section.rstrip() + "\n\n" + text[match.end() :]
    else:
        lines = "\n".join(f"- {key}: {_config_value(value)}" for key, value in updates.items())
        section = f"{heading_line}\n\n{lines}\n"
        marker = "\n## Corrections"
        if marker in text:
            text = text.replace(marker, "\n" + section + marker, 1)
        else:
            text = text.rstrip() + "\n\n" + section
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _read_text_or_default(path: Path) -> str:
    if not path.exists():
        return "# Market Data Settings\n\n"
    return path.read_text(encoding="utf-8")


def _config_value(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _target_text(target) -> str:
    if isinstance(target, list):
        return " ".join(target)
    return str(target)


if __name__ == "__main__":
    raise SystemExit(main())
