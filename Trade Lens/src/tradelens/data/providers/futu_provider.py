"""Backward-compatible Futu provider alias."""

from __future__ import annotations

import importlib
import socket

from tradelens.data.providers.futu_opend_provider import FutuOpenDProvider

FutuProvider = FutuOpenDProvider

__all__ = ["FutuProvider", "FutuOpenDProvider", "importlib", "socket"]
