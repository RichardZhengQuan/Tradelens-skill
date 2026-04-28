"""Small text extraction helpers.

These helpers are intentionally conservative. They identify obvious user-provided
order-like text but do not treat parsed values as confirmed truth.
"""

from __future__ import annotations

import re
from typing import List

from tradelens.models import ExtractionBundle, OrderLine


ACTION_RE = re.compile(
    r"\b(sell\s+to\s+open|buy\s+to\s+close|buy\s+to\s+open|sell\s+to\s+close|buy|sell|bto|sto|btc|stc|short|cover)\b",
    re.IGNORECASE,
)
SYMBOL_RE = re.compile(r"\b[A-Z]{1,6}\b")
EXPIRY_RE = r"(?:\d{8}|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})"
BROKER_ORDER_RE = re.compile(
    rf"""
    ^\s*
    (?P<action>sell\s+to\s+open|buy\s+to\s+close|buy\s+to\s+open|sell\s+to\s+close|sto|bto|stc|btc|sell|buy)
    \s+
    (?P<quantity>\d+(?:\.\d+)?)
    \s+
    (?P<symbol>[A-Za-z]{{1,6}})
    \s+
    (?:
        (?P<expiry_first>{EXPIRY_RE})
        \s+
        (?P<strike_after_expiry>\d+(?:\.\d+)?)
        \s*
        (?P<option_type_after_expiry>call|put|c|p)
      |
        (?P<strike_before_expiry>\d+(?:\.\d+)?)
        \s*
        (?P<option_type_before_expiry>call|put|c|p)
        \s+
        (?P<expiry_after_strike>{EXPIRY_RE})
    )
    (?:\s*(?:@|at)\s*(?P<price>\d+(?:\.\d+)?))?
    \s*$
    """,
    re.IGNORECASE | re.VERBOSE,
)
NON_SYMBOL_TOKENS = {
    "BUY",
    "SELL",
    "TO",
    "BTO",
    "STO",
    "BTC",
    "STC",
    "SHORT",
    "COVER",
    "CALL",
    "PUT",
    "ORDER",
    "FILLED",
    "OPEN",
    "CLOSE",
}


def _parse_broker_order(line: str) -> dict:
    match = BROKER_ORDER_RE.match(line)
    if not match:
        return {}
    groups = match.groupdict()
    option_type = groups.get("option_type_after_expiry") or groups.get("option_type_before_expiry") or "unknown"
    strike = groups.get("strike_after_expiry") or groups.get("strike_before_expiry")
    expiry = groups.get("expiry_first") or groups.get("expiry_after_strike") or "unknown"
    price = groups.get("price")
    return {
        "action": " ".join(groups["action"].lower().split()),
        "quantity": float(groups["quantity"]),
        "symbol": groups["symbol"].upper(),
        "instrument": "option",
        "option_type": {"c": "call", "p": "put"}.get(option_type.lower(), option_type.lower()),
        "strike": float(strike) if strike is not None else None,
        "expiry": expiry,
        "order_price": float(price) if price is not None else None,
    }


def extract_symbol(text: str) -> str:
    parsed = _parse_broker_order(text.strip())
    if parsed:
        return parsed["symbol"]
    for match in SYMBOL_RE.finditer(text):
        token = match.group(0)
        if token.upper() not in NON_SYMBOL_TOKENS:
            return token.upper()
    return "unknown"


def extract_bundle(text: str) -> ExtractionBundle:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    visible = [f"User text line: {line}" for line in lines]
    missing: List[str] = []
    if not ACTION_RE.search(text):
        missing.append("order action")
    if extract_symbol(text) == "unknown":
        missing.append("symbol")
    return ExtractionBundle(
        visible_facts=visible,
        missing_data=missing,
        confidence="unconfirmed text extraction",
    )


def parse_order_lines(text: str, prefix: str = "ORD") -> List[OrderLine]:
    orders: List[OrderLine] = []
    for index, line in enumerate([l.strip() for l in text.splitlines() if l.strip()], start=1):
        parsed = _parse_broker_order(line)
        action_match = ACTION_RE.search(line)
        orders.append(
            OrderLine(
                order_line_id=f"{prefix}-{index:02d}",
                symbol=parsed.get("symbol", extract_symbol(line)),
                action=parsed.get(
                    "action",
                    " ".join(action_match.group(0).lower().split()) if action_match else "unknown",
                ),
                quantity=parsed.get("quantity"),
                instrument=parsed.get("instrument", "unknown"),
                option_type=parsed.get("option_type", "unknown"),
                strike=parsed.get("strike"),
                expiry=parsed.get("expiry", "unknown"),
                order_price=parsed.get("order_price"),
                notes=line,
                extraction_confidence="unconfirmed text extraction",
            )
        )
    return orders
