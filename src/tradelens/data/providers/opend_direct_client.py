"""Direct read-only OpenD quote client.

This module uses the documented local OpenD socket protocol for quote
snapshots. It intentionally implements only InitConnect plus quote snapshot
requests; it does not expose order, unlock, password, or account mutation APIs.
"""

from __future__ import annotations

import hashlib
import json
import socket
import struct
from datetime import datetime, timezone
from typing import Any, Optional

from tradelens.data.market_snapshot import QuoteSnapshot

HEADER_LEN = 44
PROTO_FMT_JSON = 1
PROTO_VER = 0
PROTO_INIT_CONNECT = 1001
PROTO_GET_MARKET_SNAPSHOT = 3203

LOCAL_OPEND_HOSTS = {"127.0.0.1", "localhost", "::1"}

MARKET_CODES = {
    "HK": 1,
    "US": 11,
}


class OpenDDirectError(RuntimeError):
    """Raised when the direct OpenD quote path fails safely."""


def fetch_quote_direct_opend(
    symbol: str,
    host: str = "127.0.0.1",
    port: int = 11111,
    timeout: float = 1.5,
    market: str = "US",
    provider_name: str = "OpenDDirectClient",
) -> QuoteSnapshot:
    """Fetch a quote through local OpenD without requiring the Python SDK."""

    _validate_read_only_target(host)
    serial = 1
    fetched_at = datetime.now(timezone.utc)
    try:
        with socket.create_connection((host, int(port)), timeout=timeout) as sock:
            sock.settimeout(timeout)
            sock.sendall(
                _pack_message(
                    PROTO_INIT_CONNECT,
                    serial,
                    {
                        "c2s": {
                            "clientVer": 0,
                            "clientID": "TradeLensDirectQuote",
                            "recvNotify": False,
                            "packetEncAlgo": 0,
                            "pushProtoFmt": PROTO_FMT_JSON,
                        }
                    },
                )
            )
            _read_response(sock, expected_proto=PROTO_INIT_CONNECT, expected_serial=serial)
            serial += 1
            market_code, code = _market_and_code(symbol, market)
            sock.sendall(
                _pack_message(
                    PROTO_GET_MARKET_SNAPSHOT,
                    serial,
                    {"c2s": {"securityList": [{"market": market_code, "code": code}]}},
                )
            )
            response = _read_response(sock, expected_proto=PROTO_GET_MARKET_SNAPSHOT, expected_serial=serial)
    except OpenDDirectError:
        raise
    except Exception as exc:
        raise OpenDDirectError(f"Direct OpenD quote request failed: {exc}") from exc

    basic = _first_snapshot_basic(response)
    price = _float_or_none(_first_present(basic, "curPrice", "lastPrice", "price"))
    if price is None:
        raise OpenDDirectError("Direct OpenD quote response did not include a latest price")
    data_time = _snapshot_data_time(basic) or fetched_at
    return QuoteSnapshot(
        symbol=code.upper(),
        price=price,
        bid=_float_or_none(basic.get("bidPrice")),
        ask=_float_or_none(basic.get("askPrice")),
        previous_close=_float_or_none(basic.get("lastClosePrice")),
        session="unknown",
        provider_name=provider_name,
        source_type="opend_direct",
        fetched_at=fetched_at,
        data_time=data_time,
        data_quality="medium",
    )


def _validate_read_only_target(host: str) -> None:
    if host.strip().lower() not in LOCAL_OPEND_HOSTS:
        raise OpenDDirectError("Direct OpenD quote requests are limited to local hosts by default")


def _pack_message(proto_id: int, serial_no: int, body_obj: dict[str, Any]) -> bytes:
    body = json.dumps(body_obj, separators=(",", ":")).encode("utf-8")
    header = (
        b"FT"
        + struct.pack("<IBBII", proto_id, PROTO_FMT_JSON, PROTO_VER, serial_no, len(body))
        + hashlib.sha1(body).digest()
        + (b"\0" * 8)
    )
    return header + body


def _read_response(sock: socket.socket, expected_proto: int, expected_serial: int) -> dict[str, Any]:
    header = _read_exact(sock, HEADER_LEN)
    if len(header) != HEADER_LEN or header[:2] != b"FT":
        raise OpenDDirectError("Invalid OpenD response header")
    proto_id, proto_fmt, _proto_ver, serial_no, body_len = struct.unpack("<IBBII", header[2:16])
    expected_sha = header[16:36]
    if proto_id != expected_proto or serial_no != expected_serial:
        raise OpenDDirectError(f"Unexpected OpenD response protocol={proto_id} serial={serial_no}")
    if proto_fmt != PROTO_FMT_JSON:
        raise OpenDDirectError("OpenD response was not JSON formatted")
    body = _read_exact(sock, body_len)
    if hashlib.sha1(body).digest() != expected_sha:
        raise OpenDDirectError("OpenD response checksum mismatch")
    response = json.loads(body.decode("utf-8"))
    if int(response.get("retType", -1)) != 0:
        message = response.get("retMsg") or response.get("errCode") or "unknown OpenD error"
        raise OpenDDirectError(f"OpenD returned error: {message}")
    return response


def _read_exact(sock: socket.socket, size: int) -> bytes:
    chunks = bytearray()
    while len(chunks) < size:
        chunk = sock.recv(size - len(chunks))
        if not chunk:
            raise OpenDDirectError("OpenD socket closed before response completed")
        chunks.extend(chunk)
    return bytes(chunks)


def _market_and_code(symbol: str, default_market: str) -> tuple[int, str]:
    cleaned = symbol.strip().upper()
    if "." in cleaned:
        prefix, code = cleaned.split(".", 1)
        market_code = MARKET_CODES.get(prefix)
        if market_code is None:
            raise OpenDDirectError(f"Unsupported direct OpenD market prefix: {prefix}")
        return market_code, code
    market_code = MARKET_CODES.get(default_market.strip().upper())
    if market_code is None:
        raise OpenDDirectError(f"Unsupported direct OpenD market: {default_market}")
    return market_code, cleaned


def _first_snapshot_basic(response: dict[str, Any]) -> dict[str, Any]:
    snapshots = (((response.get("s2c") or {}).get("snapshotList")) or [])
    if not snapshots:
        raise OpenDDirectError("Direct OpenD quote response did not include a snapshot")
    basic = snapshots[0].get("basic") or {}
    if not isinstance(basic, dict):
        raise OpenDDirectError("Direct OpenD quote response had invalid snapshot data")
    return basic


def _snapshot_data_time(basic: dict[str, Any]) -> Optional[datetime]:
    timestamp = _float_or_none(basic.get("updateTimestamp"))
    if timestamp is not None:
        return datetime.fromtimestamp(timestamp, timezone.utc)
    update_time = basic.get("updateTime")
    if isinstance(update_time, str) and update_time:
        for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(update_time, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
    return None


def _first_present(mapping: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in mapping and mapping[key] not in (None, ""):
            return mapping[key]
    return None


def _float_or_none(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
