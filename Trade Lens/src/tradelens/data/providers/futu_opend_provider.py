"""Futu OpenD market data provider."""

from __future__ import annotations

from dataclasses import dataclass

from tradelens.data.providers.opend_base_provider import OpenDProvider


@dataclass
class FutuOpenDProvider(OpenDProvider):
    account_type: str = "futu"
    sdk_package: str = "futu"
    sdk_display_name: str = "futu-api"
    provider_type: str = "Futu OpenD"
    login_name: str = "Futu/Futubull"
    server_name: str = "Futu"
    name: str = "FutuOpenDProvider"
