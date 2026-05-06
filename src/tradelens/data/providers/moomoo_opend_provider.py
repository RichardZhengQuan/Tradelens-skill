"""Moomoo OpenD market data provider."""

from __future__ import annotations

from dataclasses import dataclass

from tradelens.data.providers.opend_base_provider import OpenDProvider


@dataclass
class MoomooOpenDProvider(OpenDProvider):
    account_type: str = "moomoo"
    sdk_package: str = "moomoo"
    sdk_display_name: str = "moomoo"
    provider_type: str = "Moomoo OpenD"
    login_name: str = "moomoo"
    server_name: str = "moomoo"
    name: str = "MoomooOpenDProvider"
